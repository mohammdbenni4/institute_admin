// Thin HTTP client for the backend API: JWT storage, auth header injection,
// transparent one-shot token refresh, and typed error handling.

import { browser } from '$app/environment';
import { env } from '$env/dynamic/public';
import type { TokenResponse } from './types';

const BASE_URL = (env.PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api/v1').replace(/\/$/, '');

const ACCESS_KEY = 'ia.access_token';
const REFRESH_KEY = 'ia.refresh_token';

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

/**
 * Derive a human-readable message from an error response body. The backend
 * normally returns a string `detail` (Arabic), but FastAPI's raw validation
 * format is an array of `{ loc, msg }` entries — handle it so a 422 never
 * collapses to a bare "حدث خطأ".
 */
function extractErrorMessage(data: unknown, status: number): string {
	if (data && typeof data === 'object') {
		const body = data as { detail?: unknown; title?: unknown };
		if (typeof body.detail === 'string' && body.detail) return body.detail;
		if (Array.isArray(body.detail)) {
			const parts = body.detail
				.map((e) => (e && typeof e === 'object' ? (e as { msg?: unknown }).msg : null))
				.filter((m): m is string => typeof m === 'string' && m.length > 0);
			if (parts.length) return parts.join('؛ ');
		}
		if (typeof body.title === 'string' && body.title) return body.title;
	}
	return `فشل الطلب (${status})`;
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
		throw new ApiError(res.status, extractErrorMessage(data, res.status), data);
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
	put: <T>(path: string, body?: unknown) => request<T>('PUT', path, body),
	delete: (path: string) => request<void>('DELETE', path)
};
