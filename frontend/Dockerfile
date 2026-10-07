# MiniCommerce Angular frontend — production image.
#   Stage 1 (Node): install exact dependencies, compile the app (production config, hashed files).
#   Stage 2 (Nginx): serve only the static output. No Node, no source, no node_modules at runtime,
#   and no `ng serve` (that is a development server).

FROM node:22-alpine AS build
WORKDIR /app
# Dependencies first: this layer is reused until package*.json changes.
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Where the *browser* finds the API. Baked into the bundle at build time (see environment.ts).
ARG API_BASE_URL=http://localhost:8000/api
RUN npm run build -- --configuration production --define "MC_API_BASE_URL='${API_BASE_URL}'"

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/minicommerce/browser /usr/share/nginx/html
EXPOSE 80
