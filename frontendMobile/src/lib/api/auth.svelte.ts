// Reactive authentication state + actions for the teacher app. This app is
// teachers-only: a successful login by any other role is rejected immediately.

import { clearOfflineData, metaGet, metaSet } from '$lib/offline/db';
import { ApiError, api, tokens } from './client';
import { teachersApi } from './resources';
import type { Teacher, TokenResponse, User } from './types';

const USER_KEY = 'auth.user';
const TEACHER_KEY = 'auth.teacher';

export const auth = $state<{ user: User | null; teacher: Teacher | null; loaded: boolean }>({
	user: null,
	teacher: null,
	loaded: false
});

/** Authenticate, enforce the teacher role, and load the teacher profile. */
export async function login(email: string, password: string): Promise<Teacher> {
	const pair = await api.post<TokenResponse>('/auth/login', { email, password });
	tokens.set(pair.access_token, pair.refresh_token);

	const user = await api.get<User>('/auth/me');
	if (user.role !== 'teacher') {
		tokens.clear();
		throw new ApiError(403, 'هذا التطبيق مخصص للمعلمين فقط');
	}

	const teacher = await teachersApi.me();
	auth.user = user;
	auth.teacher = teacher;
	auth.loaded = true;
	await metaSet(USER_KEY, user);
	await metaSet(TEACHER_KEY, teacher);
	return teacher;
}

/** Resolve the current teacher from a stored token (called once by the guard). */
export async function loadCurrentUser(): Promise<Teacher | null> {
	if (!tokens.access) {
		reset();
		auth.loaded = true;
		return null;
	}
	try {
		const user = await api.get<User>('/auth/me');
		if (user.role !== 'teacher') {
			logout();
			auth.loaded = true;
			return null;
		}
		const teacher = await teachersApi.me();
		auth.user = user;
		auth.teacher = teacher;
		await metaSet(USER_KEY, user);
		await metaSet(TEACHER_KEY, teacher);
	} catch (e) {
		if (e instanceof ApiError) {
			// Token genuinely invalid/expired (refresh failed) → sign out.
			logout();
		} else {
			// Offline: keep the session alive from the cached profile, if any.
			const teacher = await metaGet<Teacher>(TEACHER_KEY);
			if (teacher) {
				auth.user = (await metaGet<User>(USER_KEY)) ?? null;
				auth.teacher = teacher;
			} else {
				reset();
			}
		}
	}
	auth.loaded = true;
	return auth.teacher;
}

export function logout(): void {
	tokens.clear();
	reset();
	void clearOfflineData(); // the cache holds student PII
}

function reset(): void {
	auth.user = null;
	auth.teacher = null;
}
