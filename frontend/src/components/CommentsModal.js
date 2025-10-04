import React, { useState, useEffect } from 'react';
import { X, Send, Heart } from 'lucide-react';

const CommentsModal = ({ post, currentUser, onClose, onAddComment }) => {
  const [commentText, setCommentText] = useState('');
  const [comments, setComments] = useState(post.comments || []);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!commentText.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      const newComment = {
        id: Date.now(),
        user: currentUser,
        text: commentText.trim(),
        createdAt: new Date(),
        likes: 0,
        timestamp: 'now'
      };

      // Add comment locally first
      setComments(prev => [...prev, newComment]);
      setCommentText('');

      // Call parent handler
      if (onAddComment) {
        await onAddComment(newComment);
      }

      if (window.Telegram?.WebApp?.showAlert) {
        window.Telegram.WebApp.showAlert('💬 Comment added successfully!');
      }
    } catch (error) {
      console.error('Error adding comment:', error);
      if (window.Telegram?.WebApp?.showAlert) {
        window.Telegram.WebApp.showAlert('❌ Failed to add comment. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const renderAvatar = (user) => {
    const avatarUrl = user.avatarUrl || user.profilePic;
    const displayLetter = user.name?.charAt(0).toUpperCase() || '👤';

    return avatarUrl ? (
      <img src={avatarUrl} alt={`${user.name} avatar`} className="w-8 h-8 rounded-full object-cover" />
    ) : (
      <div className="w-8 h-8 flex items-center justify-center rounded-full bg-gradient-to-r from-purple-400 to-pink-500 text-white text-sm font-bold">
        {displayLetter}
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-md h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold">Comments</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Comments List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {comments.length === 0 ? (
            <div className="text-center py-8">
              <div className="text-gray-400 text-4xl mb-2">💬</div>
              <p className="text-gray-500 text-sm">No comments yet</p>
              <p className="text-gray-400 text-xs">Be the first to comment!</p>
            </div>
          ) : (
            comments.map((comment) => (
              <div key={comment.id} className="flex space-x-3">
                {renderAvatar(comment.user)}
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold text-sm">{comment.user.name || comment.user.username}</span>
                    <span className="text-gray-400 text-xs">{comment.timestamp}</span>
                  </div>
                  <p className="text-sm text-gray-800 mt-1">{comment.text}</p>
                  <div className="flex items-center space-x-4 mt-2">
                    <button className="text-gray-400 hover:text-red-500 transition-colors flex items-center space-x-1">
                      <Heart size={12} />
                      <span className="text-xs">{comment.likes || 0}</span>
                    </button>
                    <button className="text-gray-400 hover:text-blue-500 text-xs">Reply</button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Comment Input */}
        <div className="border-t p-4">
          <form onSubmit={handleSubmit} className="flex space-x-3">
            {renderAvatar(currentUser)}
            <div className="flex-1 flex space-x-2">
              <input
                type="text"
                placeholder="Add a comment..."
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-full focus:outline-none focus:border-purple-500 text-sm"
                disabled={isSubmitting}
              />
              <button
                type="submit"
                disabled={!commentText.trim() || isSubmitting}
                className="px-4 py-2 bg-purple-500 text-white rounded-full hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Send size={16} />
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default CommentsModal;