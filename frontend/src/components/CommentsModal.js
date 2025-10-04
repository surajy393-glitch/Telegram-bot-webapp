import React, { useState, useEffect } from 'react';
import { X, Send, Heart, MessageCircle, Sparkles } from 'lucide-react';
import Avatar from './ui/Avatar';

const CommentsModal = ({ post, currentUser, onClose, onAddComment }) => {
  const [commentText, setCommentText] = useState('');
  const [comments, setComments] = useState(post.comments || []);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [likedComments, setLikedComments] = useState(new Set());

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

      // Add comment locally first with animation
      setComments(prev => [...prev, newComment]);
      setCommentText('');

      // Call parent handler
      if (onAddComment) {
        await onAddComment(newComment);
      }

      // Vibration feedback
      if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.impactOccurred('light');
      }
    } catch (error) {
      console.error('Error adding comment:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLikeComment = (commentId) => {
    setLikedComments(prev => {
      const newSet = new Set(prev);
      if (newSet.has(commentId)) {
        newSet.delete(commentId);
      } else {
        newSet.add(commentId);
      }
      return newSet;
    });
    
    setComments(prev => prev.map(comment => 
      comment.id === commentId 
        ? { 
            ...comment, 
            likes: likedComments.has(commentId) 
              ? Math.max(0, comment.likes - 1) 
              : comment.likes + 1 
          }
        : comment
    ));
  };

  const renderAvatar = (user) => {
    return (
      <div className="relative">
        <Avatar user={user} size={40} />
        <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-green-400 rounded-full border-2 border-white"></div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-60 flex items-end sm:items-center justify-center z-50 p-0 sm:p-4">
      <div className="bg-white rounded-t-3xl sm:rounded-2xl w-full sm:max-w-lg h-[90vh] sm:h-[85vh] flex flex-col shadow-2xl">
        {/* Animated Header */}
        <div className="relative bg-gradient-to-r from-purple-600 to-pink-600 p-6 rounded-t-3xl sm:rounded-t-2xl">
          <div className="absolute inset-0 bg-white opacity-10 rounded-t-3xl sm:rounded-t-2xl"></div>
          <div className="relative flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <MessageCircle className="text-white" size={24} />
              <div>
                <h2 className="text-lg font-bold text-white">Comments</h2>
                <p className="text-purple-100 text-sm">{comments.length} {comments.length === 1 ? 'comment' : 'comments'}</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white hover:bg-opacity-20 rounded-full transition-all duration-200 text-white"
            >
              <X size={22} />
            </button>
          </div>
          <div className="absolute -bottom-2 left-1/2 transform -translate-x-1/2 w-8 h-1 bg-white rounded-full opacity-30"></div>
        </div>

        {/* Comments List with Custom Scrollbar */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
          {comments.length === 0 ? (
            <div className="text-center py-12">
              <div className="relative mb-6">
                <MessageCircle className="text-gray-300 mx-auto" size={64} />
                <Sparkles className="text-purple-400 absolute top-2 right-6 animate-pulse" size={20} />
              </div>
              <h3 className="text-gray-600 text-lg font-semibold mb-2">No comments yet</h3>
              <p className="text-gray-400 text-sm">Be the first to share your thoughts! ✨</p>
            </div>
          ) : (
            comments.map((comment, index) => (
              <div key={comment.id} className={`flex space-x-3 p-3 rounded-xl hover:bg-gray-50 transition-all duration-300 transform hover:scale-[1.02] ${index === comments.length - 1 ? 'animate-slideIn' : ''}`}>
                {renderAvatar(comment.user)}
                <div className="flex-1 min-w-0">
                  <div className="bg-gray-100 rounded-2xl px-4 py-3">
                    <div className="flex items-center space-x-2 mb-1">
                      <span className="font-bold text-sm text-gray-800">{comment.user.name || comment.user.username}</span>
                      <span className="text-gray-400 text-xs">{comment.timestamp}</span>
                    </div>
                    <p className="text-sm text-gray-700 leading-relaxed">{comment.text}</p>
                  </div>
                  <div className="flex items-center space-x-6 mt-2 ml-2">
                    <button 
                      onClick={() => handleLikeComment(comment.id)}
                      className={`flex items-center space-x-1 transition-all duration-200 ${
                        likedComments.has(comment.id) 
                          ? 'text-red-500 scale-110' 
                          : 'text-gray-400 hover:text-red-500'
                      }`}
                    >
                      <Heart 
                        size={14} 
                        fill={likedComments.has(comment.id) ? 'currentColor' : 'none'}
                        className="transition-all duration-200"
                      />
                      <span className="text-xs font-medium">{comment.likes || 0}</span>
                    </button>
                    <button className="text-gray-400 hover:text-purple-500 text-xs font-medium transition-colors">
                      Reply
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Modern Comment Input */}
        <div className="bg-gray-50 border-t p-4">
          <form onSubmit={handleSubmit} className="flex space-x-3">
            {renderAvatar(currentUser)}
            <div className="flex-1 flex space-x-2">
              <div className="relative flex-1">
                <input
                  type="text"
                  placeholder="Share your thoughts..."
                  value={commentText}
                  onChange={(e) => setCommentText(e.target.value)}
                  className="w-full px-4 py-3 bg-white border-2 border-gray-200 rounded-2xl focus:outline-none focus:border-purple-400 text-sm transition-all duration-200 pr-12"
                  disabled={isSubmitting}
                />
                <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                  <div className="text-gray-300 text-xs">
                    {commentText.length}/500
                  </div>
                </div>
              </div>
              <button
                type="submit"
                disabled={!commentText.trim() || isSubmitting}
                className="px-5 py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-2xl hover:from-purple-600 hover:to-pink-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 transform active:scale-95 shadow-lg hover:shadow-xl"
              >
                {isSubmitting ? (
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                ) : (
                  <Send size={18} />
                )}
              </button>
            </div>
          </form>
        </div>
      </div>

      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: #f1f1f1;
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: linear-gradient(to bottom, #8b5cf6, #ec4899);
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: linear-gradient(to bottom, #7c3aed, #db2777);
        }
        
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        .animate-slideIn {
          animation: slideIn 0.3s ease-out;
        }
      `}</style>
    </div>
  );
};

export default CommentsModal;