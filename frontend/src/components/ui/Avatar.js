import React from 'react';

const Avatar = ({ user, size = 'md', className = '' }) => {
  const sizes = {
    sm: 'w-8 h-8 text-sm',
    md: 'w-12 h-12 text-lg', 
    lg: 'w-16 h-16 text-xl',
    xl: 'w-20 h-20 text-2xl'
  };
  
  const sizeClasses = sizes[size] || sizes.md;
  
  // Get avatar URL with fallback priority
  const avatarUrl = user?.avatarUrl || user?.profilePic || user?.avatar_url;
  
  // Special handling for Luvsociety
  if (user?.name?.toLowerCase() === 'luvsociety') {
    return (
      <img 
        src="https://images.unsplash.com/photo-1614680376593-902f74cf0d41?w=200&h=200&fit=crop&crop=center"
        alt="Luvsociety" 
        className={`${sizeClasses} rounded-full object-cover ${className}`}
        onError={(e) => {
          e.target.src = 'https://ui-avatars.com/api/?name=Luvsociety&background=8b5cf6&color=fff&size=200&bold=true';
        }}
      />
    );
  }
  
  // Default avatar URL if no custom avatar
  const defaultAvatarUrl = `https://ui-avatars.com/api/?name=${encodeURIComponent(user?.name || 'User')}&background=random&color=fff&size=200`;
  
  return (
    <img 
      src={avatarUrl || defaultAvatarUrl}
      alt={`${user?.name || 'User'} avatar`} 
      className={`${sizeClasses} rounded-full object-cover ${className}`}
      onError={(e) => {
        // Fallback to default avatar service
        if (e.target.src !== defaultAvatarUrl) {
          e.target.src = defaultAvatarUrl;
        }
      }}
    />
  );
};

export default Avatar;