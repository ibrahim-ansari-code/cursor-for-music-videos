import React, { createContext, useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';

// Pages
import Leases from './pages/Leases';
import Vendors from './pages/Vendors';
import Accounting from './pages/Accounting';
import Messages from './pages/Messages';
import Properties from './pages/Properties';
import PropertyDetail from './pages/PropertyDetail';
import Tenants from './pages/Tenants';
import Maintenance from './pages/Maintenance';
import Reports from './pages/Reports';
import Settings from './pages/Settings';

// Auth Context
export const AuthContext = createContext(null);

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Check authentication status on mount
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('token');
      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/auth/me`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (response.ok) {
          const userInfo = await response.json();
          
          // Ensure the user_type is in uppercase
          const userType = userInfo.user_type?.toUpperCase();
          userInfo.user_type = userType;
          
          // Update localStorage with the normalized user type
          localStorage.setItem('user_type', userType);
          localStorage.setItem('user', JSON.stringify(userInfo));
          
          console.log('Auth check: Updated user type to:', userType);
          
          setUser(userInfo);
        } else {
          // Clear invalid token
          console.error('Auth check failed, clearing credentials');
          localStorage.removeItem('token');
          localStorage.removeItem('user_type');
          localStorage.removeItem('user');
        }
      } catch (error) {
        console.error('Auth check failed:', error);
        localStorage.removeItem('token');
        localStorage.removeItem('user_type');
        localStorage.removeItem('user');
      }
      setLoading(false);
    };

    checkAuth();
  }, []);

  const login = async (email, password) => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/auth/token`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: new URLSearchParams({
          'username': email,
          'password': password,
        })
      });

      if (!response.ok) {
        console.error('Login failed:', await response.text());
        return false;
      }

      const data = await response.json();
      
      // Ensure the user_type is in uppercase to match the enum values
      const userType = data.user_type?.toUpperCase();
      console.log('Auth token response:', { 
        originalType: data.user_type,
        normalizedType: userType
      });
      
      // Store the uppercase user_type value
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('user_type', userType);
      console.log('Stored user type:', userType);

      const userResponse = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${data.access_token}`
        }
      });

      if (!userResponse.ok) {
        console.error('Failed to get user info:', await userResponse.text());
        return false;
      }

      const userInfo = await userResponse.json();
      
      // Make sure userInfo.user_type is also uppercase
      userInfo.user_type = userType;
      console.log('User info from /me endpoint:', userInfo);
      
      localStorage.setItem('user', JSON.stringify(userInfo));
      setUser(userInfo);

      return true;
    } catch (error) {
      console.error('Login error:', error);
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user_type');
    localStorage.removeItem('user');
    setUser(null);
  };

  const authValue = {
    user,
    login,
    logout,
    isAuthenticated: !!user,
  };

  if (loading) {
    return <div className="flex items-center justify-center h-screen">Loading...</div>;
  }

  return (
    <AuthContext.Provider value={authValue}>
      <Router>
        <ToastContainer position="top-right" autoClose={5000} />
        <Routes>
          <Route path="/" element={user ? <Layout /> : <Navigate to="/login" />}>
            <Route index element={<Navigate to="/dashboard" />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="properties" element={<Properties />} />
            <Route path="properties/:id" element={<PropertyDetail />} />
            <Route path="leases" element={<Leases />} />
            <Route path="vendors" element={<Vendors />} />
            <Route path="accounting" element={<Accounting />} />
            <Route path="messages" element={<Messages />} />
            <Route path="tenants" element={<Tenants />} />
            <Route path="maintenance" element={<Maintenance />} />
            <Route path="reports" element={<Reports />} />
            <Route path="settings" element={<Settings />} />
          </Route>
          <Route path="/login" element={!user ? <LoginPage /> : <Navigate to="/dashboard" />} />
          <Route path="/register" element={!user ? <RegisterPage /> : <Navigate to="/dashboard" />} />
          <Route path="*" element={<Navigate to={user ? "/dashboard" : "/login"} />} />
        </Routes>
      </Router>
    </AuthContext.Provider>
  );
}

export default App;