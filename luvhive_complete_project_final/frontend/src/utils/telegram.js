// Telegram WebApp utility functions with compatibility checks

/**
 * Safely show an alert message with fallback to standard alert
 * @param {string} message - The message to display
 */
export const showAlert = (message) => {
  try {
    if (window.Telegram?.WebApp?.showAlert && 
        typeof window.Telegram.WebApp.showAlert === 'function') {
      window.Telegram.WebApp.showAlert(message);
    } else {
      alert(message);
    }
  } catch (error) {
    console.log('Telegram WebApp showAlert error:', error);
    alert(message); // Fallback to standard alert
  }
};

/**
 * Safely show a confirm dialog with callback
 * @param {string} message - The confirmation message
 * @param {function} callback - Callback function with boolean result
 */
export const showConfirm = (message, callback) => {
  try {
    if (window.Telegram?.WebApp?.showConfirm && 
        typeof window.Telegram.WebApp.showConfirm === 'function') {
      window.Telegram.WebApp.showConfirm(message, callback);
    } else {
      // eslint-disable-next-line no-restricted-globals
      const result = confirm(message);
      callback(result);
    }
  } catch (error) {
    console.log('Telegram WebApp showConfirm error:', error);
    // eslint-disable-next-line no-restricted-globals
    const result = confirm(message);
    callback(result);
  }
};

/**
 * Check if running in Telegram WebApp environment
 * @returns {boolean}
 */
export const isTelegramWebApp = () => {
  return !!(window.Telegram?.WebApp);
};

/**
 * Get Telegram WebApp version if available
 * @returns {string|null}
 */
export const getTelegramWebAppVersion = () => {
  return window.Telegram?.WebApp?.version || null;
};

/**
 * Safely close Telegram WebApp with fallback
 */
export const closeTelegramWebApp = () => {
  try {
    if (window.Telegram?.WebApp?.close && 
        typeof window.Telegram.WebApp.close === 'function') {
      window.Telegram.WebApp.close();
    } else {
      // Fallback: try to redirect to bot or show message
      window.open('https://t.me/LuvHiveBot', '_blank', 'noopener,noreferrer');
    }
  } catch (error) {
    console.log('Telegram WebApp close error:', error);
    window.open('https://t.me/LuvHiveBot', '_blank', 'noopener,noreferrer');
  }
};

/**
 * Safely open Telegram link
 * @param {string} url - The Telegram URL to open
 */
export const openTelegramLink = (url) => {
  try {
    if (window.Telegram?.WebApp?.openTelegramLink && 
        typeof window.Telegram.WebApp.openTelegramLink === 'function') {
      window.Telegram.WebApp.openTelegramLink(url);
    } else {
      window.open(url, '_blank', 'noopener,noreferrer');
    }
  } catch (error) {
    console.log('Telegram WebApp openTelegramLink error:', error);
    window.open(url, '_blank', 'noopener,noreferrer');
  }
};

/**
 * Initialize Telegram WebApp with error handling
 */
export const initTelegramWebApp = () => {
  try {
    if (window.Telegram?.WebApp) {
      const tg = window.Telegram.WebApp;
      
      // Safely call ready
      if (typeof tg.ready === 'function') {
        tg.ready();
      }
      
      // Safely expand
      if (typeof tg.expand === 'function') {
        tg.expand();
      }
      
      // Hide buttons safely
      if (tg.MainButton && typeof tg.MainButton.hide === 'function') {
        tg.MainButton.hide();
      }
      
      if (tg.BackButton && typeof tg.BackButton.hide === 'function') {
        tg.BackButton.hide();
      }
    }
  } catch (error) {
    console.log('Telegram WebApp initialization error:', error);
  }
};