import React from 'react';

const Avatar = ({ user, size = 32 }) => {
  const src = user.avatarUrl || user.profilePic || '';
  const fallbackLetter = user.name?.[0]?.toUpperCase() || '?';
  
  // Special handling for Luvsociety - always show proper image
  if (user?.name?.toLowerCase() === 'luvsociety') {
    return (
      <img
        src="https://images.unsplash.com/photo-1614680376593-902f74cf0d41?w=200&h=200&fit=crop&crop=center"
        alt="Luvsociety"
        style={{ width: size, height: size }}
        className="rounded-full object-cover"
        onError={(e) => {
          // Fallback to a solid avatar for Luvsociety
          e.target.src = 'https://ui-avatars.com/api/?name=Luvsociety&background=8b5cf6&color=fff&size=200&bold=true';
        }}
      />
    );
  }
  
  return src ? (
    <img
      src={src}
      alt={user.name}
      style={{ width: size, height: size }}
      className="rounded-full object-cover"
      onError={(e) => {
        // On image error, replace with fallback letter
        e.target.outerHTML = `
          <span
            style="width: ${size}px; height: ${size}px"
            class="rounded-full bg-gray-400 flex items-center justify-center text-white font-bold"
          >
            ${fallbackLetter}
          </span>
        `;
      }}
    />
  ) : (
    <span
      style={{ width: size, height: size }}
      className="rounded-full bg-gray-400 flex items-center justify-center text-white font-bold"
    >
      {fallbackLetter}
    </span>
  );
};

export default Avatar;