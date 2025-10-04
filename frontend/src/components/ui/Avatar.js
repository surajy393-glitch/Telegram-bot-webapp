// components/ui/Avatar.js (सरल संस्करण)
import React from 'react';

const Avatar = ({ user, size = 32 }) => {
  const src = user?.avatarUrl || user?.profilePic;
  const letter = user?.name?.[0]?.toUpperCase() || '?';
  
  return src ? (
    <img 
      src={src} 
      style={{ width: size, height: size }} 
      className="rounded-full object-cover" 
      alt={user?.name || 'User'}
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