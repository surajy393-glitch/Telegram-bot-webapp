import React, { useState } from 'react';

const ShareModal = ({ post, currentUser, onClose }) => {
  const [shareMethod, setShareMethod] = useState('social'); // 'social' or 'premium'
  const [isSharing, setIsSharing] = useState(false);
  const [shareStatus, setShareStatus] = useState('');

  const postUrl = `${window.location.origin}/post/${post.id}`;
  const shareText = `Check out this amazing post by ${post.user.name} on LuvHive! 🌟\n\n"${post.content.substring(0, 100)}${post.content.length > 100 ? '...' : ''}"\n\n`;

  const socialPlatforms = [
    {
      id: 'telegram',
      name: 'Telegram',
      icon: '💬',
      color: 'from-blue-400 to-blue-600',
      action: () => handleTelegramShare()
    },
    {
      id: 'whatsapp',
      name: 'WhatsApp',
      icon: '📱',
      color: 'from-green-400 to-green-600',
      action: () => handleWhatsAppShare()
    },
    {
      id: 'instagram',
      name: 'Instagram',
      icon: '📸',
      color: 'from-purple-400 to-pink-500',
      action: () => handleInstagramShare()
    },
    {
      id: 'snapchat',
      name: 'Snapchat',
      icon: '👻',
      color: 'from-yellow-400 to-yellow-600',
      action: () => handleSnapchatShare()
    }
  ];

  const handleTelegramShare = async () => {
    setIsSharing(true);
    setShareStatus('Sharing to Telegram...');
    
    try {
      const telegramUrl = `https://t.me/share/url?url=${encodeURIComponent(postUrl)}&text=${encodeURIComponent(shareText)}`;
      
      if (window.Telegram?.WebApp) {
        // If in Telegram WebApp, use native sharing
        try {
          if (window.Telegram.WebApp.openTelegramLink) {
            window.Telegram.WebApp.openTelegramLink(telegramUrl);
          } else {
            window.open(telegramUrl, '_blank', 'noopener,noreferrer');
          }
        } catch (telegramError) {
          console.log('Telegram WebApp error:', telegramError);
          // Fallback to regular window.open
          window.open(telegramUrl, '_blank', 'noopener,noreferrer');
        }
      } else {
        window.open(telegramUrl, '_blank', 'noopener,noreferrer');
      }
      
      setShareStatus('✅ Shared to Telegram!');
      setTimeout(() => onClose(), 1500);
    } catch (error) {
      console.log('Telegram share error:', error);
      setShareStatus('❌ Error sharing to Telegram');
      setTimeout(() => setShareStatus(''), 2000);
    } finally {
      setIsSharing(false);
    }
  };

  const handleWhatsAppShare = async () => {
    setIsSharing(true);
    setShareStatus('Sharing to WhatsApp...');
    
    try {
      const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(shareText + postUrl)}`;
      window.open(whatsappUrl, '_blank');
      
      setShareStatus('✅ Shared to WhatsApp!');
      setTimeout(() => onClose(), 1500);
    } catch (error) {
      setShareStatus('❌ Error sharing to WhatsApp');
      setTimeout(() => setShareStatus(''), 2000);
    } finally {
      setIsSharing(false);
    }
  };

  const handleInstagramShare = async () => {
    setIsSharing(true);
    setShareStatus('Opening Instagram...');
    
    try {
      // Copy to clipboard for Instagram with feature detection
      const textToCopy = shareText + postUrl;
      
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(textToCopy);
      } else {
        // Fallback clipboard method
        const textArea = document.createElement('textarea');
        textArea.value = textToCopy;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
      }
      
      // Try to open Instagram app safely
      try {
        const instagramUrl = 'instagram://';
        const iframe = document.createElement('iframe');
        iframe.style.display = 'none';
        iframe.src = instagramUrl;
        document.body.appendChild(iframe);
        
        // Clean up and fallback to web after short delay
        setTimeout(() => {
          document.body.removeChild(iframe);
          window.open('https://instagram.com', '_blank', 'noopener,noreferrer');
        }, 1000);
      } catch (appError) {
        console.log('Instagram app open error:', appError);
        // Direct fallback to web
        window.open('https://instagram.com', '_blank', 'noopener,noreferrer');
      }
      
      setShareStatus('✅ Link copied! Paste it in Instagram');
      setTimeout(() => onClose(), 2000);
    } catch (error) {
      console.log('Instagram share error:', error);
      setShareStatus('❌ Please copy link manually for Instagram');
      setTimeout(() => setShareStatus(''), 2000);
    } finally {
      setIsSharing(false);
    }
  };

  const handleSnapchatShare = async () => {
    setIsSharing(true);
    setShareStatus('Opening Snapchat...');
    
    try {
      // Copy to clipboard for Snapchat with feature detection
      const textToCopy = shareText + postUrl;
      
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(textToCopy);
      } else {
        // Fallback clipboard method
        const textArea = document.createElement('textarea');
        textArea.value = textToCopy;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
      }
      
      // Try to open Snapchat app safely
      try {
        const snapchatUrl = 'snapchat://';
        const iframe = document.createElement('iframe');
        iframe.style.display = 'none';
        iframe.src = snapchatUrl;
        document.body.appendChild(iframe);
        
        // Clean up and fallback to web after short delay
        setTimeout(() => {
          document.body.removeChild(iframe);
          window.open('https://snapchat.com', '_blank', 'noopener,noreferrer');
        }, 1000);
      } catch (appError) {
        console.log('Snapchat app open error:', appError);
        // Direct fallback to web
        window.open('https://snapchat.com', '_blank', 'noopener,noreferrer');
      }
      
      setShareStatus('✅ Link copied! Paste it in Snapchat');
      setTimeout(() => onClose(), 2000);
    } catch (error) {
      console.log('Snapchat share error:', error);
      setShareStatus('❌ Please copy link manually for Snapchat');
      setTimeout(() => setShareStatus(''), 2000);
    } finally {
      setIsSharing(false);
    }
  };

  const handlePremiumShare = async (targetUser) => {
    setIsSharing(true);
    setShareStatus(`Sharing with ${targetUser}...`);
    
    try {
      // Simulate premium user sharing
      setTimeout(() => {
        setShareStatus(`✅ Shared with ${targetUser}!`);
        setTimeout(() => onClose(), 1500);
      }, 1000);
    } catch (error) {
      setShareStatus('❌ Error sharing with premium user');
      setTimeout(() => setShareStatus(''), 2000);
    } finally {
      setIsSharing(false);
    }
  };

  const handleCopyLink = async () => {
    try {
      // Feature detection for clipboard API
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(postUrl);
        setShareStatus('✅ Link copied to clipboard!');
      } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = postUrl;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        setShareStatus('✅ Link copied to clipboard!');
      }
      setTimeout(() => setShareStatus(''), 2000);
    } catch (error) {
      console.log('Copy fallback:', error);
      setShareStatus('❌ Failed to copy link');
      setTimeout(() => setShareStatus(''), 2000);
    }
  };

  const handleNativeShare = async () => {
    // Feature detection for Web Share API
    if (navigator.share && navigator.canShare && navigator.canShare({
      title: `${post.user.name} on LuvHive`,
      text: shareText,
      url: postUrl
    })) {
      try {
        setIsSharing(true);
        await navigator.share({
          title: `${post.user.name} on LuvHive`,
          text: shareText,
          url: postUrl
        });
        setShareStatus('✅ Shared successfully!');
        setTimeout(() => onClose(), 1500);
      } catch (error) {
        console.log('Share API error:', error);
        if (error.name !== 'AbortError') {
          setShareStatus('❌ Sharing failed');
          setTimeout(() => setShareStatus(''), 2000);
        }
      } finally {
        setIsSharing(false);
      }
    } else {
      // Fallback to copy link if native sharing not available
      handleCopyLink();
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-end sm:items-center justify-center z-50">
      <div className="bg-white rounded-t-3xl sm:rounded-3xl w-full sm:max-w-md mx-4 max-h-[90vh] overflow-hidden animate-slide-up">
        {/* Header */}
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-gray-800">Share Post</h2>
              <p className="text-sm text-gray-500">Share {post.user.name}'s post with others</p>
            </div>
            <button
              onClick={onClose}
              disabled={isSharing}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <div className="p-4 overflow-y-auto max-h-[calc(90vh-120px)]">
          {/* Status Message */}
          {shareStatus && (
            <div className="mb-4 p-3 bg-purple-50 border border-purple-200 rounded-2xl">
              <p className="text-sm text-purple-800 text-center font-medium">{shareStatus}</p>
            </div>
          )}

          {/* Share Method Toggle */}
          <div className="flex bg-gray-100 rounded-2xl p-1 mb-6">
            <button
              onClick={() => setShareMethod('social')}
              className={`flex-1 py-2 px-4 rounded-xl text-sm font-semibold transition-all ${
                shareMethod === 'social'
                  ? 'bg-white text-purple-600 shadow-md'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              📱 Social Media
            </button>
            <button
              onClick={() => setShareMethod('premium')}
              className={`flex-1 py-2 px-4 rounded-xl text-sm font-semibold transition-all ${
                shareMethod === 'premium'
                  ? 'bg-white text-purple-600 shadow-md'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              💎 Premium Users
            </button>
          </div>

          {shareMethod === 'social' && (
            <div className="space-y-3">
              {/* Quick Actions */}
              <div className="grid grid-cols-2 gap-3 mb-4">
                {(navigator.share || navigator.clipboard || document.execCommand) && (
                  <button
                    onClick={handleNativeShare}
                    disabled={isSharing}
                    className="flex items-center justify-center space-x-2 p-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-2xl hover:shadow-lg transform hover:scale-105 transition-all disabled:opacity-50"
                  >
                    <span>📤</span>
                    <span className="font-semibold">
                      {navigator.share ? 'Share' : 'Copy Link'}
                    </span>
                  </button>
                )}
                <button
                  onClick={handleCopyLink}
                  disabled={isSharing}
                  className="flex items-center justify-center space-x-2 p-3 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-2xl transition-all disabled:opacity-50"
                >
                  <span>🔗</span>
                  <span className="font-semibold">Copy Link</span>
                </button>
              </div>

              {/* Social Platforms */}
              <div className="space-y-2">
                <h3 className="text-sm font-semibold text-gray-600 mb-2">Share to social media:</h3>
                {socialPlatforms.map((platform) => (
                  <button
                    key={platform.id}
                    onClick={platform.action}
                    disabled={isSharing}
                    className={`w-full flex items-center space-x-4 p-4 bg-gradient-to-r ${platform.color} text-white rounded-2xl hover:shadow-lg transform hover:scale-[1.02] transition-all disabled:opacity-50`}
                  >
                    <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
                      <span className="text-xl">{platform.icon}</span>
                    </div>
                    <span className="font-semibold">Share to {platform.name}</span>
                    {isSharing && (
                      <div className="ml-auto w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          {shareMethod === 'premium' && (
            <div className="space-y-3">
              <div className="text-center py-8">
                <div className="w-16 h-16 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-2xl text-white">💎</span>
                </div>
                <h3 className="text-lg font-bold text-gray-800 mb-2">Premium Sharing</h3>
                <p className="text-gray-600 text-sm mb-4">
                  Share directly with other premium users who match your interests and vibes!
                </p>
                
                {currentUser?.isPremium ? (
                  <div className="space-y-2">
                    {['Alex Dream', 'Luna Starlight', 'Nova Bright'].map((user) => (
                      <button
                        key={user}
                        onClick={() => handlePremiumShare(user)}
                        disabled={isSharing}
                        className="w-full flex items-center space-x-3 p-3 bg-gradient-to-r from-purple-50 to-pink-50 rounded-2xl hover:from-purple-100 hover:to-pink-100 transition-all disabled:opacity-50"
                      >
                        <div className="w-10 h-10 bg-gradient-to-r from-purple-400 to-pink-500 rounded-full flex items-center justify-center">
                          <span className="text-white">👤</span>
                        </div>
                        <div className="text-left">
                          <p className="font-semibold text-gray-800">{user}</p>
                          <p className="text-xs text-gray-500">Premium Member • 98% match</p>
                        </div>
                        <div className="ml-auto text-purple-500">💎</div>
                      </button>
                    ))}
                  </div>
                ) : (
                  <button
                    onClick={() => {
                      if (window.Telegram?.WebApp?.showAlert) {
                        window.Telegram.WebApp.showAlert(
                          "💎 Upgrade to Premium\n\n" +
                          "Get access to:\n" +
                          "• Direct sharing with premium users\n" +
                          "• Advanced matching algorithms\n" +
                          "• Unlimited chat features\n" +
                          "• Priority customer support\n\n" +
                          "Upgrade now in the LuvHive bot!"
                        );
                      }
                    }}
                    className="w-full py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-2xl font-semibold hover:shadow-lg transform hover:scale-105 transition-all"
                  >
                    💎 Upgrade to Premium
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ShareModal;