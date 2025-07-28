# Multi-stage build for React dashboard
FROM node:18-alpine as builder

WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./
RUN npm ci --only=production

# Copy source code and build
COPY . .
RUN npm run build

# Production stage with nginx
FROM nginx:alpine as production

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create non-root user
RUN addgroup -g 1001 -S nginx-user
RUN adduser -S nginx-user -u 1001 -G nginx-user

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

# Development stage
FROM node:18-alpine as development

WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./
RUN npm install

# Copy application code
COPY . .

# Create non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S reactuser -u 1001 -G nodejs
RUN chown -R reactuser:nodejs /app
USER reactuser

EXPOSE 3000

CMD ["npm", "run", "dev"]