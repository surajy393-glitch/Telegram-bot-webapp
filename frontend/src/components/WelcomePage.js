import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const WelcomePage = ({ user, theme, onEnterLuvHive }) => {
  const navigate = useNavigate();
  const [currentFeature, setCurrentFeature] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);

  const features = [
    {
      icon: '💕',
      title: 'LuvConnect',
      description: 'Smart matching based on vibes, interests & emotional compatibility',
      color: 'from-pink-500 to-rose-600'
    },
    {
      icon: '🌟',
      title: 'VibeFeed',
      description: 'Discover content that matches your mood with AI-powered recommendations',
      color: 'from-purple-500 to-indigo-600'
    },
    {
      icon: '🔮',
      title: 'MoodSync',
      description: 'Share your feelings through dynamic mood indicators and find kindred spirits',
      color: 'from-blue-500 to-cyan-600'
    },
    {
      icon: '✨',
      title: 'SparkChats',
      description: 'Ephemeral conversations that disappear after 24 hours - pure authenticity',
      color: 'from-emerald-500 to-teal-600'
    },
    {
      icon: '🎭',
      title: 'AuraMatch',
      description: 'Personality-based matching using advanced psychological profiling',
      color: 'from-orange-500 to-red-600'
    }
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setIsAnimating(true);
      setTimeout(() => {
        setCurrentFeature((prev) => (prev + 1) % features.length);
        setIsAnimating(false);
      }, 200);
    }, 4000);

    return () => clearInterval(interval);
  }, [features.length]);

  const handleGetStarted = () => {
    const destination = onEnterLuvHive();
    navigate(destination);
  };

  const handleWhatsNew = () => {
    navigate('/whats-new');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-pink-500 via-purple-600 to-indigo-700 relative overflow-hidden">
      {/* Animated Background Elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-white/10 rounded-full blur-3xl animate-float"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-white/10 rounded-full blur-3xl animate-float delay-1000"></div>
        <div className="absolute top-1/2 left-1/2 w-40 h-40 bg-white/5 rounded-full blur-2xl animate-pulse-love"></div>
      </div>

      {/* Header */}
      <div className="relative z-10 bg-white/10 backdrop-blur-lg border-b border-white/20 px-6 py-4">
        <div className="flex items-center justify-center">
          <div className="animate-heart-beat text-3xl mr-3">💕</div>
          <h1 className="text-2xl font-bold text-white tracking-wide">LuvHive Social</h1>
        </div>
      </div>

      <div className="relative z-10 max-w-md mx-auto px-6 py-8">
        {/* Main Welcome Card */}
        <div className="bg-white/95 backdrop-blur-lg rounded-3xl p-8 shadow-2xl mb-8 relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-pink-500 via-purple-500 to-indigo-500"></div>
          
          {/* Welcome Header */}
          <div className="text-center mb-8">
            <div className="w-20 h-20 mx-auto mb-4 bg-gradient-to-r from-pink-500 to-purple-600 rounded-full flex items-center justify-center animate-pulse-love">
              <span className="text-3xl animate-heart-beat">💕</span>
            </div>
            <h2 className="text-3xl font-bold text-gray-800 mb-2">Welcome to LuvHive!</h2>
            <p className="text-gray-600 text-lg font-medium">Where Hearts Connect & Stories Unfold</p>
            {user && (
              <div className="mt-4 text-sm text-gray-500">
                Hello, {user.firstName}! 👋
              </div>
            )}
          </div>

          {/* Dynamic Feature Showcase */}
          <div className="mb-8">
            <div className={`transform transition-all duration-300 ${isAnimating ? 'scale-95 opacity-50' : 'scale-100 opacity-100'}`}>
              <div className={`p-6 rounded-2xl bg-gradient-to-r ${features[currentFeature].color} text-white mb-4`}>
                <div className="flex items-center space-x-4">
                  <div className="text-4xl animate-float">
                    {features[currentFeature].icon}
                  </div>
                  <div>
                    <h3 className="font-bold text-xl mb-1">{features[currentFeature].title}</h3>
                    <p className="text-white/90 text-sm">{features[currentFeature].description}</p>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Feature Indicators */}
            <div className="flex justify-center space-x-2">
              {features.map((_, index) => (
                <div
                  key={index}
                  className={`w-2 h-2 rounded-full transition-all duration-300 ${
                    index === currentFeature ? 'bg-purple-600 w-6' : 'bg-gray-300'
                  }`}
                />
              ))}
            </div>
          </div>

          {/* Platform Stats */}
          <div className="grid grid-cols-3 gap-4 mb-8">
            <div className="text-center p-4 bg-gradient-to-br from-pink-50 to-purple-50 rounded-xl">
              <div className="text-2xl font-bold text-pink-600 mb-1">25K+</div>
              <div className="text-xs text-gray-600">Active Users</div>
            </div>
            <div className="text-center p-4 bg-gradient-to-br from-purple-50 to-indigo-50 rounded-xl">
              <div className="text-2xl font-bold text-purple-600 mb-1">150K+</div>
              <div className="text-xs text-gray-600">Connections</div>
            </div>
            <div className="text-center p-4 bg-gradient-to-br from-indigo-50 to-blue-50 rounded-xl">
              <div className="text-2xl font-bold text-indigo-600 mb-1">500K+</div>
              <div className="text-xs text-gray-600">Moments</div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="space-y-4">
            <button
              onClick={handleGetStarted}
              className="w-full bg-gradient-to-r from-pink-500 to-purple-600 text-white py-4 rounded-2xl font-semibold text-lg shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-200 relative overflow-hidden"
            >
              <span className="relative z-10">🚀 Enter LuvHive</span>
              <div className="absolute inset-0 bg-gradient-to-r from-purple-600 to-pink-500 opacity-0 hover:opacity-100 transition-opacity duration-300"></div>
            </button>

            <button
              onClick={handleWhatsNew}
              className="w-full bg-white border-2 border-purple-200 text-purple-600 py-4 rounded-2xl font-semibold hover:bg-purple-50 transition-all duration-200 relative overflow-hidden group"
            >
              <span className="relative z-10">✨ What's New?</span>
              <div className="absolute inset-0 bg-gradient-to-r from-purple-100 to-pink-100 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
            </button>
          </div>
        </div>

        {/* Quick Features Preview */}
        <div className="text-center text-white/90 text-sm">
          <p className="mb-2">🎯 Smart Matching • 🌟 Mood-Based Feeds • ✨ Authentic Connections</p>
          <p className="text-white/70 text-xs">Your privacy is our priority • End-to-end encrypted chats</p>
        </div>
      </div>
    </div>
  );
};

export default WelcomePage;