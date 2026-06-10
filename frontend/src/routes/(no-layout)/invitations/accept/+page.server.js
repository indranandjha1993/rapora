/**
 * Organization invitation accept page.
 *
 * load(): look up the invitation by token and show who/what it's for.
 * default action: accept it — the backend creates a passwordless account if
 * needed, attaches the org membership, and returns JWTs which we store in
 * httpOnly cookies (same as the magic-link / Google flows), then redirect in.
 */

import axios from 'axios';
import { redirect, fail } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';
import { env as publicEnv } from '$env/dynamic/public';
import { serverApiOrigin } from '$lib/server/api-origin.js';

/** @type {import('@sveltejs/kit').ServerLoad} */
export async function load({ url }) {
  const token = url.searchParams.get('token');
  if (!token) {
    return { error: 'Missing invitation token.' };
  }
  try {
    const apiUrl = serverApiOrigin;
    const res = await axios.get(`${apiUrl}/api/invitations/accept/`, {
      params: { token },
      timeout: 10000
    });
    return { invite: res.data, token };
  } catch (error) {
    const msg =
      error.response?.data?.errors ||
      error.response?.data?.error ||
      'This invitation is invalid or has expired.';
    return { error: msg };
  }
}

/** @type {import('@sveltejs/kit').Actions} */
export const actions = {
  default: async ({ request, cookies }) => {
    const formData = await request.formData();
    const token = formData.get('token')?.toString();
    if (!token) return fail(400, { error: 'Missing invitation token.' });

    try {
      const apiUrl = serverApiOrigin;
      const res = await axios.post(
        `${apiUrl}/api/invitations/accept/`,
        { token },
        { headers: { 'Content-Type': 'application/json' }, timeout: 10000 }
      );

      const { access_token, refresh_token } = res.data;
      const secure = env.NODE_ENV === 'production';
      cookies.set('jwt_access', access_token, {
        path: '/',
        httpOnly: true,
        sameSite: 'lax',
        secure,
        maxAge: 60 * 60 * 24
      });
      cookies.set('jwt_refresh', refresh_token, {
        path: '/',
        httpOnly: true,
        sameSite: 'lax',
        secure,
        maxAge: 60 * 60 * 24 * 365
      });
    } catch (error) {
      const msg =
        error.response?.data?.errors ||
        error.response?.data?.error ||
        'Could not accept this invitation.';
      return fail(400, { error: msg });
    }

    // Joined — land in the new organization's dashboard.
    throw redirect(303, '/');
  }
};
