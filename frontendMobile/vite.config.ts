import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		// 5174 so the teacher mobile app can run alongside the admin frontend (5173).
		port: 5174
	}
});
