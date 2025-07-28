# Multi-stage build for optimized production image
# Stage 1: Builder
FROM node:20-alpine AS builder

# Build-time environment variables from Porter
ARG VITE_API_URL
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY
ARG VITE_SITE_URL

# Set environment variables for build
ENV VITE_API_URL=$VITE_API_URL \
    VITE_SUPABASE_URL=$VITE_SUPABASE_URL \
    VITE_SUPABASE_ANON_KEY=$VITE_SUPABASE_ANON_KEY \
    VITE_SITE_URL=$VITE_SITE_URL

# Set working directory
WORKDIR /app

# Copy dependency files (leverages Docker cache)
COPY package*.json ./

# Install dependencies with exact versions
RUN npm ci

# Copy source code and configs
COPY . .

# Build production bundle
RUN npm run build

# Stage 2: Production
FROM nginx:stable-alpine AS production

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built app from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Use port 5174 to match development and avoid conflicts
EXPOSE 5174

# Health check for container monitoring
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:5174 || exit 1

# Run nginx in foreground
CMD ["nginx", "-g", "daemon off;"]