import React, { useState, useContext, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { AuthContext } from "../App";
import { supabase } from "../supabaseClient"; // Import Supabase client
import GoogleSignInButton from "./GoogleSignInButton"; // Import the new component
import { motion, AnimatePresence } from "framer-motion";

const RegisterForm = () => {
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [phone, setPhone] = useState("");
  const [phoneRequirements, setPhoneRequirements] = useState({
    length: false,
    digits: false,
  });
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordRequirements, setPasswordRequirements] = useState({
    length: false,
    uppercase: false,
    lowercase: false,
    digits: false,
    special: false,
  });
  const [isPasswordFocused, setIsPasswordFocused] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [registrationSuccess, setRegistrationSuccess] = useState(false);
  const [resendingEmail, setResendingEmail] = useState(false);
  const [resendSuccess, setResendSuccess] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    // If user is already logged in, redirect to dashboard
    const checkSession = async () => {
      const {
        data: { session: currentSession },
      } = await supabase.auth.getSession();
      if (currentSession) {
        console.log(
          "User already logged in, redirecting to dashboard from RegisterForm"
        );
        navigate("/dashboard", { replace: true });
      }
    };
    checkSession();
  }, [navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    setRegistrationSuccess(false);
    setResendSuccess(false);

    const userData = {
      email,
      password,
      options: {
        data: {
          // Custom data to be stored in Supabase user_metadata
          first_name: firstName,
          last_name: lastName,
          phone: phone || null,
          user_type: "LANDLORD",
        },
      },
    };

    try {
      const { data, error } = await supabase.auth.signUp(userData);

      if (error) {
        // Handle specific Supabase error messages
        let errorMessage = "Registration failed. Please try again.";
        
        if (error.message) {
          // Common Supabase registration error messages
          const errorMap = {
            "Password should be at least": "Your password is too weak. Supabase requires stronger passwords for security. Please ensure your password has at least 6 characters and includes a mix of uppercase, lowercase, numbers, and special characters.",
            "User already registered": "An account with this email already exists. Please sign in instead.",
            "Invalid email": "Please enter a valid email address.",
            "Weak password": "Your password is too weak. Please use a stronger password with a mix of character types.",
            "Password must contain": "Your password doesn't meet all security requirements. Please check the requirements below.",
            "email address invalid": "Please enter a valid email address.",
            "duplicate key value": "An account with this email already exists.",
            "Password is too weak": "Your password doesn't meet Supabase's security requirements. Please use a stronger password.",
          };
          
          // Check if we have a mapped error message
          const mappedError = Object.entries(errorMap).find(([key]) => 
            error.message.toLowerCase().includes(key.toLowerCase())
          );
          
          errorMessage = mappedError ? mappedError[1] : error.message;
          
          // If it's a password error, keep the password field focused
          if (error.message.toLowerCase().includes("password")) {
            setIsPasswordFocused(true);
          }
        }
        
        setError(errorMessage);
        console.error("Supabase SignUp error:", error);
        setLoading(false);
        return;
      }

      if (data.user) {
        // Supabase registration successful
        // The webhook will automatically sync the user to our backend
        setRegistrationSuccess(true);
        // Clear the form
        setFirstName("");
        setLastName("");
        setPhone("");
        setEmail("");
        setPassword("");
      } else {
        // Should not happen if error is not thrown, but as a fallback
        setError("Registration failed. No user data. Please contact support.");
      }
    } catch (err) {
      // This catch is for unexpected errors during the registration process
      console.error("Registration error:", err);
      
      let displayError = "Registration failed. Please try again.";
      
      // Check if it's a network error
      if (err.message && err.message.includes("fetch")) {
        displayError = "Network error. Please check your connection and try again.";
      } else if (err.message) {
        displayError = err.message;
      }
      
      // Handle validation errors from backend
      if (err.data && err.data.detail) {
        if (Array.isArray(err.data.detail)) {
          // For RequestValidationError (FastAPI Pydantic errors)
          displayError = err.data.detail
            .map((d) => {
              const field =
                d.loc && d.loc.length > 1
                  ? d.loc[d.loc.length - 1]
                  : d.loc && d.loc.length === 1
                  ? d.loc[0]
                  : "Error";
              return `${field}: ${d.msg}`;
            })
            .join("; ");
        } else if (typeof err.data.detail === "string") {
          // For HTTPException (FastAPI general errors)
          displayError = err.data.detail;
        }
      }
      
      setError(displayError);
    } finally {
      setLoading(false);
    }
  };

  const handlePhoneChange = (e) => {
    const phone = e.target.value;
    setPhone(phone);
    setPhoneRequirements({
      length: phone.length === 10,
      digits: /^\d*$/.test(phone),
    });
  };

  const handlePasswordChange = (e) => {
    const pass = e.target.value;
    setPassword(pass);
    setPasswordRequirements({
      length: pass.length >= 6,
      uppercase: /[A-Z]/.test(pass),
      lowercase: /[a-z]/.test(pass),
      digits: /[0-9]/.test(pass),
      special: /[!@#$%^&*(),.?":{}|<>]/.test(pass),
    });
  };

  const isPhoneValid = Object.values(phoneRequirements).every(Boolean);
  const isPasswordValid = Object.values(passwordRequirements).every(Boolean);

  const handleResendVerification = async () => {
    setResendingEmail(true);
    setResendSuccess(false);
    setError(""); // Clear previous errors

    // To resend verification, Supabase needs the email of the user.
    // If the form was cleared, we need to ensure `email` state is still available or re-fetch it.
    // For now, assuming `email` state used in the form is the one we need to resend for.
    if (!email) {
      setError("Please enter the email address to resend verification.");
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
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/api/auth/resend-verification`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ email }), // Backend needs to handle this email
        }
      );

      const responseData = await response.json();
      if (response.ok) {
        setResendSuccess(true);
      } else {
        setError("Failed to resend verification email");
      }
    } catch (err) {
      setError("Failed to resend verification email. Please try again.");
      console.error("Resend verification error:", err);
    } finally {
      setResendingEmail(false);
    }
  };

  // If registration was successful, show success message instead of form
  if (registrationSuccess) {
    return (
      <div className="w-full h-full flex flex-col justify-center items-center p-6">
        <div className="text-center mb-8">
          <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 mb-4">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-6 w-6 text-green-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900">
            Account created!
          </h3>
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
            {resendingEmail ? "Sending..." : "Resend Verification Email"}
          </button>

          {resendSuccess && (
            <div className="mt-4 rounded-md bg-green-50 p-4">
              <div className="flex">
                <div className="text-sm text-green-700">
                  Verification email sent! Please check your inbox.
                </div>
              </div>
            </div>
          )}

          <div className="mt-6 text-center">
            <Link
              to="/login"
              className="font-medium text-brand-teal hover:text-brand-teal/80"
            >
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
        <GoogleSignInButton setLoading={setLoading} setError={setError} />

        <div className="relative my-4">
          <div
            className="absolute inset-0 flex items-center"
            aria-hidden="true"
          >
            <div className="w-full border-t border-gray-300" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-white text-gray-500">
              Or create an account with email
            </span>
          </div>
        </div>

        <form className="space-y-6" onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label
                htmlFor="first-name"
                className="block text-sm font-medium text-gray-700"
              >
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
              <label
                htmlFor="last-name"
                className="block text-sm font-medium text-gray-700"
              >
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
            <label
              htmlFor="phone"
              className="block text-sm font-medium text-gray-700"
            >
              Phone Number
            </label>
            <input
              id="phone"
              name="phone"
              type="tel"
              required
              className={`mt-1 block w-full rounded-md border ${
                phone && !isPhoneValid
                  ? "border-red-300 focus:border-red-500 focus:ring-red-500"
                  : "border-gray-300 focus:border-brand-teal focus:ring-brand-teal"
              } px-3 py-2 shadow-sm focus:outline-none sm:text-sm`}
              placeholder="10-digit phone number"
              value={phone}
              onChange={handlePhoneChange}
            />
            {phone && !isPhoneValid && (
              <p className="mt-1 text-sm text-red-600">
                Please enter a valid 10-digit phone number
              </p>
            )}
          </div>

          <div>
            <label
              htmlFor="email-address"
              className="block text-sm font-medium text-gray-700"
            >
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
            <label
              htmlFor="password"
              className="block text-sm font-medium text-gray-700"
            >
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
              onChange={handlePasswordChange}
              onFocus={() => setIsPasswordFocused(true)}
              onBlur={() => setIsPasswordFocused(false)}
            />

            <AnimatePresence>
              {isPasswordFocused && (
                <motion.ul
                  key="password-requirements"
                  initial={{ opacity: 0, y: -10, height: 0 }}
                  animate={{ opacity: 1, y: 0, height: "auto" }}
                  exit={{ opacity: 0, y: -10, height: 0 }}
                  transition={{ duration: 0.5, ease: "easeInOut" }}
                  style={{ overflow: "hidden", margin: 0, padding: "0.5rem 0" }}
                >
                  <li
                    style={{
                      color: passwordRequirements.length ? "green" : "red",
                    }}
                  >
                    At least 6 characters
                  </li>
                  <li
                    style={{
                      color: passwordRequirements.uppercase ? "green" : "red",
                    }}
                  >
                    At least one uppercase letter
                  </li>
                  <li
                    style={{
                      color: passwordRequirements.lowercase ? "green" : "red",
                    }}
                  >
                    At least one lowercase letter
                  </li>
                  <li
                    style={{
                      color: passwordRequirements.digits ? "green" : "red",
                    }}
                  >
                    At least one number
                  </li>
                  <li
                    style={{
                      color: passwordRequirements.special ? "green" : "red",
                    }}
                  >
                    At least one special character (!@#$...)
                  </li>
                </motion.ul>
              )}
            </AnimatePresence>
          </div>

          {error && (
            <div className="rounded-md bg-red-50 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg
                    className="h-5 w-5 text-red-400"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    aria-hidden="true"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}

          <div>
            <button
              type="submit"
              disabled={
                loading ||
                !firstName ||
                !lastName ||
                !email ||
                !isPasswordValid ||
                !isPhoneValid
              }
              className="flex w-full justify-center rounded-md border border-transparent bg-brand-teal py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-brand-teal/90 focus:outline-none focus:ring-2 focus:ring-brand-teal focus:ring-offset-2 disabled:opacity-75"
            >
              {loading ? "Creating account..." : "Create account"}
            </button>
          </div>

          <div className="text-center text-sm text-gray-600">
            Already have an account?{" "}
            <Link
              to="/login"
              className="font-medium text-brand-teal hover:text-brand-teal/80"
            >
              Sign in
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
};

export default RegisterForm;
