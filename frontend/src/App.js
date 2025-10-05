import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { hydrateUser } from './state/hydrateUser';
import WelcomePage from './components/WelcomePage';
import SocialFeed from './components/SocialFeed';
import WhatsNew from './components/WhatsNew';
import UserProfile from './components/UserProfile';
import InstagramProfile from './components/InstagramProfile';
import Discover from './components/Discover';
import RegistrationFlow from './components/RegistrationFlow';

function App() {
  const [user, setUser] = useState(null);
  const [theme] = useState('passion'); // eslint-disable-line no-unused-vars
  const [isRegistered, setIsRegistered] = useState(false);

  useEffect(() => { 
    hydrateUser(); 
    
    // Initialize Telegram WebApp theme
    if (window.Telegram?.WebApp) {
      const tg = window.Telegram.WebApp;
      const telegramUser = tg.initDataUnsafe?.user; // eslint-disable-line no-unused-vars
      
      // Set theme based on Telegram theme
      if (tg.colorScheme === 'dark') {
        document.body.classList.add('dark');
      }
    }

    // Check if user is already registered
    const savedUser = localStorage.getItem('luvhive_user');
    console.log('🔍 Checking for existing user in localStorage:', savedUser ? 'Found' : 'Not found');
    
    if (savedUser) {
      try {
        const userData = JSON.parse(savedUser);
        console.log('✅ Loading existing user:', userData.name || userData.username);
        setUser(userData);
        setIsRegistered(true);
      } catch (error) {
        console.error('❌ Error parsing saved user data:', error);
        localStorage.removeItem('luvhive_user'); // Remove corrupted data
      }
    } else {
      console.log('🆕 No existing user found, user needs to register');
    }
  }, []);

  const handleRegistrationComplete = (userData) => {
    console.log('🎉 Registration completed, setting user state:', userData);
    setUser(userData);
    setIsRegistered(true);
    
    // Double-check localStorage is set correctly
    const savedUser = localStorage.getItem('luvhive_user');
    console.log('✅ Verified localStorage user data:', savedUser ? 'Present' : 'Missing');
  };

  const handleEnterLuvHive = () => {
    console.log('🎯 handleEnterLuvHive called. isRegistered:', isRegistered, 'user:', user);
    
    if (isRegistered && user) {
      // User is registered, go to feed
      console.log('✅ User already registered, redirecting to feed');
      return '/feed';
    } else {
      // User needs to register
      console.log('📝 User not registered, redirecting to registration');
      return '/register';
    }
  };

  return (
    <Router>
      <div className="App">
        <Routes>
          <Route 
            path="/" 
            element={<WelcomePage user={user} theme={theme} onEnterLuvHive={handleEnterLuvHive} />} 
          />
          <Route 
            path="/register" 
            element={<RegistrationFlow onComplete={handleRegistrationComplete} />} 
          />
          <Route 
            path="/feed" 
            element={<SocialFeed user={user} theme={theme} />} 
          />
          <Route path="/whats-new" element={<WhatsNew theme={theme} />} />
          <Route 
            path="/profile" 
            element={<UserProfile user={user} theme={theme} />} 
          />
          <Route 
            path="/instagram-profile" 
            element={<InstagramProfile user={user} />} 
          />
          <Route 
            path="/discover" 
            element={<Discover user={user} theme={theme} />} 
          />
        </Routes>
      </div>
    </Router>
  );
}

export default App;