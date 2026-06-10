import { sentrySvelteKit } from "@sentry/sveltekit";
import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  return {
    // Allow the dev server to be reached through a reverse proxy / tunnel.
    // Set VITE_ALLOWED_HOSTS (comma-separated) e.g. when serving via Cloudflare;
    // unset = Vite defaults (localhost only).
    server: {
      allowedHosts: env.VITE_ALLOWED_HOSTS
        ? env.VITE_ALLOWED_HOSTS.split(',').map((h) => h.trim())
        : undefined,
    },
    plugins: [sentrySvelteKit({
      org: "rapora",
      project: "rapora-app",
      sourceMapsUploadOptions: {
        authToken: env.SENTRY_AUTH_TOKEN
      },
      autoUploadSourceMaps: !!env.PUBLIC_SENTRY_DSN
    }), tailwindcss(), sveltekit()],
  };
});
