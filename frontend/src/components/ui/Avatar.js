// src/components/common/Avatar.jsx
export default function Avatar({ user, size = 40 }) {
  const v = user?.avatarVersion ?? 0;
  const base = user?.avatarUrl || user?.profilePic;
  
  // If no image URL, create fallback with user's initial or emoji
  if (!base || base === '/avatar-fallback.png') {
    const initial = user?.name?.[0]?.toUpperCase() || user?.username?.[0]?.toUpperCase() || '👤';
    return (
      <div 
        style={{ 
          width: size, 
          height: size, 
          borderRadius: '50%',
          backgroundColor: '#6366f1',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          fontSize: size * 0.4,
          fontWeight: 'bold'
        }}
      >
        {initial}
      </div>
    );
  }
  
  const src = `${base}${base.includes('?') ? '&' : '?'}v=${v}`;
  
  return (
    <img 
      src={src} 
      width={size} 
      height={size} 
      alt={user?.name || 'Profile'} 
      style={{ borderRadius: '50%' }}
      onError={(e) => {
        // On image load error, replace with initial fallback
        const initial = user?.name?.[0]?.toUpperCase() || user?.username?.[0]?.toUpperCase() || '👤';
        e.target.outerHTML = `<div style="width: ${size}px; height: ${size}px; border-radius: 50%; background: #6366f1; display: flex; align-items: center; justify-content: center; color: white; font-size: ${size * 0.4}px; font-weight: bold;">${initial}</div>`;
      }}
    />
  );
}