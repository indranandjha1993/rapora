import { env } from '$env/dynamic/private';
import { env as publicEnv } from '$env/dynamic/public';

/**
 * Origin for SERVER-SIDE (SSR) calls to the Django API.
 *
 * Prefers the internal container URL (INTERNAL_API_URL, e.g. http://backend:8000)
 * so server-rendered pages talk to the backend directly instead of round-tripping
 * the public Cloudflare tunnel (~10x faster: ~12ms vs ~120ms per call). Falls back
 * to the public URL when INTERNAL_API_URL is unset (e.g. local `pnpm dev` with no
 * containers). The BROWSER always uses PUBLIC_DJANGO_API_URL — only server-side
 * code (in *.server.js / hooks.server.js / $lib/server) imports this.
 */
export const serverApiOrigin = env.INTERNAL_API_URL || publicEnv.PUBLIC_DJANGO_API_URL;
