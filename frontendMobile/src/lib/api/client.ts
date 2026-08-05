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

/** One field the server rejected, ready to be shown next to its input. */
export interface FieldError {
	field: string;
	/** Arabic name of the field, e.g. «العدد الكلي». */
	label: string;
	/** Position within a batch upload, or null for a single-object request. */
	index: number | null;
	/** Stable machine-readable reason, e.g. `int_from_float`. */
	code: string;
	/** Arabic explanation. */
	message: string;
}

/**
 * Error carrying the HTTP status and the backend's Arabic `detail` message.
 *
 * `code` and `errors` are the machine-readable half: match on `code` rather than
 * on the Arabic prose, which is free to be reworded.
 */
export class ApiError extends Error {
	readonly code: string;
	readonly errors: FieldError[];

	constructor(
		readonly status: number,
		message: string,
		readonly body?: unknown
	) {
		super(message);
		this.name = 'ApiError';
		const payload = (body ?? {}) as { code?: string; errors?: FieldError[] };
		this.code = payload.code ?? 'error';
		this.errors = Array.isArray(payload.errors) ? payload.errors : [];
	}

	/** The reason a particular input was rejected, if the server named it. */
	fieldError(field: string): FieldError | undefined {
		return this.errors.find((e) => e.field === field);
	}
}

type Method = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';

const AUTH_PATHS = ['/auth/login', '/auth/refresh'];

/** Network request timeout (ms). Without this a stalled request hangs the page on a
 * perpetual spinner; on timeout the fetch aborts and the offline cache takes over. */
const TIMEOUT_MS = 8000;

/** How long to stop attempting the network after a request times out. */
const COOLDOWN_MS = 20000;

// ---- Reachability circuit breaker ------------------------------------------------
// The OS can report "connected" on a network that cannot actually reach the server
// (weak signal, captive portal, server down). Without this, every read on a page
// paid the full timeout in turn and the app looked frozen for a minute. After one
// timeout we treat the network as down for a short window and serve the cache
// immediately; the next successful request clears it.
let coolDownUntil = 0;

/** True when a recent request timed out — callers should prefer the offline cache. */
export function networkLooksDown(): boolean {
	return Date.now() < coolDownUntil;
}

function noteFailure(): void {
	coolDownUntil = Date.now() + COOLDOWN_MS;
}

function noteSuccess(): void {
	coolDownUntil = 0;
}

/** `fetch` with an abort-based timeout. AbortError is treated as a network error upstream. */
async function fetchWithTimeout(url: string, init: Parameters<typeof fetch>[1]): Promise<Response> {
	const ctrl = new AbortController();
	const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
	try {
		const res = await fetch(url, { ...init, signal: ctrl.signal });
		noteSuccess();
		return res;
	} catch (e) {
		noteFailure();
		throw e;
	} finally {
		clearTimeout(timer);
	}
}

/** Exchange the stored refresh token for a fresh token pair. Returns success. */
async function tryRefresh(): Promise<boolean> {
	const refresh = tokens.refresh;
	if (!refresh) return false;
	const res = await fetchWithTimeout(`${BASE_URL}/auth/refresh`, {
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

	const res = await fetchWithTimeout(`${BASE_URL}${path}`, {
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

/**
 * One Arabic sentence for any failure, for direct display to a teacher.
 *
 * The API already answers in Arabic (see the backend's error handlers), but a
 * request that never reaches it fails with the browser's own English text —
 * "NetworkError when attempting to fetch resource", "The operation was aborted" —
 * which used to reach the screen verbatim. Everything funnels through here.
 */
export function errorMessage(e: unknown, fallback = 'حدث خطأ غير متوقع'): string {
	if (e instanceof ApiError) {
		if (e.status === 429) return e.message || 'محاولات كثيرة جداً، يرجى المحاولة لاحقاً';
		if (e.status === 401) return 'انتهت الجلسة، يرجى تسجيل الدخول مجدداً';
		if (e.status === 403) return 'ليس لديك صلاحية لهذا الإجراء';
		if (e.status === 404) return 'العنصر المطلوب غير موجود';
		if (e.status === 409) return e.message || 'يوجد تعارض في البيانات';
		if (e.status >= 500) return 'خطأ في الخادم، يرجى المحاولة لاحقاً';
		return e.message || fallback;
	}
	// A timeout aborts the fetch; anything else here is a transport failure.
	if (e instanceof DOMException && e.name === 'AbortError') {
		return 'انتهت مهلة الاتصال، تحقق من الإنترنت وحاول مجدداً';
	}
	if (e instanceof TypeError) return 'تعذّر الاتصال بالخادم، تحقق من الإنترنت';
	return fallback;
}
