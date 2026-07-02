import adapter from '@sveltejs/adapter-node';
import adapterStatic from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

// `BUILD_TARGET=app` produces a static SPA bundle for the Capacitor (Android) shell;
// the default build uses adapter-node for the VPS (PM2 serves build/index.js on :3001).
const buildingApp = process.env.BUILD_TARGET === 'app';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	preprocess: vitePreprocess(),
	kit: {
		adapter: buildingApp ? adapterStatic({ fallback: 'index.html', strict: false }) : adapter(),
		alias: {
			$lib: 'src/lib'
		}
	}
};

export default config;
