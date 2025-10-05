import React from 'react';

const TabExplanation = ({ activeTab, onClose }) => {
  const tabExplanations = {
    following: {
      title: '💕 Following',
      description: 'Posts from people you connect with and follow',
      features: [
        'See updates from your connections',
        'Posts from people you\'ve sparked with',
        'Content from your favorite LuvHive members',
        'Personalized based on your interactions'
      ],
      icon: '💕'
    },
    discover: {
      title: '🔮 Discover',
      description: 'Find new people and content based on compatibility',
      features: [
        'AI-powered content recommendations',
        'Posts from highly compatible users',
        'Trending content in your area',
        'New members with similar interests'
      ],
      icon: '🔮'
    },
    vibes: {
      title: '🌈 Vibes',
      description: 'Content matching your current mood and energy',
      features: [
        'Posts filtered by emotional compatibility',
        'Content matching your current mood',
        'High vibe score posts (90%+)',
        'Positive energy and inspiration'
      ],
      icon: '🌈'
    },
    sparks: {
      title: '✨ Sparks',
      description: '24-hour ephemeral posts that disappear automatically',
      features: [
        'Time-limited authentic sharing',
        'More spontaneous and genuine content',
        'Posts that vanish after 24 hours',
        'Perfect for in-the-moment thoughts'
      ],
      icon: '✨'
    }
  };

  const currentTab = tabExplanations[activeTab];

  if (!currentTab) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <div className="text-3xl">{currentTab.icon}</div>
            <h2 className="text-xl font-bold text-gray-800">{currentTab.title}</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Description */}
        <p className="text-gray-600 text-lg mb-6 leading-relaxed">
          {currentTab.description}
        </p>

        {/* Features */}
        <div className="space-y-3 mb-6">
          <h3 className="font-semibold text-gray-800 mb-3">What you'll find here:</h3>
          {currentTab.features.map((feature, index) => (
            <div key={index} className="flex items-start space-x-3">
              <div className="w-6 h-6 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center mt-0.5 flex-shrink-0">
                <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" />
                </svg>
              </div>
              <p className="text-gray-700 text-sm leading-relaxed">{feature}</p>
            </div>
          ))}
        </div>

        {/* Close Button */}
        <button
          onClick={onClose}
          className="w-full bg-gradient-to-r from-purple-500 to-pink-500 text-white py-3 rounded-2xl font-semibold hover:shadow-lg transform hover:scale-105 transition-all duration-200"
        >
          Got it! ✨
        </button>
      </div>
    </div>
  );
};

export default TabExplanation;