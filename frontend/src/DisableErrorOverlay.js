// Disable React error overlay completely
if (process.env.NODE_ENV === 'development') {
  const originalError = console.error;
  console.error = (...args) => {
    if (args[0]?.includes?.('validateDOMNesting')) {
      // Suppress DOM nesting warnings
      return;
    }
    originalError.apply(console, args);
  };

  // Disable webpack dev server error overlay
  if (typeof window !== 'undefined') {
    window.__webpack_dev_server_errors__ = [];
    
    // Override error handler
    window.addEventListener('error', (e) => {
      e.stopPropagation();
      e.preventDefault();
    });
    
    // Remove any existing error overlays
    const removeErrorOverlay = () => {
      const overlays = document.querySelectorAll('iframe[id*="webpack"], div[data-reactroot] div[style*="position: fixed"]');
      overlays.forEach(overlay => {
        if (overlay.style.zIndex > 1000 || overlay.id.includes('webpack')) {
          overlay.remove();
        }
      });
    };
    
    // Run immediately and periodically
    removeErrorOverlay();
    setInterval(removeErrorOverlay, 1000);
  }
}

export default {};