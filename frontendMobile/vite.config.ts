import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import pkg from './package.json' with { type: 'json' };

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		// 5174 so the teacher mobile app can run alongside the admin frontend (5173).
		port: 5174
	},
	// Shown at the bottom of the halaqah list so a teacher can read their version out
	// during support. Baked in at build time — the browser never fetches package.json
	// (Vite's dev server refuses to serve anything outside src/).
	define: {
		__APP_VERSION__: JSON.stringify(pkg.version)
	}
});
