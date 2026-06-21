// Reactive authentication state + actions. The single source of truth for the
// signed-in super admin. Mutating `auth.*` updates every consumer.

import { api, tokens } from './client';
import type { TokenResponse, User } from './types';

export const auth = $state<{ user: User | null; loaded: boolean }>({
	user: null,
	loaded: false
});

export const isSuperAdmin = (user: User | null): boolean => user?.role === 'super_admin';

/** Authenticate and load the profile. Throws if the API rejects the request. */
export async function login(email: string, password: string): Promise<User> {
	const pair = await api.post<TokenResponse>('/auth/login', { email, password });
	tokens.set(pair.access_token, pair.refresh_token);
	const user = await api.get<User>('/auth/me');
	auth.user = user;
	auth.loaded = true;
	return user;
}

/** Resolve the current user from a stored token (called once by the guard). */
export async function loadCurrentUser(): Promise<User | null> {
	if (!tokens.access) {
		auth.user = null;
		auth.loaded = true;
		return null;
	}
	try {
		auth.user = await api.get<User>('/auth/me');
	} catch {
		tokens.clear();
		auth.user = null;
	}
	auth.loaded = true;
	return auth.user;
}

export function logout(): void {
	tokens.clear();
	auth.user = null;
}
