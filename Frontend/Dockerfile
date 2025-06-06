# Builder stage - Creates the production build of the React app
FROM node:20-alpine AS builder

# Set working directory inside the container
WORKDIR /app

# Copy package.json and package-lock.json for dependency installation
# This is done separately to leverage Docker layer caching
COPY package*.json ./

# Install all dependencies (including devDependencies needed for build)
RUN npm ci

# Copy all source code and configuration files
COPY . .

# Build the React app for production (creates /dist folder)
RUN npm run build

# Production stage - Serves the built app using Vite's preview server
FROM node:20-alpine

# Set working directory for the production container
WORKDIR /app

# Copy the built application from the builder stage
COPY --from=builder /app/dist ./dist

# Copy package files to install production dependencies
COPY --from=builder /app/package*.json ./

# Install only production dependencies (no devDependencies)
RUN npm ci

# Expose port 4173 (Vite preview server default port)
EXPOSE 4173

# Start the Vite preview server to serve the built static files
CMD ["npm", "run", "preview"]