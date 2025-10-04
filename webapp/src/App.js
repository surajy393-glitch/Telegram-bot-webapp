import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
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
    if (savedUser) {
      const userData = JSON.parse(savedUser);
      setUser(userData);
      setIsRegistered(true);
    }
  }, []);

  const handleRegistrationComplete = (userData) => {
    setUser(userData);
    setIsRegistered(true);
  };

  const handleEnterLuvHive = () => {
    if (isRegistered && user) {
      // User is registered, go to feed
      return '/feed';
    } else {
      // User needs to register
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