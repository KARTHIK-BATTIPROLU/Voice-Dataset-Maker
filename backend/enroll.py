"""
Enrollment Script - Speaker Embedding & Verification

Processes recorded enrollment clips with pretrained frozen ECAPA-TDNN model.
Computes averaged voiceprint, handles outlier rejection, and scores holdout clips.
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import sys
import logging
from pathlib import Path
import torch
import numpy as np
import pandas as pd
from speechbrain.inference.speaker import EncoderClassifier

logger = logging.getLogger(__name__)

MODEL_SOURCE = "speechbrain/spkrec-ecapa-voxceleb"
SAVEDIR = "pretrained_models/spkrec-ecapa-voxceleb"

_classifier = None


def get_classifier():
    """Lazy load frozen ECAPA-TDNN model"""
    global _classifier
    if _classifier is None:
        logger.info(f"Loading ECAPA-TDNN model from {MODEL_SOURCE}...")
        _classifier = EncoderClassifier.from_hparams(
            source=MODEL_SOURCE,
            savedir=SAVEDIR
        )
    return _classifier


def embed(path: str) -> np.ndarray:
    """Extract 192-dim speaker embedding vector for an audio file"""
    clf = get_classifier()
    signal = clf.load_audio(path)
    embeddings = clf.encode_batch(signal.unsqueeze(0))
    return embeddings.squeeze().detach().cpu().numpy()


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two 1D vectors"""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def run(
    session_id: str,
    manifest_path: str = "manifest.csv",
    output_voiceprint: str = "enrolled_voiceprint.npy",
    speaker_id: str = "ASTA_primary",
    holdout_threshold: float = 0.65
) -> dict:
    """
    Run post-session enrollment and holdout self-consistency check.
    """
    logger.info(f"Starting enrollment run for session: {session_id}")
    
    m_path = Path(manifest_path)
    if not m_path.exists():
        logger.error(f"Manifest file {manifest_path} not found!")
        return {"error": "Manifest file not found", "kept": [], "dropped": [], "holdout_results": []}

    df = pd.read_csv(m_path)
    
    # Normalize is_holdout column to boolean
    if "is_holdout" in df.columns:
        df["is_holdout"] = df["is_holdout"].astype(str).str.lower().isin(["true", "1"])
    else:
        df["is_holdout"] = False

    session_df = df[(df.session_id == session_id) & (df.speaker_id == speaker_id)]
    
    # Exclude REJECTED_QUALITY samples
    if "transcript" in session_df.columns:
        session_df = session_df[session_df.transcript != "REJECTED_QUALITY"]

    enroll_df = session_df[session_df.is_holdout == False]
    holdout_df = session_df[session_df.is_holdout == True]

    if len(enroll_df) == 0:
        logger.warning("No enrollment clips found for session!")
        return {"error": "No enrollment clips found", "kept": [], "dropped": [], "holdout_results": []}

    logger.info(f"Processing {len(enroll_df)} enrollment clips and {len(holdout_df)} holdout clips...")

    embeddings = {}
    for _, row in enroll_df.iterrows():
        try:
            file_path = str(row.file_path)
            embeddings[str(row.sample_id)] = embed(file_path)
        except Exception as e:
            logger.error(f"Failed to embed clip {row.sample_id} ({row.file_path}): {e}")

    ids = list(embeddings.keys())
    if len(ids) == 0:
        return {"error": "Failed to extract embeddings", "kept": [], "dropped": [], "holdout_results": []}

    # Self-consistency check: drop clips whose avg similarity to rest is >1.5 std below mean
    if len(ids) > 1:
        sims = {i: float(np.mean([cosine(embeddings[i], embeddings[j]) for j in ids if j != i])) for i in ids}
        mean_sim = float(np.mean(list(sims.values())))
        std_sim = float(np.std(list(sims.values())))
        cutoff = mean_sim - 1.5 * std_sim
        kept = [i for i in ids if sims[i] >= cutoff]
        dropped = [i for i in ids if i not in kept]
    else:
        kept = ids
        dropped = []

    logger.info(f"Kept {len(kept)}/{len(ids)} clips. Dropped as inconsistent: {dropped}")
    print(f"Kept {len(kept)}/{len(ids)} clips. Dropped as inconsistent: {dropped}")

    if len(kept) == 0:
        kept = ids

    master = np.mean([embeddings[i] for i in kept], axis=0)
    np.save(output_voiceprint, master)
    logger.info(f"Saved master voiceprint to {output_voiceprint}")

    # Verification against holdout clips
    holdout_results = []
    for _, row in holdout_df.iterrows():
        sample_id = str(row.sample_id)
        try:
            emb = embed(str(row.file_path))
            score = cosine(emb, master)
            passed = score >= holdout_threshold
            status_str = "PASS" if passed else "BELOW THRESHOLD"
            print(f"Holdout {sample_id}: similarity={score:.3f}  ({status_str})")
            logger.info(f"Holdout {sample_id}: similarity={score:.3f}  ({status_str})")
            holdout_results.append({
                "sample_id": sample_id,
                "similarity": round(score, 4),
                "passed": passed,
                "threshold": holdout_threshold
            })
        except Exception as e:
            logger.error(f"Failed to verify holdout clip {sample_id}: {e}")
            holdout_results.append({
                "sample_id": sample_id,
                "similarity": 0.0,
                "passed": False,
                "threshold": holdout_threshold,
                "error": str(e)
            })

    return {
        "session_id": session_id,
        "total_enrollment_clips": len(ids),
        "kept": kept,
        "dropped": dropped,
        "voiceprint_path": output_voiceprint,
        "holdout_results": holdout_results
    }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        res = run(sys.argv[1])
        print("Enrollment complete result:", res)
    else:
        print("Usage: python backend/enroll.py <session_id>")
