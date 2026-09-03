FROM node:20-alpine@sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293 AS build
WORKDIR /app
# Lockfile-exact install (FE-10/INFRA-13): npm ci, never npm install.
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html vite.config.js ./
COPY public ./public
COPY src ./src
RUN npm run build

# NOTE on root (INFRA-10): the nginx master process stays root because
# ui/nginx.conf (owned elsewhere) listens on :80 and uses the stock
# /var/cache/nginx paths; worker processes drop to the unprivileged `nginx`
# user as usual. Follow-up: move to nginxinc/nginx-unprivileged:1.27-alpine
# once nginx.conf can change its listen port to 8080.
FROM nginx:1.27-alpine@sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
