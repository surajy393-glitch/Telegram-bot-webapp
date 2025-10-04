import React, { useState } from 'react';

const PostOptionsModal = ({ post, currentUser, onClose, onAction }) => {
  const [isProcessing, setIsProcessing] = useState(false);

  const handleAction = async (action) => {
    setIsProcessing(true);
    try {
      await onAction(action, post);
    } catch (error) {
      console.error('Error performing action:', error);
    } finally {
      setIsProcessing(false);
      onClose();
    }
  };

  const isOwnPost = currentUser && post.user.name === currentUser.name;

  const options = [
    {
      id: 'report',
      title: 'Report Post',
      icon: '🚨',
      color: 'text-red-600',
      bgColor: 'hover:bg-red-50',
      description: 'Report inappropriate content',
      show: !isOwnPost
    },
    {
      id: 'save',
      title: 'Save Post',
      icon: '💾',
      color: 'text-blue-600',
      bgColor: 'hover:bg-blue-50',
      description: 'Save to your collection',
      show: true
    },
    {
      id: 'hide',
      title: 'Hide Post',
      icon: '🙈',
      color: 'text-gray-600',
      bgColor: 'hover:bg-gray-50',
      description: 'Hide from your feed',
      show: !isOwnPost
    },
    {
      id: 'copy',
      title: 'Copy Link',
      icon: '🔗',
      color: 'text-purple-600',
      bgColor: 'hover:bg-purple-50',
      description: 'Copy post link to share',
      show: true
    },
    {
      id: 'block',
      title: isOwnPost ? 'Delete Post' : 'Block User',
      icon: isOwnPost ? '🗑️' : '🚫',
      color: 'text-red-600',
      bgColor: 'hover:bg-red-50',
      description: isOwnPost ? 'Permanently delete this post' : `Block ${post.user.name}`,
      show: true
    }
  ];

  const visibleOptions = options.filter(option => option.show);

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-end sm:items-center justify-center z-50">
      <div className="bg-white rounded-t-3xl sm:rounded-3xl w-full sm:max-w-md mx-4 overflow-hidden animate-slide-up">
        {/* Header */}
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-gray-800">Post Options</h2>
              <p className="text-sm text-gray-500">Choose an action for {post.user.name}'s post:</p>
            </div>
            <button
              onClick={onClose}
              disabled={isProcessing}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Options */}
        <div className="p-4 space-y-2">
          {visibleOptions.map((option) => (
            <button
              key={option.id}
              onClick={() => handleAction(option.id)}
              disabled={isProcessing}
              className={`w-full flex items-center space-x-4 p-4 rounded-2xl transition-all duration-200 ${option.bgColor} ${
                isProcessing ? 'opacity-50 cursor-not-allowed' : 'hover:shadow-md transform hover:scale-[1.02]'
              }`}
            >
              <div className="w-12 h-12 bg-white rounded-2xl flex items-center justify-center shadow-sm">
                <span className="text-xl">{option.icon}</span>
              </div>
              <div className="flex-1 text-left">
                <h3 className={`font-semibold ${option.color}`}>{option.title}</h3>
                <p className="text-sm text-gray-500">{option.description}</p>
              </div>
              {isProcessing && (
                <div className="w-6 h-6 border-2 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
              )}
            </button>
          ))}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-100">
          <button
            onClick={onClose}
            disabled={isProcessing}
            className="w-full py-3 text-gray-600 font-semibold hover:bg-gray-50 rounded-2xl transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};

export default PostOptionsModal;