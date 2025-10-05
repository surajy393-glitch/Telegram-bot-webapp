// components/ui/Avatar.js (सरल संस्करण)
import React from 'react';

const Avatar = ({ user, size = 32 }) => {
  const baseSrc = user?.avatarUrl || user?.profilePic;
  const letter = user?.name?.[0]?.toUpperCase() || '?';
  
  // Add cache busting if avatar version exists
  const src = baseSrc && user?.avatarVersion ? 
    `${baseSrc}${baseSrc.includes('?') ? '&' : '?'}v=${user.avatarVersion}` : 
    baseSrc;
  
  return src ? (
    <img 
      src={src} 
      style={{ width: size, height: size }} 
      className="rounded-full object-cover" 
      alt={user?.name || 'User'}
      key={user?.avatarVersion || 0} // Force re-render on version change
      onError={(e) => {
        // Fallback to letter on image load error
        e.target.outerHTML = `
          <span 
            style="width: ${size}px; height: ${size}px" 
            class="rounded-full bg-gray-400 flex items-center justify-center text-white font-bold"
          >
            ${letter}
          </span>
        `;
      }}
    />
  ) : (
    <span 
      style={{ width: size, height: size }} 
      className="rounded-full bg-gray-400 flex items-center justify-center text-white font-bold"
    >
      {letter}
    </span>
  );
};

export default Avatar;