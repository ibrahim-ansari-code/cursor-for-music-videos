import React, { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { supabase } from "../../supabaseClient";
import GoogleSignInButton from "./GoogleSignInButton";
import MicrosoftSignInButton from "./MicrosoftSignInButton";
import { motion, AnimatePresence } from "framer-motion";
import * as Sentry from "@sentry/react";
import { Eye, EyeOff } from "lucide-react";

interface PasswordRequirements {
  length: boolean;
  uppercase: boolean;
  lowercase: boolean;
  digits: boolean;
  special: boolean;
}

interface PhoneRequirements {
  length: boolean;
  digits: boolean;
}

interface FieldErrors {
  firstName?: string;
  lastName?: string;
  phone?: string;
  email?: string;
  password?: string;
  confirmPassword?: string;
}

interface TouchedFields {
  firstName: boolean;
  lastName: boolean;
  phone: boolean;
  email: boolean;
  password: boolean;
  confirmPassword: boolean;
}

const RegisterForm: React.FC = () => {
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [phone, setPhone] = useState("");
  const [_phoneRequirements, setPhoneRequirements] = useState<PhoneRequirements>({
    length: false,
    digits: false,
  });
  const [email, setEmail] = useState("");
  const [registeredEmail, setRegisteredEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordRequirements, setPasswordRequirements] = useState<PasswordRequirements>({
    length: false,
    uppercase: false,
    lowercase: false,
    digits: false,
    special: false,
  });
  const [isPasswordFocused, setIsPasswordFocused] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [registrationSuccess, setRegistrationSuccess] = useState(false);
  const [resendingEmail, setResendingEmail] = useState(false);
  const [resendSuccess, setResendSuccess] = useState(false);
  const [touched, setTouched] = useState<TouchedFields>({
    firstName: false,
    lastName: false,
    phone: false,
    email: false,
    password: false,
    confirmPassword: false,
  });
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const navigate = useNavigate();

  useEffect(() => {
    const checkSession = async () => {
      const {
        data: { session: currentSession },
      } = await supabase.auth.getSession();
      if (currentSession) {
        if (import.meta.env.MODE === 'development') {
          console.log(
            "User already logged in, redirecting to dashboard from RegisterForm"
          );
        }
        navigate("/dashboard", { replace: true });
      }
    };
    checkSession();
  }, [navigate]);

  const formatPhoneNumber = (value: string): string => {
    // Remove all non-digit characters
    const digits = value.replace(/\D/g, "");
    
    // Limit to 10 digits
    const limited = digits.slice(0, 10);
    
    // Format as (XXX) XXX-XXXX
    if (limited.length <= 3) {
      return limited;
    } else if (limited.length <= 6) {
      return `(${limited.slice(0, 3)}) ${limited.slice(3)}`;
    } else {
      return `(${limited.slice(0, 3)}) ${limited.slice(3, 6)}-${limited.slice(6)}`;
    }
  };

  const getPhoneDigits = (formattedPhone: string): string => {
    return formattedPhone.replace(/\D/g, "");
  };

  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const formatted = formatPhoneNumber(e.target.value);
    setPhone(formatted);
    
    const digits = getPhoneDigits(formatted);
    setPhoneRequirements({
      length: digits.length === 10,
      digits: /^\d*$/.test(digits),
    });
  };

  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
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

  const handleBlur = (field: keyof TouchedFields) => {
    setTouched(prev => ({ ...prev, [field]: true }));
    validateField(field);
  };

  const validateField = (field: keyof TouchedFields): boolean => {
    const errors: FieldErrors = { ...fieldErrors };
    let isValid = true;

    switch (field) {
      case 'firstName':
        if (!firstName.trim()) {
          errors.firstName = "First name is required";
          isValid = false;
        } else {
          delete errors.firstName;
        }
        break;
      case 'lastName':
        if (!lastName.trim()) {
          errors.lastName = "Last name is required";
          isValid = false;
        } else {
          delete errors.lastName;
        }
        break;
      case 'phone':
        const phoneDigits = getPhoneDigits(phone);
        if (!phoneDigits) {
          errors.phone = "Phone number is required";
          isValid = false;
        } else if (phoneDigits.length !== 10) {
          errors.phone = "Phone number must be 10 digits";
          isValid = false;
        } else if (!/^\d{10}$/.test(phoneDigits)) {
          errors.phone = "Phone number must contain only digits";
          isValid = false;
        } else {
          delete errors.phone;
        }
        break;
      case 'email':
        if (!email.trim()) {
          errors.email = "Email is required";
          isValid = false;
        } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
          errors.email = "Please enter a valid email address";
          isValid = false;
        } else {
          delete errors.email;
        }
        break;
      case 'password':
        if (!password) {
          errors.password = "Password is required";
          isValid = false;
        } else if (!Object.values(passwordRequirements).every(Boolean)) {
          errors.password = "Password does not meet all requirements";
          isValid = false;
        } else {
          delete errors.password;
        }
        break;
      case 'confirmPassword':
        if (!confirmPassword) {
          errors.confirmPassword = "Please confirm your password";
          isValid = false;
        } else if (password !== confirmPassword) {
          errors.confirmPassword = "Passwords do not match";
          isValid = false;
        } else {
          delete errors.confirmPassword;
        }
        break;
    }

    setFieldErrors(errors);
    return isValid;
  };

  const validateAllFields = (): boolean => {
    const fields: (keyof TouchedFields)[] = [
      'firstName', 
      'lastName', 
      'phone', 
      'email', 
      'password', 
      'confirmPassword'
    ];
    
    // Mark all fields as touched
    const allTouched: TouchedFields = {
      firstName: true,
      lastName: true,
      phone: true,
      email: true,
      password: true,
      confirmPassword: true,
    };
    setTouched(allTouched);

    // Validate all fields
    let allValid = true;
    fields.forEach(field => {
      const valid = validateField(field);
      if (!valid) allValid = false;
    });

    return allValid;
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    setRegistrationSuccess(false);
    setResendSuccess(false);

    // Validate all fields
    if (!validateAllFields()) {
      setError("Please fill in all required fields correctly.");
      return;
    }

    setLoading(true);

    const phoneDigits = getPhoneDigits(phone);
    const userData = {
      email,
      password,
      options: {
        data: {
          first_name: firstName,
          last_name: lastName,
          phone: phoneDigits,
          user_type: "LANDLORD",
        },
      },
    };

    try {
      const { data, error: signUpError } = await supabase.auth.signUp(userData);

      if (signUpError) {
        let errorMessage = "Registration failed. Please try again.";
        
        if (signUpError.message) {
          const errorMap: Record<string, string> = {
            "Password should be at least": "Your password is too weak. Supabase requires stronger passwords for security. Please ensure your password has at least 6 characters and includes a mix of uppercase, lowercase, numbers, and special characters.",
            "User already registered": "An account with this email already exists. Please sign in instead.",
            "Invalid email": "Please enter a valid email address.",
            "Weak password": "Your password is too weak. Please use a stronger password with a mix of character types.",
            "Password must contain": "Your password doesn't meet all security requirements. Please check the requirements below.",
            "email address invalid": "Please enter a valid email address.",
            "duplicate key value": "An account with this email already exists.",
            "Password is too weak": "Your password doesn't meet Supabase's security requirements. Please use a stronger password.",
          };
          
          const mappedError = Object.entries(errorMap).find(([key]) => 
            signUpError.message.toLowerCase().includes(key.toLowerCase())
          );
          
          errorMessage = mappedError ? mappedError[1] : signUpError.message;
          
          if (signUpError.message.toLowerCase().includes("password")) {
            setIsPasswordFocused(true);
          }
        }
        
        setError(errorMessage);
        console.error("Supabase SignUp error:", signUpError);
        
        Sentry.captureException(signUpError, {
          tags: {
            component: 'RegisterForm',
            action: 'registration',
          },
          contexts: {
            registration: {
              email: email,
              hasPhone: !!phoneDigits,
            }
          }
        });
        
        setLoading(false);
        return;
      }

      if (data.user) {
        setRegistrationSuccess(true);
        setRegisteredEmail(email);
        setFirstName("");
        setLastName("");
        setPhone("");
        setEmail("");
        setPassword("");
        setConfirmPassword("");
        setTouched({
          firstName: false,
          lastName: false,
          phone: false,
          email: false,
          password: false,
          confirmPassword: false,
        });
        setFieldErrors({});
        
        Sentry.addBreadcrumb({
          category: 'auth',
          message: 'User registration successful',
          level: 'info',
        });
      } else {
        setError("Registration failed. No user data. Please contact support.");
      }
    } catch (err) {
      console.error("Registration error:", err);
      
      let displayError = "Registration failed. Please try again.";
      
      if (err instanceof Error) {
        if (err.message.includes("fetch")) {
          displayError = "Network error. Please check your connection and try again.";
        } else {
          displayError = err.message;
        }
      }
      
      setError(displayError);
      
      Sentry.captureException(err, {
        tags: {
          component: 'RegisterForm',
          action: 'registration_error',
        },
      });
    } finally {
      setLoading(false);
    }
  };

  const handleResendVerification = async () => {
    setResendingEmail(true);
    setResendSuccess(false);
    setError("");

    if (!registeredEmail) {
      setError("Please enter the email address to resend verification.");
      setResendingEmail(false);
      return;
    }

    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/api/auth/resend-verification`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ email: registeredEmail }),
        }
      );

      if (response.ok) {
        setResendSuccess(true);
      } else {
        setError("Failed to resend verification email");
      }
    } catch (err) {
      setError("Failed to resend verification email. Please try again.");
      console.error("Resend verification error:", err);
      
      Sentry.captureException(err, {
        tags: {
          component: 'RegisterForm',
          action: 'resend_verification',
        },
      });
    } finally {
      setResendingEmail(false);
    }
  };


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
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-brand-teal hover:bg-brand-teal/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-teal disabled:opacity-50 disabled:cursor-not-allowed"
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
        <GoogleSignInButton 
          setLoading={setLoading} 
          setError={setError}
        />
        <MicrosoftSignInButton 
          setLoading={setLoading} 
          setError={setError}
        />

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
                className={`mt-1 block w-full rounded-md border ${
                  touched.firstName && fieldErrors.firstName
                    ? "border-red-300 focus:border-red-500 focus:ring-red-500"
                    : "border-gray-300 focus:border-brand-teal focus:ring-brand-teal"
                } px-3 py-2 shadow-sm focus:outline-none sm:text-sm bg-white text-gray-900`}
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                onBlur={() => handleBlur('firstName')}
              />
              {touched.firstName && fieldErrors.firstName && (
                <p className="mt-1 text-sm text-red-600">{fieldErrors.firstName}</p>
              )}
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
                className={`mt-1 block w-full rounded-md border ${
                  touched.lastName && fieldErrors.lastName
                    ? "border-red-300 focus:border-red-500 focus:ring-red-500"
                    : "border-gray-300 focus:border-brand-teal focus:ring-brand-teal"
                } px-3 py-2 shadow-sm focus:outline-none sm:text-sm bg-white text-gray-900`}
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                onBlur={() => handleBlur('lastName')}
              />
              {touched.lastName && fieldErrors.lastName && (
                <p className="mt-1 text-sm text-red-600">{fieldErrors.lastName}</p>
              )}
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
              className={`mt-1 block w-full rounded-md border ${
                touched.phone && fieldErrors.phone
                  ? "border-red-300 focus:border-red-500 focus:ring-red-500"
                  : "border-gray-300 focus:border-brand-teal focus:ring-brand-teal"
              } px-3 py-2 shadow-sm focus:outline-none sm:text-sm bg-white text-gray-900`}
              placeholder="(555) 123-4567"
              value={phone}
              onChange={handlePhoneChange}
              onBlur={() => handleBlur('phone')}
            />
            {touched.phone && fieldErrors.phone && (
              <p className="mt-1 text-sm text-red-600">{fieldErrors.phone}</p>
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
              className={`mt-1 block w-full rounded-md border ${
                touched.email && fieldErrors.email
                  ? "border-red-300 focus:border-red-500 focus:ring-red-500"
                  : "border-gray-300 focus:border-brand-teal focus:ring-brand-teal"
              } px-3 py-2 shadow-sm focus:outline-none sm:text-sm bg-white text-gray-900`}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onBlur={() => handleBlur('email')}
            />
            {touched.email && fieldErrors.email && (
              <p className="mt-1 text-sm text-red-600">{fieldErrors.email}</p>
            )}
          </div>

          <div>
            <label
              htmlFor="password"
              className="block text-sm font-medium text-gray-700"
            >
              Password
            </label>
            <div className="relative">
              <input
                id="password"
                name="password"
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                className={`mt-1 block w-full rounded-md border ${
                  touched.password && fieldErrors.password
                    ? "border-red-300 focus:border-red-500 focus:ring-red-500"
                    : "border-gray-300 focus:border-brand-teal focus:ring-brand-teal"
                } px-3 py-2 pr-10 shadow-sm focus:outline-none sm:text-sm bg-white text-gray-900`}
                value={password}
                onChange={handlePasswordChange}
                onFocus={() => setIsPasswordFocused(true)}
                onBlur={() => {
                  setIsPasswordFocused(false);
                  handleBlur('password');
                }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 flex items-center pr-3 mt-1"
                tabIndex={-1}
              >
                {showPassword ? (
                  <EyeOff className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                ) : (
                  <Eye className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                )}
              </button>
            </div>

            <AnimatePresence>
              {isPasswordFocused && (
                <motion.ul
                  key="password-requirements"
                  initial={{ opacity: 0, y: -10, height: 0 }}
                  animate={{ opacity: 1, y: 0, height: "auto" }}
                  exit={{ opacity: 0, y: -10, height: 0 }}
                  transition={{ duration: 0.3, ease: "easeInOut" }}
                  className="mt-2 space-y-1 text-sm overflow-hidden"
                >
                  <li className={passwordRequirements.length ? "text-green-600" : "text-red-600"}>
                    {passwordRequirements.length ? "✓" : "○"} At least 6 characters
                  </li>
                  <li className={passwordRequirements.uppercase ? "text-green-600" : "text-red-600"}>
                    {passwordRequirements.uppercase ? "✓" : "○"} At least one uppercase letter
                  </li>
                  <li className={passwordRequirements.lowercase ? "text-green-600" : "text-red-600"}>
                    {passwordRequirements.lowercase ? "✓" : "○"} At least one lowercase letter
                  </li>
                  <li className={passwordRequirements.digits ? "text-green-600" : "text-red-600"}>
                    {passwordRequirements.digits ? "✓" : "○"} At least one number
                  </li>
                  <li className={passwordRequirements.special ? "text-green-600" : "text-red-600"}>
                    {passwordRequirements.special ? "✓" : "○"} At least one special character (!@#$...)
                  </li>
                </motion.ul>
              )}
            </AnimatePresence>

            {touched.password && fieldErrors.password && !isPasswordFocused && (
              <p className="mt-1 text-sm text-red-600">{fieldErrors.password}</p>
            )}
          </div>

          <div>
            <label
              htmlFor="confirm-password"
              className="block text-sm font-medium text-gray-700"
            >
              Confirm Password
            </label>
            <div className="relative">
              <input
                id="confirm-password"
                name="confirmPassword"
                type={showConfirmPassword ? "text" : "password"}
                autoComplete="new-password"
                className={`mt-1 block w-full rounded-md border ${
                  touched.confirmPassword && fieldErrors.confirmPassword
                    ? "border-red-300 focus:border-red-500 focus:ring-red-500"
                    : "border-gray-300 focus:border-brand-teal focus:ring-brand-teal"
                } px-3 py-2 pr-10 shadow-sm focus:outline-none sm:text-sm bg-white text-gray-900`}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                onBlur={() => handleBlur('confirmPassword')}
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute inset-y-0 right-0 flex items-center pr-3 mt-1"
                tabIndex={-1}
              >
                {showConfirmPassword ? (
                  <EyeOff className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                ) : (
                  <Eye className="h-5 w-5 text-gray-400 hover:text-gray-600" />
                )}
              </button>
            </div>
            {touched.confirmPassword && fieldErrors.confirmPassword && (
              <p className="mt-1 text-sm text-red-600">{fieldErrors.confirmPassword}</p>
            )}
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
              disabled={loading}
              className="flex w-full justify-center rounded-md border border-transparent bg-brand-teal py-2 px-4 text-sm font-medium text-white shadow-sm hover:bg-brand-teal/90 focus:outline-none focus:ring-2 focus:ring-brand-teal focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
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

