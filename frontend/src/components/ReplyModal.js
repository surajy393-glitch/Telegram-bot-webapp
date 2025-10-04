import React, { useState } from 'react';

const ReplyModal = ({ post, currentUser, onClose, onReply }) => {
  const [replyText, setReplyText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [replyType, setReplyType] = useState('text'); // 'text', 'spark', 'glow'

  const handleSubmit = async () => {
    const newReply = { text: replyText, createdAt: new Date(), user: currentUser };
    if (onReply) {
      await onReply(newReply);  // call parent handler
    }
    setReplyText('');
    onClose();
  };

  const quickReplies = [
    { emoji: '✨', text: 'Amazing vibe!' },
    { emoji: '💫', text: 'Love this!' },
    { emoji: '🌟', text: 'Incredible!' },
    { emoji: '💕', text: 'So beautiful!' },
    { emoji: '🔥', text: 'This is fire!' },
    { emoji: '💯', text: 'Perfect!' }
  ];

  const sparkTypes = [
    { id: 'spark', emoji: '✨', label: 'Send Spark', color: 'from-yellow-400 to-orange-500' },
    { id: 'glow', emoji: '💫', label: 'Send Glow', color: 'from-purple-400 to-pink-500' },
    { id: 'heart', emoji: '💕', label: 'Send Love', color: 'from-pink-400 to-red-500' }
  ];

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-end sm:items-center justify-center z-50">
      <div className="bg-white rounded-t-3xl sm:rounded-3xl w-full sm:max-w-md mx-4 max-h-[90vh] overflow-hidden animate-slide-up">
        {/* Header */}
        <div className="p-4 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-full overflow-hidden bg-gradient-to-r from-purple-400 to-pink-500 flex items-center justify-center">
                {(() => {
                  // Get proper avatar URL from user data
                  const avatarUrl = post.user.avatarUrl || post.user.profilePic || post.user.avatar_url;
                  const avatarEmoji = post.user.avatar;
                  const userName = post.user.name || 'User';
                  
                  // First priority: Use emoji if available and is a valid emoji (not string like 'L')
                  if (avatarEmoji && 
                      avatarEmoji.length <= 4 && 
                      avatarEmoji !== 'L' && 
                      avatarEmoji !== 'U' && 
                      /^[\u{1f600}-\u{1f64f}\u{1f300}-\u{1f5ff}\u{1f680}-\u{1f6ff}\u{1f1e0}-\u{1f1ff}\u{2600}-\u{26ff}\u{2700}-\u{27bf}]$/u.test(avatarEmoji)) {
                    return <span className="text-lg">{avatarEmoji}</span>;
                  }
                  // Second priority: Check for valid image URL
                  else if (avatarUrl && 
                          (avatarUrl.startsWith('http') || avatarUrl.startsWith('/') || avatarUrl.startsWith('data:')) &&
                          !avatarUrl.includes('avataaars/svg?') && 
                          !avatarUrl.includes('n/7.x/') &&
                          !avatarUrl.includes('undefined') &&
                          avatarUrl.length > 10) {
                    return (
                      <img 
                        src={avatarUrl} 
                        alt={userName} 
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          // Fallback to initials on image load error
                          e.target.style.display = 'none';
                          e.target.nextSibling.style.display = 'flex';
                        }}
                      />
                    );
                  } 
                  // Third priority: Generate initials from name
                  else {
                    const initials = userName.split(' ').map(n => n.charAt(0)).join('').substring(0, 2).toUpperCase();
                    return <span className="text-lg font-bold text-white">{initials || '👤'}</span>;
                  }
                })()}
                {/* Hidden fallback for image errors */}
                <span className="text-lg font-bold text-white" style={{ display: 'none' }}>
                  {post.user.name?.charAt(0)?.toUpperCase() || '👤'}
                </span>
              </div>
              <div>
                <h2 className="text-lg font-bold text-gray-800">Reply to {post.user.name || post.user.username || 'User'}</h2>
                <p className="text-sm text-gray-500">Share your thoughts on this post</p>
              </div>
            </div>
            <button
              onClick={onClose}
              disabled={isSubmitting}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <div className="p-4 overflow-y-auto max-h-[calc(90vh-160px)]">
          {/* Original Post Preview */}
          <div className="bg-gray-50 rounded-2xl p-4 mb-4">
            <div className="flex items-center space-x-3 mb-3">
              <div className="w-8 h-8 rounded-full bg-gradient-to-r from-purple-400 to-pink-500 flex items-center justify-center overflow-hidden">
                {(() => {
                  // Get proper avatar URL from user data
                  const avatarUrl = post.user.avatarUrl || post.user.profilePic || post.user.avatar_url;
                  const avatarEmoji = post.user.avatar;
                  const userName = post.user.name || 'User';
                  
                  // First priority: Use emoji if available and is a valid emoji (not string like 'L')
                  if (avatarEmoji && 
                      avatarEmoji.length <= 4 && 
                      avatarEmoji !== 'L' && 
                      avatarEmoji !== 'U' && 
                      /^[\u{1f600}-\u{1f64f}\u{1f300}-\u{1f5ff}\u{1f680}-\u{1f6ff}\u{1f1e0}-\u{1f1ff}\u{2600}-\u{26ff}\u{2700}-\u{27bf}]$/u.test(avatarEmoji)) {
                    return <span className="text-sm">{avatarEmoji}</span>;
                  }
                  // Second priority: Check for valid image URL
                  else if (avatarUrl && 
                          (avatarUrl.startsWith('http') || avatarUrl.startsWith('/') || avatarUrl.startsWith('data:')) &&
                          !avatarUrl.includes('avataaars/svg?') && 
                          !avatarUrl.includes('n/7.x/') &&
                          !avatarUrl.includes('undefined') &&
                          avatarUrl.length > 10) {
                    return (
                      <img 
                        src={avatarUrl} 
                        alt={userName} 
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          // Fallback to initials on image load error
                          e.target.style.display = 'none';
                          e.target.nextSibling.style.display = 'flex';
                        }}
                      />
                    );
                  } 
                  // Third priority: Generate initials from name
                  else {
                    const initials = userName.split(' ').map(n => n.charAt(0)).join('').substring(0, 2).toUpperCase();
                    return <span className="text-sm font-bold text-white">{initials || '👤'}</span>;
                  }
                })()}
                {/* Hidden fallback for image errors */}
                <span className="text-sm font-bold text-white" style={{ display: 'none' }}>
                  {post.user.name?.charAt(0)?.toUpperCase() || '👤'}
                </span>
              </div>
              <div>
                <p className="font-semibold text-gray-800">{post.user.name || post.user.username || 'User'}</p>
                <p className="text-xs text-gray-500">{post.timestamp}</p>
              </div>
            </div>
            <p className="text-gray-700 text-sm leading-relaxed line-clamp-3">
              {post.content}
            </p>
          </div>

          {/* Reply Type Selector */}
          <div className="flex bg-gray-100 rounded-2xl p-1 mb-4">
            <button
              onClick={() => setReplyType('text')}
              className={`flex-1 py-2 px-3 rounded-xl text-sm font-semibold transition-all ${
                replyType === 'text'
                  ? 'bg-white text-purple-600 shadow-md'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              💬 Text Reply
            </button>
            <button
              onClick={() => setReplyType('reaction')}
              className={`flex-1 py-2 px-3 rounded-xl text-sm font-semibold transition-all ${
                replyType === 'reaction'
                  ? 'bg-white text-purple-600 shadow-md'
                  : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              ✨ Quick React
            </button>
          </div>

          {replyType === 'text' && (
            <div className="space-y-4">
              {/* Text Input */}
              <div>
                <textarea
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  placeholder={`Share your thoughts on ${post.user.name}'s post...`}
                  className="w-full p-4 border border-gray-200 rounded-2xl resize-none focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  rows={4}
                  maxLength={280}
                  disabled={isSubmitting}
                />
                <div className="flex justify-between items-center mt-2">
                  <p className="text-xs text-gray-500">{replyText.length}/280 characters</p>
                  <div className="flex items-center space-x-2">
                    <button
                      type="button"
                      className="p-2 text-gray-400 hover:text-purple-500 rounded-full hover:bg-purple-50 transition-colors"
                      title="Add emoji"
                    >
                      😊
                    </button>
                    <button
                      type="button"
                      className="p-2 text-gray-400 hover:text-purple-500 rounded-full hover:bg-purple-50 transition-colors"
                      title="Add photo"
                    >
                      📷
                    </button>
                  </div>
                </div>
              </div>

              {/* Quick Reply Suggestions */}
              <div>
                <p className="text-sm font-semibold text-gray-600 mb-2">Quick replies:</p>
                <div className="flex flex-wrap gap-2">
                  {quickReplies.map((reply, index) => (
                    <button
                      key={index}
                      onClick={() => setReplyText(reply.text)}
                      className="flex items-center space-x-1 px-3 py-2 bg-purple-50 hover:bg-purple-100 text-purple-700 rounded-full text-sm font-medium transition-colors"
                      disabled={isSubmitting}
                    >
                      <span>{reply.emoji}</span>
                      <span>{reply.text}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {replyType === 'reaction' && (
            <div className="space-y-3">
              <p className="text-sm font-semibold text-gray-600 mb-3">Send a quick reaction:</p>
              {sparkTypes.map((spark) => (
                <button
                  key={spark.id}
                  onClick={() => {
                    setReplyText(`${spark.emoji} ${spark.label}!`);
                    setReplyType('text');
                  }}
                  disabled={isSubmitting}
                  className={`w-full flex items-center space-x-4 p-4 bg-gradient-to-r ${spark.color} text-white rounded-2xl hover:shadow-lg transform hover:scale-[1.02] transition-all disabled:opacity-50`}
                >
                  <div className="w-12 h-12 bg-white/20 rounded-full flex items-center justify-center">
                    <span className="text-2xl">{spark.emoji}</span>
                  </div>
                  <div className="text-left">
                    <h3 className="font-semibold">{spark.label}</h3>
                    <p className="text-sm opacity-90">Express your feelings instantly</p>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        {replyType === 'text' && (
          <div className="p-4 border-t border-gray-100">
            <div className="flex space-x-3">
              <button
                onClick={onClose}
                disabled={isSubmitting}
                className="flex-1 py-3 text-gray-600 font-semibold hover:bg-gray-50 rounded-2xl transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={isSubmitting || !replyText.trim()}
                className="flex-1 py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white font-semibold rounded-2xl hover:shadow-lg transform hover:scale-105 transition-all disabled:opacity-50 disabled:transform-none"
              >
                {isSubmitting ? (
                  <div className="flex items-center justify-center space-x-2">
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>Sending...</span>
                  </div>
                ) : (
                  '💬 Send Reply'
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ReplyModal;