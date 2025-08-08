import '@testing-library/jest-dom';
import { beforeAll, afterEach, vi } from 'vitest';
import React from 'react';

// Mock fetch for API calls
vi.stubGlobal('fetch', vi.fn());

// Mock environment variables
vi.mock('../utils/supabaseClient', () => ({
  supabase: {
    auth: {
      getSession: vi.fn(() => Promise.resolve({ data: { session: null }, error: null })),
      signInWithPassword: vi.fn(() => Promise.resolve({ data: { user: null, session: null }, error: null })),
      signOut: vi.fn(() => Promise.resolve({ error: null })),
      onAuthStateChange: vi.fn(() => ({ data: { subscription: { unsubscribe: vi.fn() } } }))
    }
  }
}));

// Mock React Router
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => vi.fn(),
    useLocation: () => ({ pathname: '/dashboard' }),
    Link: ({ children, to, className, ...props }) => <a href={to} className={typeof className === 'function' ? className({ isActive: false }) : className} {...props}>{children}</a>,
    NavLink: ({ children, to, className, ...props }) => <a href={to} className={typeof className === 'function' ? className({ isActive: false }) : className} {...props}>{children}</a>
  };
});

// Clean up after each test
afterEach(() => {
  vi.clearAllMocks();
});

// Set up any global test configuration
beforeAll(() => {
  // Mock window.location for navigation tests
  Object.defineProperty(window, 'location', {
    value: {
      href: 'http://localhost:3000',
      reload: vi.fn()
    },
    writable: true
  });
});