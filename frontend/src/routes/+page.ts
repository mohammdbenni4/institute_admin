import { redirect } from '@sveltejs/kit';

// The admin layout guard decides between the dashboard and the login page.
export const load = () => {
	redirect(307, '/admin');
};
