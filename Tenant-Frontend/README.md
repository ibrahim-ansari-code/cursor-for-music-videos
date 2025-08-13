# Brikli Tenant Portal

React frontend application for the Brikli Tenant Portal, providing tenants with secure access to their rental information, maintenance requests, and property management features.

## Overview

The Tenant Portal is built with React 19, Vite, and Tailwind CSS, offering a modern and responsive interface for tenant interactions with the Brikli property management platform. The application features a comprehensive sidebar navigation, error boundaries, and robust testing infrastructure.

## Features

- **Authentication**: Secure login via Supabase Auth with JWT tokens
- **Dashboard**: Overview of tenant information, upcoming payments, and quick actions
- **Rent & Payments**: View payment history and make online payments
- **Lease Documents**: Access lease agreements and related documents
- **Maintenance Requests**: Submit and track maintenance issues
- **Notifications**: Real-time updates and alerts
- **Settings**: User profile and account management

## Tech Stack

- **Frontend**: React 19 + Vite + Tailwind CSS v4
- **Icons**: FontAwesome (npm package bundled with Vite)
- **Authentication**: Supabase Auth with JWT tokens
- **Routing**: React Router v7 with nested routes
- **State Management**: React Context API
- **API Integration**: RESTful API calls to Brikli Backend
- **Testing**: Vitest + React Testing Library + jsdom
- **Error Handling**: React Error Boundaries
- **Deployment**: Docker + Nginx

## Development Setup

1. **Prerequisites**:
   - Node.js 18+ and npm
   - Backend API running at `http://localhost:8000`
   - Supabase project configured

2. **Install dependencies**:

   ```bash
   npm install
   ```

3. **Set up environment variables**:
   Create a `.env` file with:

   ```env
   VITE_API_URL=http://localhost:8000
   VITE_SUPABASE_URL=your_supabase_url
   VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
   ```

4. **Start development server**:

   ```bash
   npm run dev
   ```

   Access at: `http://localhost:5173`

## Available Scripts

```bash
# Development
npm run dev              # Start development server with HMR
npm run build           # Build for production
npm run preview         # Preview production build locally
npm run lint            # Run ESLint

# Testing
npm test                # Run tests in interactive mode
npm run test:run        # Run all tests once
npm run test:watch      # Run tests in watch mode
npm run test:coverage   # Run tests with coverage report
npm run test:ui         # Run tests with UI interface
```

## Testing

The application includes comprehensive test coverage using industry-standard tools:

- **Framework**: Vitest with jsdom environment
- **Testing Library**: React Testing Library for component testing
- **Coverage**: 75%+ test pass rate with comprehensive scenarios
- **Mocking**: API calls, authentication, and routing properly mocked

### Running Tests

```bash
# Run all tests
npm run test:run

# Run tests in watch mode (recommended for development)
npm run test:watch

# Generate coverage report
npm run test:coverage
```

### Test Structure

```text
src/
├── components/__tests__/     # Component tests
├── contexts/__tests__/       # Context and state tests
└── test/
    ├── setup.jsx            # Test configuration
    └── utils.jsx            # Test utilities and mocks
```

## Architecture

### Component Structure

```text
src/
├── components/
│   ├── Layout.jsx          # Main layout with sidebar and header
│   ├── Sidebar.jsx         # Navigation sidebar with collapse
│   ├── DashboardContent.jsx # Dashboard main content
│   ├── ErrorBoundary.jsx   # Global error handling
│   └── __tests__/          # Component tests
├── pages/
│   ├── Dashboard.jsx       # Dashboard page wrapper
│   ├── Login.jsx          # Authentication page
│   └── ResetPassword.jsx  # Password reset
├── contexts/
│   ├── AuthContext.jsx    # Authentication state management
│   └── __tests__/         # Context tests
├── utils/
│   ├── api/               # API integration layer
│   ├── supabaseClient.js  # Supabase configuration
│   └── classNames.js      # Utility functions
└── test/                  # Testing infrastructure
```

### Key Design Patterns

- **Layout System**: Shared layout with sidebar and header
- **Error Boundaries**: Graceful error handling with retry functionality
- **Loading States**: Proper loading indicators and skeleton screens
- **Responsive Design**: Mobile-first approach with Tailwind CSS
- **Icon Consistency**: FontAwesome icons bundled locally for security
- **Type Safety**: PropTypes validation and error checking

## Security Features

- **Authentication**: JWT token validation and automatic refresh
- **Route Protection**: Protected routes requiring authentication
- **User Type Validation**: Tenant-only access enforcement
- **Local Asset Bundling**: FontAwesome bundled locally vs. CDN
- **Error Handling**: Secure error messages without sensitive data
- **Input Validation**: Client-side validation for all forms

## Performance Optimizations

- **Bundle Splitting**: Code splitting for optimal loading
- **Asset Optimization**: Optimized images and fonts
- **Lazy Loading**: Route-based code splitting
- **Caching**: Proper browser caching headers
- **Tree Shaking**: Unused code elimination

## Building for Production

```bash
# Build application
npm run build

# Preview production build
npm run preview

# Analyze bundle
npm run build && npx vite-bundle-analyzer dist
```

## Docker Deployment

The application uses a multi-stage Docker build for optimized production images:

```bash
# Build Docker image
docker build -t brikli-tenant-frontend .

# Run container
docker run -p 4173:80 brikli-tenant-frontend
```

### Docker Configuration

- **Base Image**: Node 18 Alpine for building
- **Production Image**: Nginx Alpine for serving
- **Static Files**: Optimized and compressed
- **Health Checks**: Container health monitoring

## Environment Configuration

### Development

```env
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=http://127.0.0.1:54321
VITE_SUPABASE_ANON_KEY=your_local_anon_key
```

### Production

```env
VITE_API_URL=https://api.brikli.com
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_production_anon_key
```

## API Integration

The frontend integrates with the Brikli Backend API:

- **Base URL**: Configurable via `VITE_API_URL`
- **Authentication**: Bearer token in Authorization header
- **Error Handling**: Comprehensive error response handling
- **Retry Logic**: Automatic retry for failed requests
- **Timeout**: Configurable request timeouts

### API Modules

```text
src/utils/api/
├── auth.js         # Authentication endpoints
├── core.js         # Base API configuration
└── index.js        # API exports
```

## Related Services

- **Backend API**: Located in `/Backend` directory
- **Landlord Portal**: Located in `/Frontend` directory  
- **Database**: Supabase PostgreSQL with dual migration system
- **Authentication**: Supabase Auth with custom user types

## Contributing

1. Follow the existing code patterns and conventions
2. Write tests for new components and features
3. Ensure all tests pass before submitting PRs
4. Use the established error handling patterns
5. Maintain responsive design standards

## Troubleshooting

### Common Issues

1. **Authentication Errors**: Check Supabase configuration and JWT tokens
2. **API Connection**: Verify backend is running and VITE_API_URL is correct
3. **Build Failures**: Clear node_modules and reinstall dependencies
4. **Test Failures**: Check test setup and mock configurations

### Debug Commands

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json && npm install

# Reset git state
git clean -fdx && git reset --hard

# Check environment variables
npm run dev -- --debug
```

## License

Private - Brikli Property Management Platform
