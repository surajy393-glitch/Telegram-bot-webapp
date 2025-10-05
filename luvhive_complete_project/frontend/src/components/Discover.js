import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const Discover = ({ user, theme }) => {
  const navigate = useNavigate();
  const [activeFilter, setActiveFilter] = useState('all');

  const filters = [
    { id: 'all', label: 'All', icon: '🌟' },
    { id: 'nearby', label: 'Nearby', icon: '📍' },
    { id: 'compatible', label: 'Compatible', icon: '💕' },
    { id: 'trending', label: 'Trending', icon: '🔥' }
  ];

  const discoverItems = [
    {
      id: 1,
      type: 'person',
      name: 'Luna Starlight',
      username: '@luna_cosmic',
      avatar: '🌙',
      bio: 'Spiritual seeker & midnight philosopher',
      compatibility: 94,
      commonInterests: ['Meditation', 'Astrology', 'Art'],
      mood: 'mystical',
      distance: '2.3 km away',
      isOnline: true
    },
    {
      id: 2,
      type: 'person',
      name: 'River Phoenix',
      username: '@river_wild',
      avatar: '🌊',
      bio: 'Adventure photographer capturing souls',
      compatibility: 87,
      commonInterests: ['Photography', 'Travel', 'Nature'],
      mood: 'adventurous',
      distance: '5.7 km away',
      isOnline: false
    },
    {
      id: 3,
      type: 'event',
      title: 'Midnight Meditation Circle',
      description: 'Join us for a peaceful group meditation under the stars',
      location: 'Central Park',
      time: 'Tonight, 11:30 PM',
      attendees: 12,
      maxAttendees: 20,
      host: { name: 'Sage Wisdom', avatar: '🧙‍♀️' }
    },
    {
      id: 4,
      type: 'person',
      name: 'Nova Bright',
      username: '@nova_shine',
      avatar: '⭐',
      bio: 'Spreading positivity one smile at a time',
      compatibility: 91,
      commonInterests: ['Yoga', 'Music', 'Dancing'],
      mood: 'radiant',
      distance: '1.2 km away',
      isOnline: true
    },
    {
      id: 5,
      type: 'group',
      name: 'Cosmic Coffee Lovers',
      description: 'A gathering of souls who appreciate deep conversations over cosmic coffee',
      members: 47,
      category: 'Social',
      meetupFrequency: 'Weekly Sundays',
      vibe: 'intellectual'
    }
  ];

  const handleConnect = (itemId) => {
    console.log(`Connecting with item ${itemId}`);
  };

  const handleJoin = (itemId) => {
    console.log(`Joining item ${itemId}`);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-600 via-pink-500 to-orange-400">
      {/* Header */}
      <div className="sticky top-0 z-50 bg-white/10 backdrop-blur-lg border-b border-white/20">
        <div className="flex items-center justify-between px-4 py-3">
          <button
            onClick={() => navigate('/feed')}
            className="p-2 rounded-full bg-white/20 hover:bg-white/30 transition-all duration-200"
          >
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          
          <div className="flex items-center space-x-2">
            <div className="animate-pulse">🔮</div>
            <h1 className="text-xl font-bold text-white">Discover</h1>
          </div>
          
          <button className="p-2 rounded-full bg-white/20 hover:bg-white/30 transition-all duration-200">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </button>
        </div>

        {/* Filter Tabs */}
        <div className="px-4 pb-3">
          <div className="flex space-x-2 overflow-x-auto">
            {filters.map(filter => (
              <button
                key={filter.id}
                onClick={() => setActiveFilter(filter.id)}
                className={`flex items-center space-x-2 px-4 py-2 rounded-full whitespace-nowrap transition-all duration-200 ${
                  activeFilter === filter.id
                    ? 'bg-white text-purple-600 font-semibold'
                    : 'bg-white/20 text-white hover:bg-white/30'
                }`}
              >
                <span className="text-sm">{filter.icon}</span>
                <span className="text-sm">{filter.label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-md mx-auto px-4 py-6 space-y-4">
        {discoverItems.map(item => (
          <div key={item.id} className="bg-white/95 backdrop-blur-lg rounded-3xl p-6 shadow-xl">
            {item.type === 'person' && (
              <>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    <div className="relative">
                      <div className="w-16 h-16 bg-gradient-to-r from-purple-400 to-pink-500 rounded-full flex items-center justify-center">
                        <span className="text-2xl">{item.avatar}</span>
                      </div>
                      {item.isOnline && (
                        <div className="absolute -bottom-1 -right-1 w-5 h-5 bg-green-400 rounded-full border-2 border-white flex items-center justify-center">
                          <div className="w-2 h-2 bg-white rounded-full"></div>
                        </div>
                      )}
                    </div>
                    <div>
                      <h3 className="font-bold text-gray-800 text-lg">{item.name}</h3>
                      <p className="text-sm text-gray-500">{item.username}</p>
                      <p className="text-xs text-gray-400">{item.distance}</p>
                    </div>
                  </div>
                  
                  <div className="text-center">
                    <div className="w-12 h-12 bg-gradient-to-r from-green-400 to-emerald-500 rounded-full flex items-center justify-center mb-1">
                      <span className="text-white font-bold text-sm">{item.compatibility}%</span>
                    </div>
                    <p className="text-xs text-gray-500">Match</p>
                  </div>
                </div>

                <p className="text-gray-600 text-sm mb-4 leading-relaxed">{item.bio}</p>

                {/* Mood */}
                <div className="flex items-center space-x-2 mb-4">
                  <div className="px-3 py-1 bg-purple-100 text-purple-700 text-xs font-medium rounded-full">
                    {item.mood} mood
                  </div>
                </div>

                {/* Common Interests */}
                <div className="mb-4">
                  <p className="text-xs text-gray-500 mb-2">Common interests:</p>
                  <div className="flex flex-wrap gap-1">
                    {item.commonInterests.map((interest, index) => (
                      <span
                        key={index}
                        className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-full"
                      >
                        {interest}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="flex space-x-3">
                  <button
                    onClick={() => handleConnect(item.id)}
                    className="flex-1 bg-gradient-to-r from-purple-500 to-pink-500 text-white py-3 rounded-2xl font-semibold hover:shadow-lg transform hover:scale-105 transition-all duration-200"
                  >
                    💕 Connect
                  </button>
                  <button className="px-4 py-3 bg-gray-100 hover:bg-gray-200 text-gray-600 rounded-2xl transition-all duration-200">
                    💬
                  </button>
                </div>
              </>
            )}

            {item.type === 'event' && (
              <>
                <div className="flex items-start space-x-3 mb-4">
                  <div className="w-12 h-12 bg-gradient-to-r from-indigo-400 to-purple-500 rounded-full flex items-center justify-center">
                    <span className="text-xl">🧘</span>
                  </div>
                  <div className="flex-1">
                    <h3 className="font-bold text-gray-800 text-lg mb-1">{item.title}</h3>
                    <p className="text-sm text-gray-600 leading-relaxed">{item.description}</p>
                  </div>
                </div>

                <div className="space-y-2 mb-4">
                  <div className="flex items-center space-x-2 text-sm text-gray-600">
                    <span>📍</span>
                    <span>{item.location}</span>
                  </div>
                  <div className="flex items-center space-x-2 text-sm text-gray-600">
                    <span>🕐</span>
                    <span>{item.time}</span>
                  </div>
                  <div className="flex items-center space-x-2 text-sm text-gray-600">
                    <span>👥</span>
                    <span>{item.attendees}/{item.maxAttendees} attending</span>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <div className="w-8 h-8 bg-gradient-to-r from-yellow-400 to-orange-500 rounded-full flex items-center justify-center">
                      <span className="text-sm">{item.host.avatar}</span>
                    </div>
                    <span className="text-sm text-gray-600">Hosted by {item.host.name}</span>
                  </div>
                  
                  <button
                    onClick={() => handleJoin(item.id)}
                    className="bg-gradient-to-r from-indigo-500 to-purple-500 text-white px-6 py-2 rounded-full font-semibold hover:shadow-lg transform hover:scale-105 transition-all duration-200"
                  >
                    ✨ Join
                  </button>
                </div>
              </>
            )}

            {item.type === 'group' && (
              <>
                <div className="flex items-start space-x-3 mb-4">
                  <div className="w-12 h-12 bg-gradient-to-r from-orange-400 to-red-500 rounded-full flex items-center justify-center">
                    <span className="text-xl">☕</span>
                  </div>
                  <div className="flex-1">
                    <h3 className="font-bold text-gray-800 text-lg mb-1">{item.name}</h3>
                    <p className="text-sm text-gray-600 leading-relaxed">{item.description}</p>
                  </div>
                </div>

                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-4 text-sm text-gray-600">
                    <div className="flex items-center space-x-1">
                      <span>👥</span>
                      <span>{item.members} members</span>
                    </div>
                    <div className="flex items-center space-x-1">
                      <span>📅</span>
                      <span>{item.meetupFrequency}</span>
                    </div>
                  </div>
                  
                  <div className="px-3 py-1 bg-orange-100 text-orange-700 text-xs font-medium rounded-full">
                    {item.vibe}
                  </div>
                </div>

                <button
                  onClick={() => handleJoin(item.id)}
                  className="w-full bg-gradient-to-r from-orange-500 to-red-500 text-white py-3 rounded-2xl font-semibold hover:shadow-lg transform hover:scale-105 transition-all duration-200"
                >
                  🎯 Join Group
                </button>
              </>
            )}
          </div>
        ))}

        {/* Load More */}
        <div className="text-center py-6">
          <button className="bg-white/20 backdrop-blur-lg text-white px-6 py-3 rounded-full font-semibold hover:bg-white/30 transition-all duration-200">
            Discover More ✨
          </button>
        </div>
      </div>
    </div>
  );
};

export default Discover;