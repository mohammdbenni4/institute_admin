// Reactive authentication state + actions for the teacher app. This app is
// teachers-only: a successful login by any other role is rejected immediately.

import { ApiError, api, tokens } from './client';
import { teachersApi } from './resources';
import type { Teacher, TokenResponse, User } from './types';

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
		auth.user = user;
		auth.teacher = await teachersApi.me();
	} catch {
		tokens.clear();
		reset();
	}
	auth.loaded = true;
	return auth.teacher;
}

export function logout(): void {
	tokens.clear();
	reset();
}

function reset(): void {
	auth.user = null;
	auth.teacher = null;
}
