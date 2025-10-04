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
          if (value && value.length > 50000) { // Remove very large items
            console.log('Removing large localStorage item:', key);
            localStorage.removeItem(key);
          }
          // Try to parse JSON to check if it's valid
          if (value && (key.includes('luvhive_') || key.includes('posts') || key.includes('stories'))) {
            JSON.parse(value);
          }
        } catch (error) {
          console.log('Removing corrupted localStorage item:', key);
          localStorage.removeItem(key);
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