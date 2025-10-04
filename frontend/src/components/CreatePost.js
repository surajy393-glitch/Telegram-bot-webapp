import React, { useState, useEffect } from 'react';

const CreatePost = ({ user, onClose, onPostCreated }) => {
  const [postText, setPostText] = useState('');
  const [selectedImages, setSelectedImages] = useState([]);
  const [selectedVideos, setSelectedVideos] = useState([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [mood, setMood] = useState('happy');
  const [selectedMusic, setSelectedMusic] = useState(null);
  const [selectedLocation, setSelectedLocation] = useState('');
  const [showMusicModal, setShowMusicModal] = useState(false);
  const [musicSearch, setMusicSearch] = useState('');
  const [selectedGenre, setSelectedGenre] = useState('All');

  const moods = [
    { value: 'happy', label: 'Happy', emoji: '😊', color: 'from-yellow-400 to-orange-500' },
    { value: 'excited', label: 'Excited', emoji: '🤩', color: 'from-pink-400 to-red-500' },
    { value: 'peaceful', label: 'Peaceful', emoji: '😌', color: 'from-green-400 to-blue-500' },
    { value: 'creative', label: 'Creative', emoji: '🎨', color: 'from-purple-400 to-indigo-500' },
    { value: 'adventurous', label: 'Adventurous', emoji: '🗺️', color: 'from-orange-400 to-red-500' },
    { value: 'contemplative', label: 'Thoughtful', emoji: '🤔', color: 'from-indigo-400 to-purple-500' }
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

  const genres = ['All', 'Pop', 'Hip Hop', 'Electronic', 'Alternative', 'Rock', 'R&B', 'Country', 'Latin', 'Lo-Fi', 'Jazz', 'Ambient'];

  const filteredMusic = musicOptions.filter(music => {
    const matchesSearch = music.name.toLowerCase().includes(musicSearch.toLowerCase()) ||
                         music.artist.toLowerCase().includes(musicSearch.toLowerCase());
    const matchesGenre = selectedGenre === 'All' || music.genre === selectedGenre;
    return matchesSearch && matchesGenre;
  });

  const handleMediaUpload = async (event) => {
    const files = Array.from(event.target.files);
    
    for (const file of files) {
      const isImage = file.type.startsWith('image/');
      const isVideo = file.type.startsWith('video/');
      
      // Check file type
      if (!isImage && !isVideo) {
        alert('केवल इमेज और वीडियो फाइलें समर्थित हैं।');
        continue;
      }
      
      // Check file size limits
      const maxImageSize = 20 * 1024 * 1024; // 20MB for images
      const maxVideoSize = 50 * 1024 * 1024; // 50MB for videos
      
      if (isImage && file.size > maxImageSize) {
        alert(`इमेज बहुत बड़ी है (${(file.size / (1024 * 1024)).toFixed(1)}MB)। कृपया 20MB से कम साइज की इमेज चुनें।`);
        continue;
      }
      
      if (isVideo && file.size > maxVideoSize) {
        alert(`वीडियो बहुत बड़ा है (${(file.size / (1024 * 1024)).toFixed(1)}MB)। कृपया 50MB से कम साइज का वीडियो चुनें।`);
        continue;
      }
      
      // Check total media limit (combined images + videos)
      const totalMedia = selectedImages.length + selectedVideos.length;
      if (totalMedia >= 4) {
        alert('अधिकतम 4 मीडिया फाइलें (इमेज + वीडियो) अपलोड की जा सकती हैं।');
        break;
      }
      
      // Read file for preview
      const reader = new FileReader();
      reader.onload = (e) => {
        const mediaItem = {
          id: Date.now() + Math.random(),
          url: e.target.result,
          file: file,
          type: isVideo ? 'video' : 'image'
        };
        
        if (isVideo) {
          setSelectedVideos(prev => [...prev, mediaItem]);
        } else {
          setSelectedImages(prev => [...prev, mediaItem]);
        }
      };
      reader.readAsDataURL(file);
    }
  };

  const removeMedia = (id, type) => {
    if (type === 'video') {
      setSelectedVideos(prev => prev.filter(video => video.id !== id));
    } else {
      setSelectedImages(prev => prev.filter(img => img.id !== id));
    }
  };

  const uploadImageToBackend = async (imageObj) => {
    try {
      const formData = new FormData();
      formData.append('file', imageObj.file);
      
      const backendUrl = process.env.REACT_APP_BACKEND_URL || '';
      const response = await fetch(`${backendUrl}/api/upload-media`, {
        method: 'POST',
        body: formData,
        headers: {
          // Include Telegram WebApp initData for authentication if available
          ...(window.Telegram?.WebApp?.initData ? {
            'X-Telegram-Init-Data': window.Telegram.WebApp.initData
          } : {})
        }
      });
      
      if (!response.ok) {
        throw new Error('Upload failed');
      }
      
      const result = await response.json();
      
      // Ensure we always return a valid image URL
      if (!result.success) {
        throw new Error(result.message || 'Upload failed');
      }
      
      // photo_url should always be present from backend
      if (!result.photo_url) {
        console.error('No photo_url in response:', result);
        throw new Error('Invalid server response - no photo URL');
      }
      
      return result.photo_url;
    } catch (error) {
      console.error('Image upload error:', error);
      throw error;
    }
  };

  const handleSubmit = async () => {
    if (!postText.trim() && selectedImages.length === 0) return;

    setIsSubmitting(true);
    console.log('🔄 Post submission started');
    
    // Create default user if none exists
    const defaultUser = user || { name: 'Test User', username: 'testuser', profilePic: '✨' };
    
    // Upload images to backend first if any
    let uploadedImageUrls = [];
    if (selectedImages.length > 0) {
      try {
        console.log('📤 Uploading images to backend...');
        const uploadPromises = selectedImages.map(img => uploadImageToBackend(img));
        uploadedImageUrls = await Promise.all(uploadPromises);
        console.log('✅ Images uploaded:', uploadedImageUrls);
      } catch (error) {
        console.error('❌ Image upload failed:', error);
        setIsSubmitting(false);
        alert('⚠️ Failed to upload images. Please try again.');
        return;
      }
    }
    
    // Simulate post creation with uploaded image URLs
    const newPost = {
      id: Date.now(),
      user: {
        name: defaultUser.name,
        username: defaultUser.username,
        avatar: defaultUser.profilePic,
        mood: mood,
        aura: getAuraByMood(mood)
      },
      content: postText,
      images: uploadedImageUrls, // Use uploaded URLs instead of Base64
      mood: mood,
      music: selectedMusic,
      location: selectedLocation || null,
      vibeScore: Math.floor(Math.random() * 20) + 80, // Random score 80-100
      sparkCount: 0,
      glowCount: 0,
      timestamp: 'Just now',
      isSparkPost: false
    };

    let saveSuccess = false;
    
    // Save post to user's profile with storage management
    try {
      const userPostsKey = `luvhive_posts_${defaultUser.username}`;
      console.log('📝 Saving post to key:', userPostsKey);
      let existingPosts = JSON.parse(localStorage.getItem(userPostsKey) || '[]');
      console.log('📝 Existing posts before:', existingPosts.length);
      
      // Limit to 50 posts per user to prevent quota issues
      if (existingPosts.length >= 50) {
        existingPosts = existingPosts.slice(0, 49);
      }
      
      existingPosts.unshift(newPost); // Add to beginning of array
      localStorage.setItem(userPostsKey, JSON.stringify(existingPosts));
      console.log('📝 Posts after save:', existingPosts.length);
      console.log('📝 Saved post data:', newPost);
      saveSuccess = true;
    } catch (error) {
      console.log('Storage error:', error);
      // If localStorage is full, clear old data
      if (error.name === 'QuotaExceededError') {
        try {
          console.log('⚠️ Storage quota exceeded, clearing old data...');
          // Clear old stories and posts to make space
          for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            if (key && (key.includes('luvhive_posts_') || key.includes('luvhive_stories_'))) {
              const data = JSON.parse(localStorage.getItem(key) || '[]');
              if (data.length > 5) {
                // Keep only 5 most recent items
                localStorage.setItem(key, JSON.stringify(data.slice(0, 5)));
              }
            }
          }
          // Try saving again
          const userPostsKey = `luvhive_posts_${defaultUser.username}`;
          const existingPosts = JSON.parse(localStorage.getItem(userPostsKey) || '[]');
          existingPosts.unshift(newPost);
          localStorage.setItem(userPostsKey, JSON.stringify(existingPosts));
          console.log('✅ Saved post after cleanup');
          saveSuccess = true;
        } catch (retryError) {
          console.log('❌ Failed to save post even after cleanup:', retryError);
          setIsSubmitting(false);
          alert('⚠️ Failed to save post. Image might be too large. Try with smaller image or without image.');
          return; // Exit early - don't call onPostCreated
        }
      } else {
        setIsSubmitting(false);
        alert('⚠️ Failed to save post: ' + error.message);
        return; // Exit early - don't call onPostCreated
      }
    }

    // Only proceed if save was successful
    if (saveSuccess) {
      setTimeout(() => {
        console.log('✅ Post created successfully:', newPost);
        onPostCreated && onPostCreated(newPost);
        onClose && onClose();
        
        // Show success feedback
        if (window.Telegram?.WebApp?.showAlert) {
          window.Telegram.WebApp.showAlert('✨ Post shared successfully!');
        } else {
          alert('✨ Post shared successfully!');
        }
      }, 1500);
    }
  };

  useEffect(() => {
    // Reset form when modal opens
    setPostText('');
    setSelectedImages([]);
    setMood('Happy');
    setSelectedMusic(null);
    setSelectedLocation(null);
    setIsSubmitting(false);
  }, []);

  const handleMusicSelect = (music) => {
    setSelectedMusic(music);
  };

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

  const getAuraByMood = (mood) => {
    const auraMap = {
      happy: 'golden',
      excited: 'rainbow',
      peaceful: 'blue',
      creative: 'purple',
      adventurous: 'orange',
      contemplative: 'cosmic'
    };
    return auraMap[mood] || 'golden';
  };

  return (
    <div 
      className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-end sm:items-center justify-center z-50"
      style={{ pointerEvents: 'auto' }}
    >
      <div 
        className="bg-white rounded-t-3xl sm:rounded-3xl w-full sm:max-w-md mx-4 max-h-[90vh] overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-100">
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          <h2 className="text-lg font-semibold">Create Post</h2>
          <button
            id="post-share-btn"
            onClick={handleSubmit}
            disabled={(!postText.trim() && selectedImages.length === 0) || isSubmitting}
            className={`px-4 py-2 rounded-full font-semibold transition-all ${
              (!postText.trim() && selectedImages.length === 0) || isSubmitting
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
            {isSubmitting ? '✨' : 'Share'}
          </button>
        </div>

        <div className="p-4 space-y-4 max-h-[calc(90vh-80px)] overflow-y-auto">
          {/* User Info */}
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 rounded-full overflow-hidden bg-gradient-to-r from-pink-500 to-purple-600">
              <img src={user.profilePic} alt={user.name} className="w-full h-full object-cover" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-800">{user.name}</h3>
              <p className="text-sm text-gray-500">@{user.username}</p>
            </div>
          </div>

          {/* Mood Selector */}
          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Current Mood</p>
            <div className="flex space-x-2 overflow-x-auto pb-2">
              {moods.map((moodOption) => (
                <button
                  key={moodOption.value}
                  onClick={() => setMood(moodOption.value)}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-full whitespace-nowrap transition-all ${
                    mood === moodOption.value
                      ? `bg-gradient-to-r ${moodOption.color} text-white shadow-lg`
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >
                  <span>{moodOption.emoji}</span>
                  <span className="text-sm font-medium">{moodOption.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Text Input */}
          <textarea
            value={postText}
            onChange={(e) => setPostText(e.target.value)}
            placeholder={`What's on your mind, ${user.name.split(' ')[0]}? Share your vibe... ✨`}
            className="w-full p-4 border border-gray-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
            rows="4"
          />

          {/* Image Preview */}
          {selectedImages.length > 0 && (
            <div className="grid grid-cols-2 gap-2">
              {selectedImages.map((image) => (
                <div key={image.id} className="relative">
                  <img
                    src={image.url}
                    alt="Upload preview"
                    className="w-full h-32 object-cover rounded-2xl"
                  />
                  <button
                    onClick={() => removeImage(image.id)}
                    className="absolute top-2 right-2 bg-red-500 text-white p-1 rounded-full hover:bg-red-600 transition-colors"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center space-x-4 pt-4 border-t border-gray-100">
            <label className="flex items-center space-x-2 cursor-pointer hover:bg-gray-100 p-2 rounded-2xl transition-colors">
              <div className="w-10 h-10 bg-gradient-to-r from-green-400 to-blue-500 rounded-full flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
              <span className="text-sm font-medium">Photo</span>
              <input
                type="file"
                multiple
                accept="image/*"
                onChange={handleImageUpload}
                className="hidden"
              />
            </label>

            <button 
              onClick={() => setShowMusicModal(true)}
              className={`flex items-center space-x-2 hover:bg-gray-100 p-2 rounded-2xl transition-colors ${selectedMusic ? 'bg-purple-50' : ''}`}
            >
              <div className="w-10 h-10 bg-gradient-to-r from-purple-400 to-pink-500 rounded-full flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
              <div className="w-10 h-10 bg-gradient-to-r from-orange-400 to-red-500 rounded-full flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <span className="text-sm font-medium">
                {selectedLocation ? '📍 Added' : 'Location'}
              </span>
            </button>
          </div>

          {/* Character Count */}
          <div className="text-right">
            <span className={`text-sm ${postText.length > 280 ? 'text-red-500' : 'text-gray-400'}`}>
              {postText.length}/500
            </span>
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

export default CreatePost;