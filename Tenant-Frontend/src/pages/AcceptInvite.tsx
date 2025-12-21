import React, { useState, useEffect, useContext, useMemo } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { AuthContext } from '@/contexts/AuthContext';
import BrandingPanel from '@/components/auth/BrandingPanel';
import {
  validateInvitationToken,
  acceptInvitation,
  registerAndAcceptInvitation,
  type InvitationValidateResponse,
} from '@/utils/api/invitations';
import { supabase } from '@/utils/supabaseClient';

/**
 * Extract token from URL fragment for security.
 * Using fragment (#token=) instead of query param (?token=) prevents:
 * - Token leakage via browser history
 * - Token leakage via HTTP Referer headers
 * - Token logging by intermediary servers
 */
const getTokenFromFragment = (): string | null => {
  const hash = window.location.hash;
  if (!hash || !hash.startsWith('#token=')) {
    return null;
  }
  return hash.slice(7); // Remove "#token=" prefix
};

/**
 * Password Requirement Component
 * Shows a checkmark or X icon with requirement text
 */
const PasswordRequirement: React.FC<{ met: boolean; text: string }> = ({ met, text }) => (
  <div className="flex items-center gap-2 text-xs">
    {met ? (
      <svg className="w-4 h-4 text-green-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ) : (
      <svg className="w-4 h-4 text-gray-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    )}
    <span className={met ? 'text-green-700' : 'text-gray-600'}>
      {text}
    </span>
  </div>
);

/**
 * AcceptInvite Page Component
 *
 * Streamlined tenant invitation acceptance flow:
 * 1. Validates the invitation token from URL fragment
 * 2. Displays invitation details (landlord, property, etc.)
 * 3. Creates account OR signs in existing user
 * 4. Auto-accepts invitation and redirects to dashboard
 *
 * Note: Email verification is skipped because clicking the invitation
 * link already proves email ownership (industry standard pattern used
 * by Slack, Notion, Discourse, etc.)
 */
const AcceptInvite: React.FC = () => {
  const navigate = useNavigate();

  // Extract token from URL fragment (more secure than query params)
  const token = useMemo(() => getTokenFromFragment(), []);

  const authContext = useContext(AuthContext);
  const { user, isAuthenticated, loading: authLoading } = authContext || {};

  // Invitation state
  const [invitationData, setInvitationData] = useState<InvitationValidateResponse | null>(null);
  const [validating, setValidating] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Auth form state
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [password, setPassword] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Accept state (for already authenticated users)
  const [accepting, setAccepting] = useState(false);
  const [acceptError, setAcceptError] = useState<string | null>(null);

  // Password validation
  const passwordRequirements = useMemo(() => ({
    minLength: password.length >= 8,
    hasLowercase: /[a-z]/.test(password),
    hasUppercase: /[A-Z]/.test(password),
    hasNumber: /[0-9]/.test(password),
    hasSpecial: /[!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?~]/.test(password),
  }), [password]);

  const isPasswordValid = useMemo(() =>
    Object.values(passwordRequirements).every(Boolean),
    [passwordRequirements]
  );

  // Validate token on mount
  useEffect(() => {
    const validateToken = async () => {
      if (!token) {
        setError('No invitation token provided. Please use the link from your invitation email.');
        setValidating(false);
        return;
      }

      try {
        const data = await validateInvitationToken(token);
        setInvitationData(data);
      } catch (err) {
        console.error('Token validation error:', err);
        setError(err instanceof Error ? err.message : 'Failed to validate invitation');
      } finally {
        setValidating(false);
      }
    };

    validateToken();
  }, [token]);

  // Auto-accept if user is already authenticated with matching email
  useEffect(() => {
    if (isAuthenticated && user && invitationData?.valid && token && !accepting) {
      // Check if email matches
      if (user.email?.toLowerCase() === invitationData.email?.toLowerCase()) {
        handleAcceptInvitation();
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, user, invitationData]);

  // Handle new user registration (streamlined - no email verification needed)
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setIsRegistering(true);

    if (!password) {
      setFormError('Please enter a password');
      setIsRegistering(false);
      return;
    }

    if (!isPasswordValid) {
      setFormError('Password does not meet all requirements');
      setIsRegistering(false);
      return;
    }

    if (!token) {
      setFormError('Invalid invitation token');
      setIsRegistering(false);
      return;
    }

    try {
      // Use backend endpoint that handles everything:
      // 1. Creates Supabase user (with email pre-confirmed)
      // 2. Creates backend User record with user_type=TENANT
      // 3. Accepts invitation
      // 4. Returns session tokens
      console.log('[AcceptInvite] Calling registerAndAcceptInvitation...');
      const result = await registerAndAcceptInvitation(token, password, firstName, lastName);
      console.log('[AcceptInvite] Registration result:', result);

      if (!result.success) {
        setFormError(result.message || 'Registration failed');
        setIsRegistering(false);
        return;
      }

      // Sign in with the new credentials (this triggers AuthProvider's onAuthStateChange)
      console.log('[AcceptInvite] Signing in with new credentials...');
      const { error: signInError } = await supabase.auth.signInWithPassword({
        email: invitationData?.email ?? '',
        password: password,
      });

      if (signInError) {
        console.error('[AcceptInvite] Sign in error:', signInError);
        setFormError('Account created but sign-in failed. Please try logging in.');
        setIsRegistering(false);
        return;
      }

      // The AuthProvider's onAuthStateChange will handle fetching the user profile
      // and redirecting. We just need to navigate to trigger the protected route check.
      console.log('[AcceptInvite] Sign in successful, navigating to dashboard...');
      navigate('/dashboard', { replace: true });

    } catch (err) {
      console.error('[AcceptInvite] Registration error:', err);
      setFormError(err instanceof Error ? err.message : 'Registration failed');
      setIsRegistering(false);
    }
  };

  // Handle invitation acceptance (for already authenticated users)
  const handleAcceptInvitation = async () => {
    if (!token) return;

    setAccepting(true);
    setAcceptError(null);

    try {
      const result = await acceptInvitation(token);

      if (result.success) {
        navigate('/dashboard', { replace: true });
      } else {
        setAcceptError(result.message || 'Failed to accept invitation');
      }
    } catch (err) {
      console.error('Accept invitation error:', err);
      setAcceptError(err instanceof Error ? err.message : 'Failed to accept invitation');
    } finally {
      setAccepting(false);
    }
  };

  // Calculate days until expiry
  const getDaysUntilExpiry = (): number | null => {
    if (!invitationData?.expires_at) return null;
    const expiresAt = new Date(invitationData.expires_at);
    const now = new Date();
    const diffTime = expiresAt.getTime() - now.getTime();
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  };

  // Loading state
  if (validating || authLoading) {
    return (
      <div className="min-h-screen flex bg-gray-50">
        <div className="hidden md:block md:w-3/5 sticky top-0 h-screen overflow-hidden">
          <BrandingPanel />
        </div>
        <div className="w-full md:w-2/5 bg-white flex items-center justify-center p-8 md:p-12 overflow-y-auto">
          <div className="text-center">
            <div className="w-12 h-12 border-4 border-brand-teal border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="mt-4 text-gray-600">Validating invitation...</p>
          </div>
        </div>
      </div>
    );
  }

  // Error state (no token or validation failed)
  if (error || !invitationData?.valid) {
    return (
      <div className="min-h-screen flex bg-gray-50">
        <div className="hidden md:block md:w-3/5 sticky top-0 h-screen overflow-hidden">
          <BrandingPanel />
        </div>
        <div className="w-full md:w-2/5 bg-white flex items-center justify-center p-8 md:p-12 overflow-y-auto">
          <div className="w-full max-w-sm text-center">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Invitation Invalid</h2>
            <p className="text-gray-600 mb-6">
              {error || invitationData?.message || 'This invitation is no longer valid.'}
            </p>
            <Link
              to="/login"
              className="inline-flex items-center justify-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-brand-teal hover:bg-brand-teal/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-teal"
            >
              Go to Login
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // Email mismatch check for authenticated users
  const emailMismatch = isAuthenticated && user &&
    user.email?.toLowerCase() !== invitationData.email?.toLowerCase();

  // Valid invitation - show details and auth/accept UI
  return (
    <div className="min-h-screen flex bg-gray-50">
      {/* Left Column - Branding Panel (Fixed) */}
      <div className="hidden md:block md:w-3/5 sticky top-0 h-screen overflow-hidden">
        <BrandingPanel />
      </div>

      {/* Right Column - Invitation Details & Auth (Scrollable) */}
      <div className="w-full md:w-2/5 bg-white flex items-center justify-center p-8 md:p-12 overflow-y-auto">
        <div className="w-full max-w-sm my-8">
          {/* Invitation Header */}
          <div className="text-center mb-8">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">You're Invited!</h2>
            <p className="text-gray-600">
              Your landlord, {invitationData.landlord_name}, has invited you to join the Tenant Portal
            </p>
          </div>

          {/* Invitation Details Card - only show if there's content */}
          {(invitationData.property_name || invitationData.unit_name || (getDaysUntilExpiry() !== null && getDaysUntilExpiry()! <= 3)) && (
            <div className="bg-gray-50 rounded-lg p-4 mb-6 border border-gray-200">
              <div className="space-y-3">
                {invitationData.property_name && (
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-white rounded-lg flex items-center justify-center shadow-sm">
                      <svg className="w-4 h-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 uppercase font-medium">Property</p>
                      <p className="text-sm font-semibold text-gray-900">{invitationData.property_name}</p>
                    </div>
                  </div>
                )}

                {invitationData.unit_name && (
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-white rounded-lg flex items-center justify-center shadow-sm">
                      <svg className="w-4 h-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 uppercase font-medium">Unit</p>
                      <p className="text-sm font-semibold text-gray-900">{invitationData.unit_name}</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Expiry Notice */}
              {getDaysUntilExpiry() !== null && getDaysUntilExpiry()! <= 3 && (
                <div className={`${invitationData.property_name || invitationData.unit_name ? 'mt-4' : ''} p-3 bg-yellow-50 rounded-md border border-yellow-200`}>
                  <div className="flex items-center gap-2">
                    <svg className="w-4 h-4 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p className="text-sm text-yellow-700">
                      Expires in {getDaysUntilExpiry()} day{getDaysUntilExpiry() !== 1 ? 's' : ''}
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Email Mismatch Error */}
          {emailMismatch && (
            <div className="mb-6 p-4 bg-red-50 rounded-lg border border-red-200">
              <div className="flex items-start gap-3">
                <svg className="w-5 h-5 text-red-500 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <div>
                  <p className="text-sm font-medium text-red-800">Email Mismatch</p>
                  <p className="text-sm text-red-700 mt-1">
                    You're signed in as <strong>{user?.email}</strong>, but this invitation was sent to <strong>{invitationData.email}</strong>.
                  </p>
                  <button
                    onClick={async () => {
                      await supabase.auth.signOut();
                      window.location.reload();
                    }}
                    className="mt-2 text-sm font-medium text-red-700 hover:text-red-800 underline"
                  >
                    Sign out and try again
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Accept Error */}
          {acceptError && (
            <div className="mb-6 p-4 bg-red-50 rounded-lg border border-red-200">
              <p className="text-sm text-red-700">{acceptError}</p>
            </div>
          )}

          {/* Auth/Accept Section */}
          {!isAuthenticated ? (
            // Not logged in - show registration form
            <div>
              <form onSubmit={handleRegister} className="space-y-4">
                {/* Name fields */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label htmlFor="firstName" className="block text-sm font-medium text-gray-700">
                      First name
                    </label>
                    <input
                      id="firstName"
                      type="text"
                      autoComplete="given-name"
                      required
                      value={firstName}
                      onChange={(e) => setFirstName(e.target.value)}
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-teal focus:outline-none focus:ring-brand-teal sm:text-sm"
                      placeholder="John"
                    />
                  </div>
                  <div>
                    <label htmlFor="lastName" className="block text-sm font-medium text-gray-700">
                      Last name
                    </label>
                    <input
                      id="lastName"
                      type="text"
                      autoComplete="family-name"
                      required
                      value={lastName}
                      onChange={(e) => setLastName(e.target.value)}
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-teal focus:outline-none focus:ring-brand-teal sm:text-sm"
                      placeholder="Doe"
                    />
                  </div>
                </div>

                {/* Email (read-only, from invitation) */}
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                    Email address
                  </label>
                  <input
                    id="email"
                    type="email"
                    value={invitationData.email || ''}
                    readOnly
                    className="mt-1 block w-full rounded-md border border-gray-200 bg-gray-50 px-3 py-2 shadow-sm text-gray-600 cursor-not-allowed sm:text-sm"
                  />
                </div>

                {/* Password */}
                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                    Create Password
                  </label>
                  <input
                    id="password"
                    type="password"
                    autoComplete="new-password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand-teal focus:outline-none focus:ring-brand-teal sm:text-sm"
                    placeholder="Create a strong password"
                  />

                  {/* Password Requirements */}
                  {password.length > 0 && (
                    <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200 space-y-1.5">
                      <p className="text-xs font-medium text-gray-700 mb-1.5">Password must contain:</p>
                      <div className="space-y-1">
                        <PasswordRequirement met={passwordRequirements.minLength} text="At least 8 characters" />
                        <PasswordRequirement met={passwordRequirements.hasLowercase} text="One lowercase letter (a-z)" />
                        <PasswordRequirement met={passwordRequirements.hasUppercase} text="One uppercase letter (A-Z)" />
                        <PasswordRequirement met={passwordRequirements.hasNumber} text="One number (0-9)" />
                        <PasswordRequirement met={passwordRequirements.hasSpecial} text="One special character (!@#$%^&*...)" />
                      </div>
                    </div>
                  )}
                </div>

                {formError && (
                  <div className="rounded-md bg-red-50 p-3">
                    <p className="text-sm text-red-700">{formError}</p>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={isRegistering || !isPasswordValid}
                  className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-brand-green hover:bg-brand-green/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-green disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
                >
                  {isRegistering ? (
                    <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                  ) : (
                    'Create Account & Continue'
                  )}
                </button>
              </form>
            </div>
          ) : !emailMismatch ? (
            // Logged in with matching email - show accept button
            <div>
              {accepting ? (
                <div className="text-center py-4">
                  <div className="w-8 h-8 border-4 border-brand-teal border-t-transparent rounded-full animate-spin mx-auto" />
                  <p className="mt-2 text-gray-600">Linking your account...</p>
                </div>
              ) : (
                <>
                  <p className="text-sm text-gray-600 text-center mb-4">
                    Signed in as <strong>{user?.email}</strong>
                  </p>
                  <button
                    onClick={handleAcceptInvitation}
                    disabled={accepting}
                    className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-brand-teal hover:bg-brand-teal/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-teal disabled:opacity-50"
                  >
                    Accept Invitation
                  </button>
                </>
              )}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};

export default AcceptInvite;
