# Builder stage - Creates the production build of the React app
FROM node:20-alpine AS builder

# ----- Build-time env vars from Porter env group -----
ARG VITE_API_URL
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
ARG VITE_SITE_URL
ARG VITE_AZURE_MAPS_KEY
ARG VITE_GOOGLE_MAPS_API_KEY
ARG VITE_GOOGLE_MAP_ID

ENV \
  VITE_API_URL=$VITE_API_URL \
  VITE_SUPABASE_URL=$VITE_SUPABASE_URL \
  VITE_SUPABASE_ANON_KEY=$VITE_SUPABASE_ANON_KEY \
  VITE_SITE_URL=$VITE_SITE_URL \
  VITE_AZURE_MAPS_KEY=$VITE_AZURE_MAPS_KEY \
  VITE_GOOGLE_MAPS_API_KEY=$VITE_GOOGLE_MAPS_API_KEY \
  VITE_GOOGLE_MAP_ID=$VITE_GOOGLE_MAP_ID

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

# Create non-root user for security
RUN addgroup -g 1001 -S nginxuser && \
    adduser -S -D -H -u 1001 -h /var/cache/nginx -s /sbin/nologin -G nginxuser -g nginxuser nginxuser && \
    chown -R nginxuser:nginxuser /var/cache/nginx && \
    chown -R nginxuser:nginxuser /var/log/nginx && \
    chown -R nginxuser:nginxuser /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && \
    chown -R nginxuser:nginxuser /var/run/nginx.pid

# Copy custom nginx config for React Router support and optimizations
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the built application from the builder stage to nginx html directory
COPY --from=builder /app/dist /usr/share/nginx/html

# Set ownership of html directory
RUN chown -R nginxuser:nginxuser /usr/share/nginx/html

# Switch to non-root user
USER nginxuser

# Expose port 4173 to align with Porter container port
EXPOSE 4173

# Health check for container monitoring
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:4173 || exit 1

# Nginx runs in the foreground by default
CMD ["nginx", "-g", "daemon off;"]