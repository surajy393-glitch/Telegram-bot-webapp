import React, { useState } from 'react';

const Stories = ({ user, onClose, targetUser = null }) => {
  const [currentStoryIndex, setCurrentStoryIndex] = useState(0);
  const [progress, setProgress] = useState(0);

  // Get stories based on target user or use mock data
  const getStoriesData = () => {
    if (targetUser && targetUser.isOwn) {
      // Load user's own stories from localStorage
      const userStoriesKey = `luvhive_stories_${user?.username}`;
      const userStories = JSON.parse(localStorage.getItem(userStoriesKey) || '[]');
      return userStories.length > 0 ? userStories : [];
    }
    
    // Mock stories data for other users
    return [
    {
      id: 1,
      user: { name: 'Luna Starlight', username: 'luna_cosmic', avatar: '🌙', isOwn: false },
      content: {
        type: 'image',
        url: 'https://images.unsplash.com/photo-1519904981063-b0cf448d479e?w=400',
        text: 'Midnight meditation session 🧘‍♀️ Finding peace in the cosmos ✨'
      },
      timestamp: '2h ago',
      views: 23,
      mood: 'peaceful'
    },
    {
      id: 2,
      user: { name: 'River Phoenix', username: 'river_wild', avatar: '🌊', isOwn: false },
      content: {
        type: 'image',
        url: 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=400',
        text: 'Mountain sunrise captured my soul today 🏔️'
      },
      timestamp: '4h ago',
      views: 45,
      mood: 'adventurous'
    },
    {
      id: 3,
      user: { name: 'Nova Bright', username: 'nova_shine', avatar: '⭐', isOwn: false },
      content: {
        type: 'text',
        backgroundColor: 'from-pink-400 to-purple-600',
        text: 'Sometimes the universe whispers and sometimes it screams. Today it sang. 🎵'
      },
      timestamp: '6h ago',
      views: 67,
      mood: 'creative'
    }
    ];
  };

  const stories = getStoriesData();

  const currentStory = stories[currentStoryIndex];

  React.useEffect(() => {
    const timer = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          // Move to next story
          if (currentStoryIndex < stories.length - 1) {
            setCurrentStoryIndex(prev => prev + 1);
            return 0;
          } else {
            onClose();
            return 100;
          }
        }
        return prev + 2; // Progress every 100ms for 5 seconds
      });
    }, 100);

    return () => clearInterval(timer);
  }, [currentStoryIndex, stories.length, onClose]);

  const goToNextStory = () => {
    if (currentStoryIndex < stories.length - 1) {
      setCurrentStoryIndex(prev => prev + 1);
      setProgress(0);
    } else {
      onClose();
    }
  };

  const goToPrevStory = () => {
    if (currentStoryIndex > 0) {
      setCurrentStoryIndex(prev => prev - 1);
      setProgress(0);
    }
  };

  const getMoodColor = (mood) => {
    const colors = {
      peaceful: 'from-blue-400 to-green-500',
      adventurous: 'from-orange-400 to-red-500',
      creative: 'from-purple-400 to-pink-500',
      happy: 'from-yellow-400 to-orange-500'
    };
    return colors[mood] || 'from-gray-400 to-gray-600';
  };

  return (
    <div className="fixed inset-0 bg-black z-50 flex items-center justify-center">
      {/* Progress Bars */}
      <div className="absolute top-4 left-4 right-4 flex space-x-1">
        {stories.map((_, index) => (
          <div key={index} className="flex-1 h-1 bg-white/30 rounded-full overflow-hidden">
            <div
              className={`h-full bg-white transition-all duration-100 ${
                index === currentStoryIndex ? 'animate-pulse' : ''
              }`}
              style={{
                width: index === currentStoryIndex ? `${progress}%` : index < currentStoryIndex ? '100%' : '0%'
              }}
            />
          </div>
        ))}
      </div>

      {/* Close Button */}
      <button
        onClick={onClose}
        className="absolute top-4 right-4 p-2 bg-black/50 text-white rounded-full hover:bg-black/70 transition-colors z-10"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      {/* Story Content */}
      <div className="relative w-full h-full max-w-md mx-auto">
        {/* Navigation Areas */}
        <button
          onClick={goToPrevStory}
          className="absolute left-0 top-0 w-1/3 h-full z-10 opacity-0"
          disabled={currentStoryIndex === 0}
        />
        <button
          onClick={goToNextStory}
          className="absolute right-0 top-0 w-1/3 h-full z-10 opacity-0"
        />

        {/* Story Background */}
        {currentStory.content.type === 'image' ? (
          <div className="relative h-full">
            <img
              src={currentStory.content.url}
              alt="Story"
              className="w-full h-full object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/30" />
          </div>
        ) : (
          <div className={`h-full bg-gradient-to-br ${currentStory.content.backgroundColor} flex items-center justify-center p-8`}>
            <p className="text-white text-2xl font-bold text-center leading-relaxed">
              {currentStory.content.text}
            </p>
          </div>
        )}

        {/* Story Text Overlay for Image Stories */}
        {currentStory.content.type === 'image' && currentStory.content.text && (
          <div className="absolute bottom-24 left-0 right-0 px-6">
            <p className="text-white text-lg font-medium text-center leading-relaxed shadow-lg">
              {currentStory.content.text}
            </p>
          </div>
        )}

        {/* User Info */}
        <div className="absolute top-16 left-4 right-4 flex items-center space-x-3">
          <div className={`w-12 h-12 rounded-full flex items-center justify-center bg-gradient-to-r ${getMoodColor(currentStory.mood)} shadow-lg`}>
            <span className="text-2xl">{currentStory.user.avatar}</span>
          </div>
          <div className="flex-1">
            <h3 className="text-white font-semibold text-lg drop-shadow-lg">{currentStory.user.name}</h3>
            <div className="flex items-center space-x-2">
              <p className="text-white/80 text-sm">@{currentStory.user.username}</p>
              <span className="text-white/60 text-sm">•</span>
              <p className="text-white/60 text-sm">{currentStory.timestamp}</p>
            </div>
          </div>
        </div>

        {/* Views Count - Bottom Position */}
        <div className="absolute bottom-2 left-4 flex items-center space-x-1 bg-black/40 px-3 py-1 rounded-full backdrop-blur-sm">
          <svg className="w-4 h-4 text-white/80" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
          <span className="text-white text-sm font-medium">{currentStory.views || 0} views</span>
        </div>

        {/* Reaction Bar - Only for OTHER users' stories */}
        {!currentStory.user.isOwn && (
          <div className="absolute bottom-12 left-4 right-4 flex items-center space-x-3">
            <div className="flex-1 flex items-center space-x-2 bg-black/30 rounded-full px-4 py-3 backdrop-blur-sm">
              <button className="p-2 hover:bg-white/20 rounded-full transition-colors">
                <span className="text-2xl">✨</span>
              </button>
              <button className="p-2 hover:bg-white/20 rounded-full transition-colors">
                <span className="text-2xl">💫</span>
              </button>
              <button className="p-2 hover:bg-white/20 rounded-full transition-colors">
                <span className="text-2xl">🔥</span>
              </button>
              <input
                type="text"
                placeholder="Reply to story..."
                className="flex-1 bg-transparent text-white placeholder-white/70 text-sm outline-none"
              />
            </div>
          </div>
        )}

        {/* Own Story Options - Only for user's own stories */}
        {currentStory.user.isOwn && (
          <div className="absolute bottom-12 right-4 flex items-center space-x-2">
            <button className="p-3 bg-black/40 hover:bg-black/60 rounded-full backdrop-blur-sm transition-colors">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
              </svg>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Stories;