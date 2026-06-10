FROM node:22-slim

# Enable pnpm via corepack
RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

# Install dependencies (layer cached). pnpm-workspace.yaml carries the
# allowBuilds / onlyBuiltDependencies settings that let approved packages
# (e.g. @sentry/cli) run their build scripts — without it pnpm aborts.
COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile || pnpm install

EXPOSE 5173

CMD ["pnpm", "dev", "--host", "0.0.0.0"]
