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
          fontWeight: 'bold',
          flexShrink: 0,
          overflow: 'hidden'
        }}
      >
        {initial}
      </div>
    );
  }
  
  const src = `${base}${base.includes('?') ? '&' : '?'}v=${v}`;
  
  return (
    <div 
      style={{ 
        width: size, 
        height: size, 
        borderRadius: '50%',
        overflow: 'hidden',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
        backgroundColor: '#f3f4f6'
      }}
    >
      <img 
        src={src} 
        alt={user?.name || 'Profile'} 
        style={{ 
          width: '100%', 
          height: '100%', 
          objectFit: 'cover',
          borderRadius: '50%'
        }}
        onError={(e) => {
          // On image load error, replace with initial fallback - safer approach
          if (e.target && e.target.parentElement) {
            const initial = user?.name?.[0]?.toUpperCase() || user?.username?.[0]?.toUpperCase() || '👤';
            e.target.style.display = 'none';
            
            // Create fallback div
            const fallbackDiv = document.createElement('div');
            fallbackDiv.style.cssText = `width: 100%; height: 100%; border-radius: 50%; background: #6366f1; display: flex; align-items: center; justify-content: center; color: white; font-size: ${size * 0.4}px; font-weight: bold;`;
            fallbackDiv.textContent = initial;
            
            // Only replace if parent exists
            if (e.target.parentElement) {
              e.target.parentElement.appendChild(fallbackDiv);
            }
          }
        }}
      />
    </div>
  );
}