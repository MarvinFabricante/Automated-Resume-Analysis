# Build Stage
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Copy source files
COPY . .

# Build args
ARG NEXT_PUBLIC_API_URL=/api
ARG NEXT_PUBLIC_WS_URL=""
ARG VITE_API_URL=/api
ARG VITE_WS_URL=""

ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_WS_URL=$VITE_WS_URL

# Build production Next.js standalone bundle
RUN npm run build

# Production Stage: Next.js standalone + Nginx proxy
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3000
ENV HOSTNAME="127.0.0.1"

RUN apk add --no-cache nginx

# Copy Next.js standalone application and static assets
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

# Clean default Alpine nginx configurations and copy custom virtual host configuration
RUN mkdir -p /etc/nginx/http.d && rm -f /etc/nginx/http.d/*.conf /etc/nginx/conf.d/*.conf
COPY nginx.conf /etc/nginx/http.d/default.conf

EXPOSE 80

CMD ["sh", "-c", "node server.js & nginx -g 'daemon off;'"]
