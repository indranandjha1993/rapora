FROM node:22-slim

# Enable pnpm via corepack
RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

# Install dependencies (layer cached). pnpm-workspace.yaml carries the
# allowBuilds / onlyBuiltDependencies settings that let approved packages
# (e.g. @sentry/cli) run their build scripts — without it pnpm aborts.
COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile || pnpm install

# Build the SvelteKit app for production (adapter-node → ./build). This serves
# a single optimized bundle instead of Vite's dev module graph, which is far
# more robust behind a reverse proxy / tunnel (no HMR, no per-module requests).
COPY . .
RUN pnpm build

ENV NODE_ENV=production
ENV PORT=5173
EXPOSE 5173

# adapter-node production server. PORT / ORIGIN / *_HEADER come from the env.
CMD ["node", "build"]
