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
 * Safely show a popup with buttons - with version compatibility
 * @param {object} params - Popup parameters
 */
export const showPopup = (params) => {
  try {
    const version = getTelegramWebAppVersion();
    
    // Check if showPopup is supported (version 6.1 and above)
    if (window.Telegram?.WebApp?.showPopup && 
        typeof window.Telegram.WebApp.showPopup === 'function' &&
        version && parseFloat(version) >= 6.1) {
      window.Telegram.WebApp.showPopup(params);
    } else {
      // Fallback for older versions or unavailable showPopup
      const message = params.message || params.title || 'Notification';
      
      if (params.buttons && params.buttons.length > 0) {
        // For buttons, use confirm for yes/no type popups
        const firstButton = params.buttons[0];
        if (params.buttons.length === 1 || firstButton.type === 'ok' || firstButton.type === 'close') {
          alert(message);
          if (firstButton.callback) {
            firstButton.callback();
          }
        } else {
          const result = confirm(message);
          const buttonIndex = result ? 0 : 1;
          const selectedButton = params.buttons[buttonIndex];
          if (selectedButton && selectedButton.callback) {
            selectedButton.callback();
          }
        }
      } else {
        alert(message);
      }
    }
  } catch (error) {
    console.log('Telegram WebApp showPopup error:', error);
    // Final fallback
    alert(params.message || params.title || 'Notification');
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