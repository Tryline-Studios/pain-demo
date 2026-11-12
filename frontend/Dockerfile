# Stage 1: build the Workbench with the pinned Node and pnpm (spec 2.2, 2.3).
FROM node:24.21.0-alpine AS build
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
RUN corepack enable
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

# Stage 2: Caddy serves the build and proxies /api to the api service.
FROM caddy:2.11.6-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
EXPOSE 8080
