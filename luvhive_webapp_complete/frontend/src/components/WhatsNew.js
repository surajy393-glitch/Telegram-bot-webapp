import React from 'react';
import { useNavigate } from 'react-router-dom';

const WhatsNew = ({ theme }) => {
  const navigate = useNavigate();

  const updates = [
    {
      version: '3.2.0',
      date: 'October 2025',
      badge: 'Latest',
      color: 'from-green-400 to-emerald-500',
      features: [
        {
          icon: '🧠',
          title: 'AI Personality Insights',
          description: 'Advanced AI analyzes your interactions to provide deep personality insights and better matching'
        },
        {
          icon: '🌈',
          title: 'Mood Spectrum',
          description: 'Express yourself with 50+ mood indicators and find people who vibe with your current energy'
        },
        {
          icon: '🎪',
          title: 'Virtual Hangouts',
          description: 'Create virtual spaces for group activities, games, and shared experiences'
        },
        {
          icon: '💫',
          title: 'Memory Capsules',
          description: 'Time-locked messages and photos that unlock based on special moments or dates'
        }
      ]
    },
    {
      version: '3.1.0',
      date: 'September 2025',
      badge: 'Previous',
      color: 'from-blue-400 to-indigo-500',
      features: [
        {
          icon: '🔮',
          title: 'Vibe Matching 2.0',
          description: 'Enhanced algorithm that matches based on energy levels, communication styles, and values'
        },
        {
          icon: '🎭',
          title: 'Anonymous Confessions',
          description: 'Share your deepest thoughts anonymously and connect with others through vulnerability'
        },
        {
          icon: '🌟',
          title: 'Spark Challenges',
          description: 'Daily interactive challenges to break the ice and create meaningful conversations'
        }
      ]
    },
    {
      version: '3.0.0',
      date: 'August 2025',
      badge: 'Major',
      color: 'from-purple-400 to-pink-500',
      features: [
        {
          icon: '💝',
          title: 'LuvHive Core Launch',
          description: 'Complete platform redesign with focus on authentic connections and emotional intelligence'
        },
        {
          icon: '🛡️',
          title: 'Advanced Privacy',
          description: 'Military-grade encryption and granular privacy controls for all interactions'
        },
        {
          icon: '🎨',
          title: 'Customizable Profiles',
          description: 'Express yourself with themes, animations, and interactive profile elements'
        }
      ]
    }
  ];

  const upcomingFeatures = [
    {
      icon: '🌍',
      title: 'Global Events',
      description: 'Join worldwide social events and meetups organized by the community',
      eta: 'November 2025'
    },
    {
      icon: '🎵',
      title: 'Music Sync',
      description: 'Share your current mood through music and discover people with similar taste',
      eta: 'December 2025'
    },
    {
      icon: '🤖',
      title: 'LuvBot Assistant',
      description: 'AI companion to help improve your social skills and relationship advice',
      eta: '2026 Q1'
    }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-600 relative overflow-hidden">
      {/* Animated Background */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-20 left-10 w-32 h-32 bg-white/5 rounded-full blur-xl animate-float"></div>
        <div className="absolute bottom-20 right-10 w-40 h-40 bg-white/5 rounded-full blur-xl animate-float delay-1000"></div>
        <div className="absolute top-1/3 right-1/4 w-24 h-24 bg-white/5 rounded-full blur-xl animate-pulse-love"></div>
      </div>

      {/* Header with Back Button */}
      <div className="relative z-10 bg-white/10 backdrop-blur-lg border-b border-white/20 px-4 py-4 flex items-center">
        <button
          onClick={() => navigate('/')}
          className="mr-4 p-2 rounded-full bg-white/20 hover:bg-white/30 transition-all duration-200 transform hover:scale-110 group"
        >
          <svg className="w-6 h-6 text-white group-hover:text-pink-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <div className="flex items-center">
          <div className="animate-heart-beat text-2xl mr-3">✨</div>
          <h1 className="text-xl font-bold text-white">What's New in LuvHive?</h1>
        </div>
      </div>

      <div className="relative z-10 max-w-md mx-auto px-4 py-6">
        <div className="space-y-6">
          {/* Current Version Highlight */}
          <div className="bg-white/95 backdrop-blur-lg rounded-3xl p-6 shadow-xl">
            <div className="flex items-center mb-4">
              <div className={`w-12 h-12 bg-gradient-to-r ${updates[0].color} rounded-full flex items-center justify-center mr-4 animate-pulse-love`}>
                <span className="text-2xl">🚀</span>
              </div>
              <div>
                <div className="flex items-center space-x-2 mb-1">
                  <h2 className="text-xl font-bold text-gray-800">Version {updates[0].version}</h2>
                  <span className="px-2 py-1 bg-green-100 text-green-800 text-xs font-semibold rounded-full">
                    {updates[0].badge}
                  </span>
                </div>
                <p className="text-sm text-gray-500">{updates[0].date} - Revolutionary Update!</p>
              </div>
            </div>
          </div>

          {/* Version Updates */}
          {updates.map((update, index) => (
            <div key={index} className="bg-white/95 backdrop-blur-lg rounded-3xl p-6 shadow-xl">
              <div className="flex items-center mb-4">
                <div className={`w-8 h-8 bg-gradient-to-r ${update.color} rounded-full flex items-center justify-center mr-3`}>
                  <span className="text-white text-sm font-bold">v{update.version.split('.')[1]}</span>
                </div>
                <div>
                  <h3 className="text-lg font-bold text-gray-800">Version {update.version}</h3>
                  <p className="text-sm text-gray-500">{update.date}</p>
                </div>
              </div>

              <div className="space-y-4">
                {update.features.map((feature, featureIndex) => (
                  <div key={featureIndex} className="flex items-start space-x-3">
                    <div className="w-8 h-8 bg-gradient-to-br from-purple-100 to-pink-100 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                      <span className="text-sm">{feature.icon}</span>
                    </div>
                    <div className="flex-1">
                      <h4 className="font-semibold text-gray-800 mb-1">{feature.title}</h4>
                      <p className="text-sm text-gray-600 leading-relaxed">{feature.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}

          {/* Coming Soon */}
          <div className="bg-gradient-to-r from-purple-500/20 to-pink-500/20 backdrop-blur-lg rounded-3xl p-6 shadow-xl border border-white/30">
            <h3 className="text-lg font-bold text-white mb-4 flex items-center">
              <span className="animate-pulse mr-2">🔮</span>
              Coming Soon
            </h3>
            <div className="space-y-4">
              {upcomingFeatures.map((feature, index) => (
                <div key={index} className="flex items-start space-x-3">
                  <div className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                    <span className="text-sm">{feature.icon}</span>
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-1">
                      <h4 className="font-semibold text-white">{feature.title}</h4>
                      <span className="px-2 py-1 bg-white/20 text-white text-xs rounded-full">
                        {feature.eta}
                      </span>
                    </div>
                    <p className="text-sm text-white/80 leading-relaxed">{feature.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Performance Stats */}
          <div className="bg-white/95 backdrop-blur-lg rounded-3xl p-6 shadow-xl">
            <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center">
              <span className="mr-2">⚡</span>
              Platform Improvements
            </h3>
            <div className="space-y-3">
              <div className="flex items-center space-x-3">
                <div className="w-6 h-6 bg-green-400 rounded-full flex items-center justify-center">
                  <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" />
                  </svg>
                </div>
                <p className="text-gray-700 text-sm">15x faster matching algorithm with AI optimization</p>
              </div>
              
              <div className="flex items-center space-x-3">
                <div className="w-6 h-6 bg-green-400 rounded-full flex items-center justify-center">
                  <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" />
                  </svg>
                </div>
                <p className="text-gray-700 text-sm">Real-time emotional analysis and compatibility scoring</p>
              </div>
              
              <div className="flex items-center space-x-3">
                <div className="w-6 h-6 bg-green-400 rounded-full flex items-center justify-center">
                  <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" />
                  </svg>
                </div>
                <p className="text-gray-700 text-sm">Zero data retention - complete privacy by design</p>
              </div>
              
              <div className="flex items-center space-x-3">
                <div className="w-6 h-6 bg-green-400 rounded-full flex items-center justify-center">
                  <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" />
                  </svg>
                </div>
                <p className="text-gray-700 text-sm">Cross-platform compatibility with seamless sync</p>
              </div>
            </div>
          </div>

          {/* Continue Button */}
          <button
            onClick={() => navigate('/')}
            className="w-full bg-gradient-to-r from-purple-500 to-pink-500 text-white py-4 rounded-2xl font-semibold text-lg shadow-lg hover:shadow-xl transform hover:scale-105 transition-all duration-200 relative overflow-hidden"
          >
            <span className="relative z-10">🚀 Experience LuvHive Now!</span>
            <div className="absolute inset-0 bg-gradient-to-r from-pink-500 to-purple-500 opacity-0 hover:opacity-100 transition-opacity duration-300"></div>
          </button>
        </div>
      </div>
    </div>
  );
};

export default WhatsNew;