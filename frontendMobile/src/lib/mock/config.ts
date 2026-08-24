// Whether the app talks to the in-browser mock backend instead of the real API.
// Toggle with PUBLIC_MOCK_MODE=true in .env (web) or VITE_MOCK_MODE=true (.env.app, static build).

import { env } from '$env/dynamic/public';

export const MOCK_MODE = (env.PUBLIC_MOCK_MODE || import.meta.env.VITE_MOCK_MODE || '') === 'true';

export const DEMO_EMAIL = 'teacher@demo.com';
export const DEMO_PASSWORD = '123456';
