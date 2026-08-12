/**
 * Notification Component
 * 
 * Displays quality warnings and system messages
 */

import { useEffect, useState } from 'react';
import './Notification.css';

const Notification = ({ message, type, onDismiss }) => {
  useEffect(() => {
    if (message) {
      const timer = setTimeout(() => {
        onDismiss();
      }, 5000);

      return () => clearTimeout(timer);
    }
  }, [message, onDismiss]);

  if (!message) return null;

  return (
    <div className={`notification ${type}`}>
      <span className="notification-message">{message}</span>
      <button className="notification-close" onClick={onDismiss}>
        ×
      </button>
    </div>
  );
};

export default Notification;
