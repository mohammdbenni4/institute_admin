// Thin HTTP client for the backend API: JWT storage, auth header injection,
// transparent one-shot token refresh, and typed error handling.

import { browser } from '$app/environment';
import { env } from '$env/dynamic/public';
import type { TokenResponse } from './types';

// Web (adapter-node) resolves the API at runtime via $env/dynamic/public. The static
// APK build has no server, so it falls back to the Vite-baked VITE_API_BASE_URL (.env.app).
const BASE_URL = (
	env.PUBLIC_API_BASE_URL ||
	import.meta.env.VITE_API_BASE_URL ||
	'http://localhost:8000/api/v1'
).replace(/\/$/, '');

const ACCESS_KEY = 'ia.teacher.access_token';
const REFRESH_KEY = 'ia.teacher.refresh_token';

export const tokens = {
	get access(): string | null {
		return browser ? localStorage.getItem(ACCESS_KEY) : null;
	},
	get refresh(): string | null {
		return browser ? localStorage.getItem(REFRESH_KEY) : null;
	},
	set(access: string, refresh: string): void {
		if (!browser) return;
		localStorage.setItem(ACCESS_KEY, access);
		localStorage.setItem(REFRESH_KEY, refresh);
	},
	clear(): void {
		if (!browser) return;
		localStorage.removeItem(ACCESS_KEY);
		localStorage.removeItem(REFRESH_KEY);
	}
};

/** Error carrying the HTTP status and the backend's Arabic `detail` message. */
export class ApiError extends Error {
	constructor(
		readonly status: number,
		message: string,
		readonly body?: unknown
	) {
		super(message);
		this.name = 'ApiError';
	}
}

type Method = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';

const AUTH_PATHS = ['/auth/login', '/auth/refresh'];

/** Exchange the stored refresh token for a fresh token pair. Returns success. */
async function tryRefresh(): Promise<boolean> {
	const refresh = tokens.refresh;
	if (!refresh) return false;
	const res = await fetch(`${BASE_URL}/auth/refresh`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ refresh_token: refresh })
	});
	if (!res.ok) {
		tokens.clear();
		return false;
	}
	const data = (await res.json()) as TokenResponse;
	tokens.set(data.access_token, data.refresh_token);
	return true;
}

async function request<T>(
	method: Method,
	path: string,
	body?: unknown,
	isRetry = false
): Promise<T> {
	const headers: Record<string, string> = {};
	if (body !== undefined) headers['Content-Type'] = 'application/json';
	const access = tokens.access;
	if (access) headers['Authorization'] = `Bearer ${access}`;

	const res = await fetch(`${BASE_URL}${path}`, {
		method,
		headers,
		body: body !== undefined ? JSON.stringify(body) : undefined
	});

	// Transparently refresh once on an expired/invalid access token.
	if (res.status === 401 && !isRetry && !AUTH_PATHS.some((p) => path.startsWith(p))) {
		if (await tryRefresh()) return request<T>(method, path, body, true);
	}

	if (res.status === 204) return undefined as T;

	const data = await res.json().catch(() => null);
	if (!res.ok) {
		const detail = (data && (data.detail || data.title)) || `فشل الطلب (${res.status})`;
		throw new ApiError(res.status, typeof detail === 'string' ? detail : 'حدث خطأ', data);
	}
	return data as T;
}

/** Build a query string from defined params (skips `undefined`/`null`/`''`). */
export function qs(params?: object): string {
	if (!params) return '';
	const search = new URLSearchParams();
	for (const [key, value] of Object.entries(params)) {
		if (value !== undefined && value !== null && value !== '') search.set(key, String(value));
	}
	const out = search.toString();
	return out ? `?${out}` : '';
}

export const api = {
	get: <T>(path: string) => request<T>('GET', path),
	post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
	patch: <T>(path: string, body?: unknown) => request<T>('PATCH', path, body),
	delete: (path: string) => request<void>('DELETE', path)
};
