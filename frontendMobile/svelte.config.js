import adapterAuto from '@sveltejs/adapter-auto';
import adapterStatic from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

// `BUILD_TARGET=app` produces a static SPA bundle for the Capacitor (Android) shell;
// the default build keeps adapter-auto for the web deployment (adapter-node on the VPS).
const buildingApp = process.env.BUILD_TARGET === 'app';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	preprocess: vitePreprocess(),
	kit: {
		adapter: buildingApp ? adapterStatic({ fallback: 'index.html', strict: false }) : adapterAuto(),
		alias: {
			$lib: 'src/lib'
		}
	}
};

export default config;
