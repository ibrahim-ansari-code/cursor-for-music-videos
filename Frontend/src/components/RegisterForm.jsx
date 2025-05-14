import React, { useState, useContext } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { AuthContext } from '../App';
import { supabase } from '../supabaseClient'; // Import Supabase client

const RegisterForm = () => {
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [registrationSuccess, setRegistrationSuccess] = useState(false);
  const [resendingEmail, setResendingEmail] = useState(false);
  const [resendSuccess, setResendSuccess] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    setRegistrationSuccess(false);
    setResendSuccess(false);

    const userData = {
      email,
      password,
      options: {
        data: { // Custom data to be stored in Supabase user_metadata
          first_name: firstName,
          last_name: lastName,
          phone: phone || null,
          user_type: "LANDLORD" 
        }
      }
    };

    try {
      const { data, error } = await supabase.auth.signUp(userData);

      if (error) {
        setError(error.message || 'Registration failed. Please try again.');
        console.error('Supabase SignUp error:', error);
        setLoading(false);
        return;
      }

      if (data.user) {
        // Supabase registration successful
        // Now, call backend to sync user to local DB
        // This is a new endpoint you'll need to create on your backend.
        try {
          const syncResponse = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/sync-user`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              // If your sync endpoint requires auth (e.g. an admin/service key for this action),
              // you'd add it here. However, this specific sync is for a new user.
              // Alternatively, this could be a Supabase function triggered by new auth.users row.
            },
            body: JSON.stringify({
              supabase_user_id: data.user.id,
              email: data.user.email,
              first_name: firstName,
              last_name: lastName,
              phone: phone || null,
              user_type: "LANDLORD",
              // Include any other fields your backend /sync-user expects or that your local User model needs
            }),
          });

          const syncData = await syncResponse.json();

          if (!syncResponse.ok) {
            // Handle error from your /sync-user endpoint
            console.error('Error syncing user to local DB:', syncData);
            // Decide on user experience: inform them verification email sent but profile sync failed?
            // Or treat as full registration failure for now?
            setError(syncData.detail || 'Registration partially failed (user created, profile sync failed). Please contact support.');
            // Potentially, you might want to delete the Supabase user if local sync fails critically.
            // await supabase.auth.admin.deleteUser(data.user.id) // Requires admin privileges on Supabase client
            setLoading(false);
            return;
          }
          
          // User synced to local DB successfully
          setRegistrationSuccess(true);
          // Clear the form
          setFirstName('');
          setLastName('');
          setPhone('');
          setEmail(''); // Keep email for resend verification if needed, or clear too
          setPassword('');

        } catch (syncError) {
          console.error('Error calling /sync-user endpoint:', syncError);
          setError('Registration partially failed (user created, profile sync had network issue). Please contact support.');
          // Potentially, delete Supabase user.
          setLoading(false);
          return;
        }

      } else {
        // Should not happen if error is not thrown, but as a fallback
        setError('Registration failed. No user data returned from Supabase.');
      }
      
    } catch (err) { // This catch is for errors not caught by supabase.auth.signUp's own error object
      // err is the error object thrown by handleResponse (via apiRegister)
      // It should have a .message property, and .data for JSON error details
      let displayError = 'Registration failed. Please try again.';
      if (err.message) {
        displayError = err.message;
      }

      if (err.data && err.data.detail) {
        if (Array.isArray(err.data.detail)) { // For RequestValidationError (FastAPI Pydantic errors)
          displayError = err.data.detail.map(d => {
            const field = d.loc && d.loc.length > 1 ? d.loc[d.loc.length - 1] : (d.loc && d.loc.length === 1 ? d.loc[0] : 'Error');
            return `${field}: ${d.msg}`;
          }).join('; ');
        } else if (typeof err.data.detail === 'string') { // For HTTPException (FastAPI general errors)
          displayError = err.data.detail;
        }
      }
      setError(displayError);
      console.error('Registration error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleResendVerification = async () => {
    setResendingEmail(true);
    setResendSuccess(false);
    setError(''); // Clear previous errors
    
    // To resend verification, Supabase needs the email of the user.
    // If the form was cleared, we need to ensure `email` state is still available or re-fetch it.
    // For now, assuming `email` state used in the form is the one we need to resend for.
    if (!email) {
        setError('Please enter the email address to resend verification.');
        setResendingEmail(false);
        return;
    }

    try {
      // Supabase client-side resend confirmation is for the *currently signed-in user* typically.
      // For a newly registered user who isn't signed in, or if admin wants to resend for *any* user,
      // this usually needs to be a backend operation using Supabase Admin SDK.
      // The old /api/auth/resend-verification can be adapted for this.
      // For a quick client-side attempt (might have limitations for unconfirmed users):
      // const { error } = await supabase.auth.resend({ type: 'signup', email: email });
      // if (error) throw error;

      // Sticking to the existing pattern of calling a backend endpoint for this:
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/auth/resend-verification`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }), // Backend needs to handle this email
      });
      
      const responseData = await response.json();
      if (response.ok) {
        setResendSuccess(true);
      } else {
        setError(responseData.detail || 'Failed to resend verification email');
      }
    } catch (err) {
      setError('Failed to resend verification email. Please try again.');
      console.error('Resend verification error:', err);
    } finally {
      setResendingEmail(false);
    }
  };

  const validatePhone = (value) => {
    const phoneRegex = /^[0-9]{10}$/;
    return phoneRegex.test(value);
  };

  // If registration was successful, show success message instead of form
  if (registrationSuccess) {
    return (
      <div className="w-full h-full flex flex-col justify-center items-center p-6">
        <div className="text-center mb-8">
          <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 mb-4">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900">Account created!</h3>
          <p className="mt-2 text-sm text-gray-600">
            Please check your email to verify your account before signing in.
          </p>
        </div>
        
        <div className="w-full max-w-md">
          <button
            type="button"
            onClick={handleResendVerification}
            disabled={resendingEmail}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-brand-teal hover:bg-brand-teal/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-teal"
          >
            {resendingEmail ? 'Sending...' : 'Resend Verification Email'}
          </button>
          
          {resendSuccess && (
            <div className="mt-4 rounded-md bg-green-50 p-4">
              <div className="flex">
                <div className="text-sm text-green-700">Verification email sent! Please check your inbox.</div>
              </div>
            </div>
          )}
          
          <div className="mt-6 text-center">
            <Link to="/login" className="font-medium text-brand-teal hover:text-brand-teal/80">
              Go to login page
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col justify-center">
      <div className="sm:mx-auto sm:w-full">
        <h2 className="text-center text-3xl font-bold tracking-tight text-brand-green">
          Create your account
        </h2>
        <p className="mt-2 text-center text-sm text-gray-600">
          Join Brikli to manage your properties more efficiently
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full">
        <form className="space-y-6" onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="first-name" className="block text-sm font-medium text-gray-700">
                First Name
              </label>
              <input
                id="first-name"
                name="firstName"
                type="text"
                required
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-teal focus:outline-none focus:ring-brand-teal sm:text-sm"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
              />
            </div>
            
            <div>
              <label htmlFor="last-name" className="block text-sm font-medium text-gray-700">
                Last Name
              </label>
              <input
                id="last-name"
                name="lastName"
                type="text"
                required
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-teal focus:outline-none focus:ring-brand-teal sm:text-sm"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
              />
            </div>
          </div>

          <div>
            <label htmlFor="phone" className="block text-sm font-medium text-gray-700">
              Phone Number
            </label>
            <input
              id="phone"
              name="phone"
              type="tel"
              required
              className={`mt-1 block w-full rounded-md border ${
                phone && !validatePhone(phone)
                  ? 'border-red-300 focus:border-red-500 focus:ring-red-500'
                  : 'border-gray-300 focus:border-brand-teal focus:ring-brand-teal'
              } px-3 py-2 shadow-sm focus:outline-none sm:text-sm`}
              placeholder="10-digit phone number"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
            {phone && !validatePhone(phone) && (
              <p className="mt-1 text-sm text-red-600">Please enter a valid 10-digit phone number</p>
            )}
          </div>

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
              autoComplete="new-password"
              required
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-teal focus:outline-none focus:ring-brand-teal sm:text-sm"
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

          <div>
            <button
              type="submit"
              disabled={loading}
              className="flex w-full justify-center rounded-md border border-transparent bg-brand-teal py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-brand-teal/90 focus:outline-none focus:ring-2 focus:ring-brand-teal focus:ring-offset-2 disabled:opacity-75"
            >
              {loading ? 'Creating account...' : 'Create account'}
            </button>
          </div>

          <div className="text-center text-sm text-gray-600">
            Already have an account?{' '}
            <Link to="/login" className="font-medium text-brand-teal hover:text-brand-teal/80">
              Sign in
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
};

export default RegisterForm; 