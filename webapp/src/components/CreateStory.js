import React, { useState, useEffect } from 'react';

const CreateStory = ({ user, onClose, onStoryCreated }) => {
  const [storyType, setStoryType] = useState('image'); // 'image' or 'text'
  const [storyText, setStoryText] = useState('');
  const [selectedImage, setSelectedImage] = useState(null);
  const [backgroundColor, setBackgroundColor] = useState('from-pink-400 to-purple-600');
  const [mood, setMood] = useState(''); // Empty by default (optional)
  const [selectedMusic, setSelectedMusic] = useState(null);
  const [selectedLocation, setSelectedLocation] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showMusicModal, setShowMusicModal] = useState(false);
  const [musicSearch, setMusicSearch] = useState('');
  const [selectedGenre, setSelectedGenre] = useState('All');
  const [showPoll, setShowPoll] = useState(false);
  const [pollQuestion, setPollQuestion] = useState('');
  const [pollOptions, setPollOptions] = useState(['', '']);

  const backgrounds = [
    'from-pink-400 to-purple-600',
    'from-blue-400 to-indigo-600',
    'from-green-400 to-teal-600',
    'from-orange-400 to-red-600',
    'from-purple-400 to-pink-600',
    'from-indigo-400 to-blue-600',
    'from-yellow-400 to-orange-500',
    'from-teal-400 to-green-600'
  ];

  const moods = [
    { value: '', emoji: '😐', color: 'from-gray-400 to-gray-500', label: 'No Mood' },
    { value: 'happy', emoji: '😊', color: 'from-yellow-400 to-orange-500', label: 'Happy' },
    { value: 'excited', emoji: '🤩', color: 'from-pink-400 to-red-500', label: 'Excited' },
    { value: 'peaceful', emoji: '😌', color: 'from-green-400 to-blue-500', label: 'Peaceful' },
    { value: 'creative', emoji: '🎨', color: 'from-purple-400 to-indigo-500', label: 'Creative' },
    { value: 'adventurous', emoji: '🗺️', color: 'from-orange-400 to-red-500', label: 'Adventurous' },
    { value: 'contemplative', emoji: '🤔', color: 'from-indigo-400 to-purple-500', label: 'Contemplative' }
  ];

  const musicOptions = [
    // Popular Hits
    { id: '1', name: 'Anti-Hero', artist: 'Taylor Swift', duration: '3:20', genre: 'Pop' },
    { id: '2', name: 'Flowers', artist: 'Miley Cyrus', duration: '3:20', genre: 'Pop' },
    { id: '3', name: 'As It Was', artist: 'Harry Styles', duration: '2:47', genre: 'Pop Rock' },
    { id: '4', name: 'Bad Habit', artist: 'Steve Lacy', duration: '3:51', genre: 'Alternative' },
    { id: '5', name: 'Unholy', artist: 'Sam Smith ft. Kim Petras', duration: '2:36', genre: 'Pop' },
    
    // Hip Hop & Rap
    { id: '6', name: 'God Is Good', artist: 'Drake', duration: '3:18', genre: 'Hip Hop' },
    { id: '7', name: 'Creepin\'', artist: 'Metro Boomin, The Weeknd, 21 Savage', duration: '3:41', genre: 'Hip Hop' },
    { id: '8', name: 'Jimmy Cooks', artist: 'Drake ft. 21 Savage', duration: '3:45', genre: 'Hip Hop' },
    
    // Electronic/Dance
    { id: '9', name: 'I\'m Good (Blue)', artist: 'David Guetta & Bebe Rexha', duration: '2:55', genre: 'Electronic' },
    { id: '10', name: 'Pepas', artist: 'Farruko', duration: '4:11', genre: 'Reggaeton' },
    { id: '11', name: 'Stay', artist: 'The Kid LAROI & Justin Bieber', duration: '2:21', genre: 'Pop' },
    
    // Alternative/Indie
    { id: '12', name: 'Heat Waves', artist: 'Glass Animals', duration: '3:58', genre: 'Alternative' },
    { id: '13', name: 'Good 4 U', artist: 'Olivia Rodrigo', duration: '2:58', genre: 'Pop Punk' },
    { id: '14', name: 'Levitating', artist: 'Dua Lipa', duration: '3:23', genre: 'Pop' },
    
    // Chill/Lo-Fi
    { id: '15', name: 'Chill Vibes', artist: 'Lo-Fi Collective', duration: '3:45', genre: 'Lo-Fi' },
    { id: '16', name: 'Summer Dreams', artist: 'Indie Wave', duration: '4:12', genre: 'Chill' },
    { id: '17', name: 'Midnight Jazz', artist: 'Cool Cats', duration: '5:30', genre: 'Jazz' },
    { id: '18', name: 'Ocean Sounds', artist: 'Nature Mix', duration: '2:18', genre: 'Ambient' },
    { id: '19', name: 'City Lights', artist: 'Synth Pop', duration: '3:55', genre: 'Synthwave' },
    { id: '20', name: 'Peaceful Mind', artist: 'Meditation Music', duration: '6:00', genre: 'Ambient' },
    
    // Rock/Metal
    { id: '21', name: 'Enemy', artist: 'Imagine Dragons x JID', duration: '2:53', genre: 'Alternative Rock' },
    { id: '22', name: 'Industry Baby', artist: 'Lil Nas X ft. Jack Harlow', duration: '3:32', genre: 'Hip Hop' },
    { id: '23', name: 'Shivers', artist: 'Ed Sheeran', duration: '3:27', genre: 'Pop' },
    
    // R&B/Soul
    { id: '24', name: 'About Damn Time', artist: 'Lizzo', duration: '3:12', genre: 'Pop/R&B' },
    { id: '25', name: 'Break My Soul', artist: 'Beyoncé', duration: '4:38', genre: 'Dance/Electronic' },
    
    // Country
    { id: '26', name: 'The Good Ones', artist: 'Gabby Barrett', duration: '2:45', genre: 'Country' },
    { id: '27', name: 'Heartbreak Highway', artist: 'Country Stars', duration: '3:22', genre: 'Country' },
    
    // International
    { id: '28', name: 'Tití Me Preguntó', artist: 'Bad Bunny', duration: '4:02', genre: 'Reggaeton' },
    { id: '29', name: 'Moscow Mule', artist: 'Bad Bunny', duration: '4:17', genre: 'Reggaeton' },
    { id: '30', name: 'Quevedo: Bzrp Music Sessions', artist: 'Bizarrap & Quevedo', duration: '3:29', genre: 'Latin Pop' }
  ];

  const handleImageUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        setSelectedImage(e.target.result);
        setStoryType('image');
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSubmit = async () => {
    if ((storyType === 'text' && !storyText.trim()) || (storyType === 'image' && !selectedImage)) {
      return;
    }

    setIsSubmitting(true);
    console.log('🔄 Story submission started');
    
    // Create default user if none exists
    const defaultUser = user || { name: 'Test User', username: 'testuser', profilePic: '✨' };
    
    // Create story object with all features
    const newStory = {
      id: Date.now(),
      user: {
        name: defaultUser.name,
        username: defaultUser.username,
        avatar: defaultUser.profilePic || '🌟',
        isOwn: true
      },
      content: storyType === 'image' ? {
        type: 'image',
        url: selectedImage,
        text: storyText
      } : {
        type: 'text',
        backgroundColor: backgroundColor,
        text: storyText
      },
      timestamp: 'Just now',
      views: 0,
      mood: mood || null,
      music: selectedMusic,
      location: selectedLocation || null,
      poll: showPoll ? {
        question: pollQuestion,
        options: pollOptions.filter(opt => opt.trim()),
        votes: {}
      } : null,
      expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000) // 24 hours from now
    };

    // Save to localStorage for persistence with error handling
    try {
      const userStoriesKey = `luvhive_stories_${defaultUser.username}`;
      console.log('📚 Saving story to key:', userStoriesKey);
      let existingStories = JSON.parse(localStorage.getItem(userStoriesKey) || '[]');
      console.log('📚 Existing stories before:', existingStories.length);
      
      // Limit to 20 stories per user to prevent quota issues
      if (existingStories.length >= 20) {
        existingStories = existingStories.slice(0, 19);
      }
      
      existingStories.unshift(newStory);
      localStorage.setItem(userStoriesKey, JSON.stringify(existingStories));
      console.log('📚 Stories after save:', existingStories.length);
      console.log('📚 Saved story data:', newStory);
    } catch (error) {
      console.log('Story storage error:', error);
      // If localStorage is full, clear old data
      if (error.name === 'QuotaExceededError') {
        try {
          // Clear old data to make space
          for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && key.includes('luvhive_stories_')) {
              const data = JSON.parse(localStorage.getItem(key) || '[]');
              if (data.length > 5) {
                localStorage.setItem(key, JSON.stringify(data.slice(0, 5)));
              }
            }
          }
          // Try saving again
          const userStoriesKey = `luvhive_stories_${defaultUser.username}`;
          const existingStories = JSON.parse(localStorage.getItem(userStoriesKey) || '[]');
          existingStories.unshift(newStory);
          localStorage.setItem(userStoriesKey, JSON.stringify(existingStories));
        } catch (retryError) {
          console.log('Failed to save story even after cleanup');
        }
      }
    }

    // Simulate story creation
    setTimeout(() => {
      console.log('✅ Story created successfully:', newStory);
      onStoryCreated && onStoryCreated(newStory);
      onClose && onClose();
      
      // Show success feedback
      if (window.Telegram?.WebApp?.showAlert) {
        window.Telegram.WebApp.showAlert('✨ Story shared successfully!');
      } else {
        alert('✨ Story shared successfully!');
      }
    }, 1500);
  };

  const handleMusicSelect = (music) => {
    setSelectedMusic(music);
  };

  const genres = ['All', 'Pop', 'Hip Hop', 'Electronic', 'Alternative', 'Rock', 'R&B', 'Country', 'Latin', 'Lo-Fi', 'Jazz', 'Ambient'];

  const filteredMusic = musicOptions.filter(music => {
    const matchesSearch = music.name.toLowerCase().includes(musicSearch.toLowerCase()) ||
                         music.artist.toLowerCase().includes(musicSearch.toLowerCase());
    const matchesGenre = selectedGenre === 'All' || music.genre === selectedGenre;
    return matchesSearch && matchesGenre;
  });

  const handleLocationSelect = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setSelectedLocation(`${position.coords.latitude.toFixed(4)}, ${position.coords.longitude.toFixed(4)}`);
        },
        () => {
          // Fallback to manual input
          const location = prompt('Enter your location:');
          if (location) setSelectedLocation(location);
        }
      );
    } else {
      const location = prompt('Enter your location:');
      if (location) setSelectedLocation(location);
    }
  };

  useEffect(() => {
    // Reset form when modal opens
    setStoryType('text');
    setStoryText('');
    setSelectedImage(null);
    setMood('');
    setSelectedMusic(null);
    setSelectedLocation('');
    setBackgroundColor('from-pink-400 to-purple-600');
    setPollOptions(['', '']);
    setIsSubmitting(false);

    // Force attach event handler directly to DOM
    const attachShareHandler = () => {
      const shareBtn = document.getElementById('story-share-btn');
      if (shareBtn) {
        console.log('🔧 Direct DOM handler attached to Share button');
        shareBtn.addEventListener('click', (e) => {
          console.log('🔥 DIRECT DOM CLICK HANDLER TRIGGERED!');
          e.preventDefault();
          e.stopPropagation();
          
          // Get current text from textarea
          const currentText = document.querySelector('textarea').value;
          console.log('📝 Current story text:', currentText);
          
          if (!currentText.trim()) {
            console.log('❌ Story validation failed - no text content');
            return;
          }
          console.log('🚀 Calling story handleSubmit directly');
          handleSubmit();
        });
      }
    };
    
    // Attach handler with delay to ensure DOM is ready
    setTimeout(attachShareHandler, 1000);
  }, []);
  return (
    <div 
      className="fixed inset-0 bg-black/90 flex items-end sm:items-center justify-center z-50"
      style={{ pointerEvents: 'auto' }}
    >
      <div 
        className="w-full max-w-md mx-4 bg-white rounded-t-3xl sm:rounded-3xl overflow-hidden" 
        style={{height: '90vh', maxHeight: '90vh'}}
      >
        {/* Fixed Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-100 bg-white">
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            title="Cancel"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          <h2 className="text-lg font-semibold">Create Story</h2>
          <button
            id="story-share-btn"
            onClick={handleSubmit}
            disabled={((storyType === 'text' && !storyText.trim()) || (storyType === 'image' && !selectedImage)) || isSubmitting}
            className={`px-4 py-2 rounded-full font-semibold transition-all ${
              ((storyType === 'text' && !storyText.trim()) || (storyType === 'image' && !selectedImage)) || isSubmitting
                ? 'bg-gray-200 text-gray-400'
                : 'bg-gradient-to-r from-pink-500 to-purple-600 text-white hover:shadow-lg'
            }`}
            style={{ 
              pointerEvents: 'auto', 
              zIndex: 9999, 
              position: 'relative',
              border: 'none',
              outline: 'none'
            }}
          >
            {isSubmitting ? '✨ Sharing...' : 'Share'}
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto">
          <div className="p-4 space-y-4">
          {/* Story Type Selector */}
          <div className="flex space-x-2">
            <button
              onClick={() => setStoryType('image')}
              className={`flex-1 p-3 rounded-2xl font-semibold transition-all ${
                storyType === 'image'
                  ? 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              📸 Photo Story
            </button>
            <button
              onClick={() => setStoryType('text')}
              className={`flex-1 p-3 rounded-2xl font-semibold transition-all ${
                storyType === 'text'
                  ? 'bg-gradient-to-r from-purple-500 to-pink-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              ✍️ Text Story
            </button>
          </div>

          {/* Story Preview */}
          <div className="relative h-96 rounded-3xl overflow-hidden">
            {storyType === 'image' ? (
              <div className="h-full relative">
                {selectedImage ? (
                  <>
                    <img src={selectedImage} alt="Story preview" className="w-full h-full object-cover" />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/30" />
                    {storyText && (
                      <div className="absolute bottom-8 left-4 right-4">
                        <p className="text-white text-lg font-medium text-center leading-relaxed">
                          {storyText}
                        </p>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="h-full bg-gray-100 flex items-center justify-center">
                    <label className="cursor-pointer text-center">
                      <div className="w-16 h-16 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-full flex items-center justify-center mx-auto mb-4">
                        <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                      </div>
                      <p className="text-gray-600 font-medium">Tap to add photo</p>
                      <input
                        type="file"
                        accept="image/*"
                        onChange={handleImageUpload}
                        className="hidden"
                      />
                    </label>
                  </div>
                )}
              </div>
            ) : (
              <div className={`h-full bg-gradient-to-br ${backgroundColor} flex items-center justify-center p-8`}>
                <textarea
                  value={storyText}
                  onChange={(e) => {
                    setStoryText(e.target.value);
                    console.log('📝 Story text updated:', e.target.value);
                  }}
                  placeholder="Share what's on your mind..."
                  className="w-full bg-transparent text-white text-2xl font-bold text-center placeholder-white/70 outline-none resize-none"
                  rows="4"
                />
              </div>
            )}

            {/* User Avatar Overlay */}
            <div className="absolute top-4 left-4 flex items-center space-x-2">
              <div className="w-10 h-10 rounded-full overflow-hidden bg-gradient-to-r from-pink-500 to-purple-600">
                <img src={user.profilePic} alt={user.name} className="w-full h-full object-cover" />
              </div>
              <div>
                <p className="text-white text-sm font-semibold drop-shadow-lg">{user.name}</p>
                <p className="text-white/80 text-xs">@{user.username}</p>
              </div>
            </div>
          </div>

          {/* Caption Input for Image Stories */}
          {storyType === 'image' && selectedImage && (
            <div className="mb-4">
              <label className="text-sm font-medium text-gray-700 mb-2 block">Add Caption</label>
              <textarea
                value={storyText}
                onChange={(e) => {
                  setStoryText(e.target.value);
                  console.log('📝 Story text updated:', e.target.value);
                }}
                placeholder="Write a caption for your story..."
                className="w-full p-3 border border-gray-200 rounded-2xl resize-none focus:outline-none focus:ring-2 focus:ring-purple-500"
                rows={3}
                maxLength={280}
              />
              <div className="flex justify-between items-center mt-1">
                <span className="text-xs text-gray-500">{storyText.length}/280 characters</span>
              </div>
            </div>
          )}

          {/* Selected Music Display */}
          {selectedMusic && (
            <div className="mb-4 p-3 bg-purple-50 border border-purple-200 rounded-2xl">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-gradient-to-r from-purple-400 to-pink-500 rounded-full flex items-center justify-center">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                  </svg>
                </div>
                <div className="flex-1">
                  <p className="font-semibold text-gray-800">{selectedMusic.name}</p>
                  <p className="text-sm text-gray-500">{selectedMusic.artist}</p>
                </div>
                <button
                  onClick={() => setSelectedMusic(null)}
                  className="p-1 hover:bg-purple-100 rounded-full"
                >
                  <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
          )}

          {/* Selected Location Display */}
          {selectedLocation && (
            <div className="mb-4 p-3 bg-orange-50 border border-orange-200 rounded-2xl">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-gradient-to-r from-orange-400 to-red-500 rounded-full flex items-center justify-center">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                </div>
                <div className="flex-1">
                  <p className="font-semibold text-gray-800">📍 Location Added</p>
                  <p className="text-sm text-gray-500">{selectedLocation}</p>
                </div>
                <button
                  onClick={() => setSelectedLocation('')}
                  className="p-1 hover:bg-orange-100 rounded-full"
                >
                  <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
          )}

          {/* Poll Creation Interface */}
          {showPoll && (
            <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-2xl">
              <div className="flex items-center space-x-3 mb-3">
                <div className="w-10 h-10 bg-gradient-to-r from-green-400 to-blue-500 rounded-full flex items-center justify-center">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
                <div className="flex-1">
                  <p className="font-semibold text-gray-800">📊 Create Poll</p>
                </div>
                <button
                  onClick={() => setShowPoll(false)}
                  className="p-1 hover:bg-green-100 rounded-full"
                >
                  <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              {/* Poll Question */}
              <div className="mb-3">
                <input
                  type="text"
                  placeholder="Ask a question..."
                  value={pollQuestion}
                  onChange={(e) => setPollQuestion(e.target.value)}
                  className="w-full p-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-green-500"
                  maxLength={100}
                />
              </div>
              
              {/* Poll Options */}
              <div className="space-y-2">
                {pollOptions.map((option, index) => (
                  <div key={index} className="flex items-center space-x-2">
                    <input
                      type="text"
                      placeholder={`Option ${index + 1}`}
                      value={option}
                      onChange={(e) => {
                        const newOptions = [...pollOptions];
                        newOptions[index] = e.target.value;
                        setPollOptions(newOptions);
                      }}
                      className="flex-1 p-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
                      maxLength={50}
                    />
                    {pollOptions.length > 2 && (
                      <button
                        onClick={() => {
                          const newOptions = pollOptions.filter((_, i) => i !== index);
                          setPollOptions(newOptions);
                        }}
                        className="p-2 text-red-500 hover:bg-red-50 rounded-lg"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    )}
                  </div>
                ))}
                
                {pollOptions.length < 4 && (
                  <button
                    onClick={() => setPollOptions([...pollOptions, ''])}
                    className="flex items-center space-x-2 p-2 text-green-600 hover:bg-green-50 rounded-lg text-sm font-medium"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                    <span>Add Option</span>
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Background Colors for Text Stories */}
          {storyType === 'text' && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">Background</p>
              <div className="grid grid-cols-4 gap-2">
                {backgrounds.map((bg, index) => (
                  <button
                    key={index}
                    onClick={() => setBackgroundColor(bg)}
                    className={`w-12 h-12 rounded-2xl bg-gradient-to-r ${bg} border-2 transition-all ${
                      backgroundColor === bg ? 'border-gray-800 scale-110' : 'border-transparent hover:scale-105'
                    }`}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Mood Selector - Optional */}
          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Story Mood <span className="text-gray-400">(Optional)</span></p>
            <div className="flex space-x-2 overflow-x-auto pb-2">
              {moods.map((moodOption) => (
                <button
                  key={moodOption.value}
                  onClick={() => setMood(moodOption.value)}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-full whitespace-nowrap transition-all ${
                    mood === moodOption.value
                      ? `bg-gradient-to-r ${moodOption.color} text-white shadow-lg scale-105`
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  <span>{moodOption.emoji}</span>
                  <span className="text-sm font-medium">{moodOption.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Additional Options */}
          <div className="flex items-center space-x-4 pt-4 border-t border-gray-100">
            <label className="flex items-center space-x-2 cursor-pointer hover:bg-gray-100 p-2 rounded-2xl transition-colors">
              <div className="w-8 h-8 bg-gradient-to-r from-green-400 to-blue-500 rounded-full flex items-center justify-center">
                <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 002 2z" />
                </svg>
              </div>
              <span className="text-sm font-medium">Photo</span>
              <input
                type="file"
                accept="image/*"
                onChange={handleImageUpload}
                className="hidden"
              />
            </label>

            <button 
              onClick={() => setShowMusicModal(true)}
              className={`flex items-center space-x-2 hover:bg-gray-100 p-2 rounded-2xl transition-colors ${selectedMusic ? 'bg-purple-50' : ''}`}
            >
              <div className="w-8 h-8 bg-gradient-to-r from-purple-400 to-pink-500 rounded-full flex items-center justify-center">
                <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                </svg>
              </div>
              <span className="text-sm font-medium">
                {selectedMusic ? selectedMusic.name : 'Music'}
              </span>
            </button>

            <button 
              onClick={handleLocationSelect}
              className={`flex items-center space-x-2 hover:bg-gray-100 p-2 rounded-2xl transition-colors ${selectedLocation ? 'bg-orange-50' : ''}`}
            >
              <div className="w-8 h-8 bg-gradient-to-r from-orange-400 to-red-500 rounded-full flex items-center justify-center">
                <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <span className="text-sm font-medium">
                {selectedLocation ? '📍 Added' : 'Location'}
              </span>
            </button>

            <button 
              onClick={() => setShowPoll(!showPoll)}
              className={`flex items-center space-x-2 hover:bg-gray-100 p-2 rounded-2xl transition-colors ${showPoll ? 'bg-green-50' : ''}`}
            >
              <div className="w-8 h-8 bg-gradient-to-r from-green-400 to-blue-500 rounded-full flex items-center justify-center">
                <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <span className="text-sm font-medium">
                {showPoll ? '📊 Poll Added' : 'Add Poll'}
              </span>
            </button>
          </div>
        </div>
        </div>

        {/* Enhanced Music Selection Modal */}
        {showMusicModal && (
          <div className="absolute inset-0 bg-black/50 flex items-end justify-center z-10">
            <div className="bg-white rounded-t-3xl w-full p-4 overflow-hidden" style={{height: '70vh'}}>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">Choose Music 🎵</h3>
                <button 
                  onClick={() => {
                    setShowMusicModal(false);
                    setMusicSearch('');
                    setSelectedGenre('All');
                  }}
                  className="p-2 hover:bg-gray-100 rounded-full"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              {/* Search Bar */}
              <div className="mb-4">
                <input
                  type="text"
                  placeholder="Search songs, artists..."
                  value={musicSearch}
                  onChange={(e) => setMusicSearch(e.target.value)}
                  className="w-full p-3 border border-gray-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>
              
              {/* Genre Filter */}
              <div className="mb-4">
                <div className="flex space-x-2 overflow-x-auto pb-2">
                  {genres.map((genre) => (
                    <button
                      key={genre}
                      onClick={() => setSelectedGenre(genre)}
                      className={`px-3 py-2 rounded-full whitespace-nowrap text-sm font-medium transition-all ${
                        selectedGenre === genre
                          ? 'bg-purple-500 text-white'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      {genre}
                    </button>
                  ))}
                </div>
              </div>
              
              {/* Music List */}
              <div className="overflow-y-auto" style={{height: 'calc(70vh - 200px)'}}>
                <div className="space-y-2">
                  {filteredMusic.length > 0 ? filteredMusic.map((music) => (
                    <button
                      key={music.id}
                      onClick={() => {
                        handleMusicSelect(music);
                        setShowMusicModal(false);
                        setMusicSearch('');
                        setSelectedGenre('All');
                      }}
                      className={`w-full flex items-center space-x-3 p-3 rounded-2xl transition-all ${
                        selectedMusic?.id === music.id 
                          ? 'bg-purple-100 border-2 border-purple-500' 
                          : 'bg-gray-50 hover:bg-gray-100'
                      }`}
                    >
                      <div className="w-12 h-12 bg-gradient-to-r from-purple-400 to-pink-500 rounded-full flex items-center justify-center">
                        <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                        </svg>
                      </div>
                      <div className="flex-1 text-left">
                        <p className="font-medium text-gray-800">{music.name}</p>
                        <p className="text-sm text-gray-500">{music.artist} • {music.duration}</p>
                        <p className="text-xs text-purple-600">{music.genre}</p>
                      </div>
                      {selectedMusic?.id === music.id && (
                        <div className="text-purple-500 text-xl">✓</div>
                      )}
                    </button>
                  )) : (
                    <div className="text-center py-8">
                      <div className="text-4xl mb-2">🔍</div>
                      <p className="text-gray-500">No music found</p>
                      <p className="text-sm text-gray-400">Try a different search or genre</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CreateStory;