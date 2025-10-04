import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { initTelegramWebApp } from './utils/telegram';
import './DisableErrorOverlay';

// Clean up corrupted localStorage data
const cleanupLocalStorage = () => {
  try {
    for (let i = localStorage.length - 1; i >= 0; i--) {
      const key = localStorage.key(i);
      if (key) {
        try {
          const value = localStorage.getItem(key);
          
          // Protect critical LuvHive keys from deletion
          const isProtectedKey = key.includes('luvhive_') || key.includes('luv_hive_') || 
                                key === 'luvhive_user' || key === 'luv_hive_user' ||
                                key.includes('posts') || key.includes('stories');
          
          if (isProtectedKey) {
            // Try to parse protected keys, but don't remove them even if parsing fails
            try {
              if (value) {
                JSON.parse(value);
                console.log(`✅ Validated protected LuvHive key: ${key}`);
              }
            } catch (parseError) {
              console.log(`⚠️ Protected key has invalid JSON but keeping: ${key}`);
            }
          } else {
            // For non-protected keys, remove if too large
            if (value && value.length > 50000) {
              console.log('Removing large localStorage item:', key);
              localStorage.removeItem(key);
            } else if (value) {
              // Try to parse and remove if corrupted
              JSON.parse(value);
            }
          }
        } catch (error) {
          // Only remove non-protected keys if corrupted
          const isProtectedKey = key.includes('luvhive_') || key.includes('luv_hive_') || 
                                key === 'luvhive_user' || key === 'luv_hive_user';
          if (!isProtectedKey) {
            console.log('Removing corrupted localStorage item:', key);
            localStorage.removeItem(key);
          } else {
            console.log(`⚠️ Corrupted but protected key preserved: ${key}`);
          }
        }
      }
    }
  } catch (error) {
    console.log('Error cleaning localStorage:', error);
    // If localStorage is completely corrupted, clear it
    try {
      localStorage.clear();
    } catch (clearError) {
      console.log('Could not clear localStorage');
    }
  }
};

// Clean up on app start
cleanupLocalStorage();

// Initialize Telegram WebApp if available with safe error handling
initTelegramWebApp();

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);