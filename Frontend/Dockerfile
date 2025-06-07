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

# Production stage - Uses Nginx to serve the static files
FROM nginx:stable-alpine AS production

# Copy custom nginx config for React Router support and optimizations
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the built application from the builder stage to nginx html directory
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port 4173 to align with Porter container port
EXPOSE 4173

# Nginx runs in the foreground by default
CMD ["nginx", "-g", "daemon off;"]