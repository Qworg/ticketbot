FROM node:18-alpine

WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./
RUN npm install

# Copy application code
COPY . .

# Create non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nextjs -u 1001
RUN chown -R nextjs:nodejs /app
USER nextjs

EXPOSE 3000

CMD ["npm", "run", "dev"]