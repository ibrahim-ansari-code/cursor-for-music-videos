import React, { useState, useContext } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { AuthContext } from '../App';

const LoginForm = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [isEmailVerificationError, setIsEmailVerificationError] = useState(false);
  const [resendingEmail, setResendingEmail] = useState(false);
  const [resendSuccess, setResendSuccess] = useState(false);
  const navigate = useNavigate();
  const { login } = useContext(AuthContext);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    setIsEmailVerificationError(false);
    setResendSuccess(false);

    try {
      const success = await login(email, password);
      if (success) {
        navigate('/dashboard', { replace: true });
      } else {
        // Generic error for now, will be overridden if we detect a verification issue
        setError('Invalid email or password');
        
        // Check if this is an email verification issue
        // The actual API response would determine this logic
        try {
          const checkResponse = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/auth/check-email-status`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email }),
          });
          
          const checkData = await checkResponse.json();
          
          if (checkData.detail === 'Email not verified') {
            setIsEmailVerificationError(true);
            setError('Your email is not verified. Please check your inbox or click below to resend the verification link.');
          }
        } catch (checkErr) {
          // If we can't check verification status, stick with the generic error
          console.error('Error checking email verification status:', checkErr);
        }
      }
    } catch (err) {
      setError('Login failed. Please try again.');
      console.error('Login error:', err);
      
      // Check if the error message indicates email verification issue
      if (err.message && err.message.toLowerCase().includes('not verified')) {
        setIsEmailVerificationError(true);
        setError('Your email is not verified. Please check your inbox or click below to resend the verification link.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleResendVerification = async () => {
    setResendingEmail(true);
    setResendSuccess(false);
    
    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/auth/resend-verification`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });
      
      if (response.ok) {
        setResendSuccess(true);
      } else {
        const data = await response.json();
        setError(data.detail || 'Failed to resend verification email');
      }
    } catch (err) {
      setError('Failed to resend verification email. Please try again.');
      console.error('Resend verification error:', err);
    } finally {
      setResendingEmail(false);
    }
  };

  return (
    <div className="w-full h-full flex flex-col justify-center">
      <div className="sm:mx-auto sm:w-full">
        <h2 className="text-center text-3xl font-bold tracking-tight text-brand-green">
          Sign in to your account
        </h2>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full">
        <form className="space-y-6" onSubmit={handleSubmit}>
          <div>
            <label htmlFor="email-address" className="block text-sm font-medium text-gray-700">
              Email address
            </label>
            <input
              id="email-address"
              name="email"
              type="email"
              autoComplete="email"
              required
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-teal focus:outline-none focus:ring-brand-teal sm:text-sm"
              placeholder="Email address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700">
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-teal focus:outline-none focus:ring-brand-teal sm:text-sm"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          {error && (
            <div className="rounded-md bg-red-50 p-4">
              <div className="flex">
                <div className="text-sm text-red-700">{error}</div>
              </div>
            </div>
          )}

          {isEmailVerificationError && (
            <div className="mt-4">
              <button
                type="button"
                onClick={handleResendVerification}
                disabled={resendingEmail}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-brand-teal hover:bg-brand-teal/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-teal"
              >
                {resendingEmail ? 'Sending...' : 'Resend Verification Email'}
              </button>
            </div>
          )}

          {resendSuccess && (
            <div className="rounded-md bg-green-50 p-4">
              <div className="flex">
                <div className="text-sm text-green-700">Verification email sent! Please check your inbox.</div>
              </div>
            </div>
          )}

          <div>
            <button
              type="submit"
              disabled={loading}
              className="flex w-full justify-center rounded-md border border-transparent bg-brand-teal py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-brand-teal/90 focus:outline-none focus:ring-2 focus:ring-brand-teal focus:ring-offset-2 disabled:opacity-75"
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </div>

          <div className="text-center text-sm text-gray-600">
            Don't have an account?{' '}
            <Link to="/register" className="font-medium text-brand-teal hover:text-brand-teal/80">
              Register
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
};

export default LoginForm; 