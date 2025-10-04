import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

const RegistrationFlow = ({ onComplete }) => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    name: '',
    username: '',
    age: '',
    gender: '',
    profilePic: null,
    bio: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [profilePicPreview, setProfilePicPreview] = useState(null);

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleProfilePicChange = (event) => {
    const file = event.target.files[0];
    if (file) {
      setFormData(prev => ({ ...prev, profilePic: file }));
      const reader = new FileReader();
      reader.onload = (e) => setProfilePicPreview(e.target.result);
      reader.readAsDataURL(file);
    }
  };

  const generateAvatar = (name) => {
    return `https://api.dicebear.com/7.x/avataaars/svg?seed=${name}&backgroundColor=b6e3f4,c0aede,d1d4f9,ffd5dc,ffdfbf`;
  };

  const handleNext = () => {
    if (step < 4) {
      setStep(step + 1);
    } else {
      handleSubmit();
    }
  };

  const handleBack = () => {
    if (step > 1) {
      setStep(step - 1);
    } else {
      navigate('/');
    }
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      // Create user profile
      const userData = {
        ...formData,
        profilePic: profilePicPreview || generateAvatar(formData.name),
        joinDate: new Date().toISOString(),
        stats: { posts: 0, followers: 0, following: 0, sparks: 0 }
      };
      
      // Save to localStorage for now (in real app, save to backend)
      localStorage.setItem('luvhive_user', JSON.stringify(userData));
      
      // Complete registration
      setTimeout(() => {
        onComplete(userData);
        navigate('/feed');
      }, 1500);
    } catch (error) {
      console.error('Registration error:', error);
      setIsSubmitting(false);
    }
  };

  const isStepValid = () => {
    switch (step) {
      case 1: return formData.name.trim().length >= 2;
      case 2: return formData.username.trim().length >= 3 && formData.age >= 18;
      case 3: return formData.gender !== '';
      case 4: return true;
      default: return false;
    }
  };

  if (isSubmitting) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-pink-500 via-purple-600 to-indigo-700 flex items-center justify-center">
        <div className="text-center">
          <div className="w-20 h-20 bg-white/20 rounded-full flex items-center justify-center mb-6 animate-pulse-love mx-auto">
            <span className="text-3xl animate-heart-beat">💫</span>
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">Creating your LuvHive profile...</h2>
          <p className="text-white/80">Welcome to the family! ✨</p>
          <div className="mt-4 flex justify-center space-x-1">
            <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce"></div>
            <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce delay-100"></div>
            <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce delay-200"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-pink-500 via-purple-600 to-indigo-700">
      {/* Header */}
      <div className="bg-white/10 backdrop-blur-lg border-b border-white/20 px-4 py-4">
        <div className="flex items-center justify-between max-w-md mx-auto">
          <button
            onClick={handleBack}
            className="p-2 rounded-full bg-white/20 hover:bg-white/30 transition-all duration-200 transform hover:scale-110"
          >
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          
          <h1 className="text-xl font-bold text-white">Join LuvHive</h1>
          
          <div className="w-10 h-10 flex items-center justify-center">
            <span className="text-white text-sm font-semibold">{step}/4</span>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="max-w-md mx-auto px-4 py-4">
        <div className="flex space-x-2">
          {[1, 2, 3, 4].map((num) => (
            <div
              key={num}
              className={`flex-1 h-1 rounded-full transition-all duration-300 ${
                num <= step ? 'bg-white' : 'bg-white/30'
              }`}
            />
          ))}
        </div>
      </div>

      <div className="max-w-md mx-auto px-4">
        {/* Step 1: Name */}
        {step === 1 && (
          <div className="bg-white/95 backdrop-blur-lg rounded-3xl p-8 shadow-2xl">
            <div className="text-center mb-8">
              <div className="w-16 h-16 bg-gradient-to-r from-pink-500 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-4 animate-pulse-love">
                <span className="text-2xl">👋</span>
              </div>
              <h2 className="text-3xl font-bold text-gray-800 mb-2">What's your name?</h2>
              <p className="text-gray-600">Let's start with how we should call you</p>
            </div>

            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Full Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => handleInputChange('name', e.target.value)}
                  placeholder="Enter your full name"
                  className="w-full px-4 py-4 border border-gray-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent text-lg"
                />
              </div>

              <button
                onClick={handleNext}
                disabled={!isStepValid()}
                className={`w-full py-4 rounded-2xl font-semibold text-lg transition-all duration-200 ${
                  isStepValid()
                    ? 'bg-gradient-to-r from-pink-500 to-purple-600 text-white hover:shadow-lg transform hover:scale-105'
                    : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                }`}
              >
                Continue
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Username & Age */}
        {step === 2 && (
          <div className="bg-white/95 backdrop-blur-lg rounded-3xl p-8 shadow-2xl">
            <div className="text-center mb-8">
              <div className="w-16 h-16 bg-gradient-to-r from-purple-500 to-indigo-600 rounded-full flex items-center justify-center mx-auto mb-4 animate-pulse-love">
                <span className="text-2xl">✨</span>
              </div>
              <h2 className="text-3xl font-bold text-gray-800 mb-2">Choose your identity</h2>
              <p className="text-gray-600">Pick a unique username and tell us your age</p>
            </div>

            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Username</label>
                <div className="relative">
                  <span className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400">@</span>
                  <input
                    type="text"
                    value={formData.username}
                    onChange={(e) => handleInputChange('username', e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ''))}
                    placeholder="username"
                    className="w-full pl-8 pr-4 py-4 border border-gray-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent text-lg"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Age</label>
                <input
                  type="number"
                  value={formData.age}
                  onChange={(e) => handleInputChange('age', parseInt(e.target.value) || '')}
                  placeholder="18+"
                  min="18"
                  max="100"
                  className="w-full px-4 py-4 border border-gray-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent text-lg"
                />
              </div>

              <button
                onClick={handleNext}
                disabled={!isStepValid()}
                className={`w-full py-4 rounded-2xl font-semibold text-lg transition-all duration-200 ${
                  isStepValid()
                    ? 'bg-gradient-to-r from-purple-500 to-indigo-600 text-white hover:shadow-lg transform hover:scale-105'
                    : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                }`}
              >
                Continue
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Gender */}
        {step === 3 && (
          <div className="bg-white/95 backdrop-blur-lg rounded-3xl p-8 shadow-2xl">
            <div className="text-center mb-8">
              <div className="w-16 h-16 bg-gradient-to-r from-indigo-500 to-pink-600 rounded-full flex items-center justify-center mx-auto mb-4 animate-pulse-love">
                <span className="text-2xl">🎭</span>
              </div>
              <h2 className="text-3xl font-bold text-gray-800 mb-2">Express yourself</h2>
              <p className="text-gray-600">How do you identify?</p>
            </div>

            <div className="space-y-4">
              {[
                { value: 'male', label: 'Male', icon: '👨', color: 'from-blue-400 to-indigo-500' },
                { value: 'female', label: 'Female', icon: '👩', color: 'from-pink-400 to-purple-500' },
                { value: 'prefer-not-to-say', label: 'Don\'t want to say', icon: '✨', color: 'from-gray-400 to-gray-500' }
              ].map((option) => (
                <button
                  key={option.value}
                  onClick={() => handleInputChange('gender', option.value)}
                  className={`w-full p-4 rounded-2xl border-2 transition-all duration-200 transform hover:scale-105 ${
                    formData.gender === option.value
                      ? `bg-gradient-to-r ${option.color} text-white border-transparent shadow-lg`
                      : 'bg-white border-gray-200 hover:border-purple-300'
                  }`}
                >
                  <div className="flex items-center space-x-4">
                    <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                      formData.gender === option.value ? 'bg-white/20' : 'bg-gray-100'
                    }`}>
                      <span className="text-2xl">{option.icon}</span>
                    </div>
                    <span className={`font-semibold text-lg ${
                      formData.gender === option.value ? 'text-white' : 'text-gray-800'
                    }`}>
                      {option.label}
                    </span>
                  </div>
                </button>
              ))}
            </div>

            <button
              onClick={handleNext}
              disabled={!isStepValid()}
              className={`w-full mt-6 py-4 rounded-2xl font-semibold text-lg transition-all duration-200 ${
                isStepValid()
                  ? 'bg-gradient-to-r from-indigo-500 to-pink-600 text-white hover:shadow-lg transform hover:scale-105'
                  : 'bg-gray-200 text-gray-400 cursor-not-allowed'
              }`}
            >
              Continue
            </button>
          </div>
        )}

        {/* Step 4: Profile Picture & Bio */}
        {step === 4 && (
          <div className="bg-white/95 backdrop-blur-lg rounded-3xl p-8 shadow-2xl">
            <div className="text-center mb-8">
              <div className="w-16 h-16 bg-gradient-to-r from-pink-500 to-orange-500 rounded-full flex items-center justify-center mx-auto mb-4 animate-pulse-love">
                <span className="text-2xl">📸</span>
              </div>
              <h2 className="text-3xl font-bold text-gray-800 mb-2">Complete your profile</h2>
              <p className="text-gray-600">Add a photo and tell us about yourself</p>
            </div>

            <div className="space-y-6">
              {/* Profile Picture Upload */}
              <div className="text-center">
                <div className="relative inline-block">
                  <div className="w-32 h-32 rounded-full overflow-hidden bg-gradient-to-r from-pink-500 to-purple-600 mx-auto mb-4 border-4 border-white shadow-lg">
                    {profilePicPreview ? (
                      <img src={profilePicPreview} alt="Profile" className="w-full h-full object-cover" />
                    ) : (
                      <img src={generateAvatar(formData.name)} alt="Avatar" className="w-full h-full object-cover" />
                    )}
                  </div>
                  <label className="absolute bottom-0 right-0 bg-purple-600 text-white p-2 rounded-full cursor-pointer hover:bg-purple-700 transition-colors shadow-lg">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                    <input
                      type="file"
                      accept="image/*"
                      onChange={handleProfilePicChange}
                      className="hidden"
                    />
                  </label>
                </div>
                <p className="text-sm text-gray-500">Tap to upload your photo or use generated avatar</p>
              </div>

              {/* Bio */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Bio (Optional)</label>
                <textarea
                  value={formData.bio}
                  onChange={(e) => handleInputChange('bio', e.target.value)}
                  placeholder="Tell the world something about yourself... ✨"
                  rows="3"
                  className="w-full px-4 py-3 border border-gray-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
                />
              </div>

              <button
                onClick={handleNext}
                className="w-full bg-gradient-to-r from-pink-500 to-orange-500 text-white py-4 rounded-2xl font-semibold text-lg hover:shadow-lg transform hover:scale-105 transition-all duration-200"
              >
                🚀 Join LuvHive Community
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default RegistrationFlow;