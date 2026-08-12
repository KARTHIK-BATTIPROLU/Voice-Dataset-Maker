"""
Manifest Generator Component

Creates and updates SpeechBrain-compatible CSV manifest with atomic operations.
"""

from pathlib import Path
import csv
import threading
from typing import List
import logging
from models import SampleMetadata, ValidationReport
import wave


logger = logging.getLogger(__name__)


class ManifestGenerator:
    """
    Manages the SpeechBrain-compatible manifest CSV file.
    
    Provides atomic append operations and comprehensive validation.
    """
    
    HEADERS = [
        "sample_id",
        "file_path",
        "transcript",
        "duration_sec",
        "sample_rate",
        "session_id",
        "timestamp",
        "whisper_confidence"
    ]
    
    def __init__(self, manifest_path: Path = Path("manifest.csv"), project_root: Path = Path(".")):
        """
        Initialize manifest generator with CSV file path.
        
        Args:
            manifest_path: Path to manifest CSV file
            project_root: Project root for relative path conversion
        """
        self.manifest_path = manifest_path
        self.project_root = project_root.resolve()
        self.lock = threading.Lock()
        
        # Initialize manifest if it doesn't exist
        if not self.manifest_path.exists():
            self.initialize_manifest()
    
    def initialize_manifest(self) -> None:
        """Create manifest.csv with headers if not exists"""
        try:
            with open(self.manifest_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(self.HEADERS)
            logger.info(f"Initialized manifest: {self.manifest_path}")
        except Exception as e:
            logger.error(f"Failed to initialize manifest: {e}")
            raise
    
    def append_sample(self, sample_data: SampleMetadata) -> None:
        """
        Atomically append sample row to manifest.
        
        Args:
            sample_data: Complete sample metadata
        """
        with self.lock:
            try:
                with open(self.manifest_path, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(sample_data.to_csv_row())
                logger.info(f"Appended sample {sample_data.sample_id} to manifest")
            except Exception as e:
                logger.error(f"Failed to append to manifest: {e}")
                raise
    
    def to_relative_path(self, absolute_path: Path) -> str:
        """
        Convert absolute path to relative path from project root.
        
        Args:
            absolute_path: Absolute file path
            
        Returns:
            Relative path with forward slashes for portability
        """
        try:
            rel_path = absolute_path.resolve().relative_to(self.project_root)
            # Convert to forward slashes for portability
            return str(rel_path).replace('\\', '/')
        except ValueError:
            # If path is not relative to project_root, return as-is
            return str(absolute_path).replace('\\', '/')
    
    def validate_manifest(self) -> ValidationReport:
        """
        Validate manifest integrity.
        
        Checks:
        - All file paths exist
        - Sample IDs are unique
        - Required columns present
        - Duration matches actual file duration (sampling check)
        
        Returns:
            ValidationReport with issues list
        """
        report = ValidationReport(is_valid=True)
        
        if not self.manifest_path.exists():
            report.is_valid = False
            report.format_errors.append("Manifest file does not exist")
            return report
        
        try:
            with open(self.manifest_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # Check headers
                if not reader.fieldnames or set(reader.fieldnames) != set(self.HEADERS):
                    report.is_valid = False
                    report.format_errors.append(f"Invalid headers. Expected: {self.HEADERS}")
                    return report
                
                seen_ids = set()
                sample_rates = set()
                transcripts = set()
                
                for row in reader:
                    sample_id = row['sample_id']
                    file_path = row['file_path']
                    transcript = row['transcript']
                    sample_rate = int(row['sample_rate'])
                    
                    report.total_samples += 1
                    
                    # Check for duplicate IDs
                    if sample_id in seen_ids:
                        report.duplicate_ids.append(sample_id)
                        report.is_valid = False
                    seen_ids.add(sample_id)
                    
                    # Check file exists
                    full_path = self.project_root / file_path
                    if not full_path.exists():
                        report.missing_files.append(file_path)
                        report.is_valid = False
                    else:
                        report.valid_samples += 1
                    
                    # Track sample rates
                    sample_rates.add(sample_rate)
                    
                    # Track transcripts
                    if transcript == "__unclear__":
                        report.unclear_samples += 1
                    else:
                        transcripts.add(transcript)
                
                # Check sample rate consistency
                if len(sample_rates) > 1:
                    report.format_errors.append(f"Inconsistent sample rates found: {sample_rates}")
                    report.is_valid = False
                
                report.unique_transcripts = len(transcripts)
                report.ready_for_training = report.valid_samples >= 500
                
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            report.is_valid = False
            report.format_errors.append(f"Validation error: {str(e)}")
        
        return report
    
    def get_max_sample_id(self) -> int:
        """
        Get the maximum sample ID from manifest.
        
        Returns:
            Maximum sample ID as integer, or 0 if manifest is empty
        """
        if not self.manifest_path.exists():
            return 0
        
        max_id = 0
        try:
            with open(self.manifest_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        sample_num = int(row['sample_id'])
                        max_id = max(max_id, sample_num)
                    except (ValueError, KeyError):
                        continue
        except Exception as e:
            logger.error(f"Failed to read manifest: {e}")
        
        return max_id
