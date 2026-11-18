# Stage 1: Build the production Vite bundle
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci || npm install

COPY . ./
RUN npm run build

# Stage 2: Serve using high-performance lightweight Nginx
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html

# Provide standard SPA fallback configuration
RUN echo 'server { \
    listen 80; \
    server_name localhost; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html index.htm; \
        try_files $uri $uri/ /index.html; \
    } \
    location /v1/ { \
        proxy_pass http://api:8000; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
