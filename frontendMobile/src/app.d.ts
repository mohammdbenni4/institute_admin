// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
	namespace App {
		// interface Error {}
		// interface Locals {}
		// interface PageData {}
		// interface PageState {}
		// interface Platform {}
	}

	/** package.json's `version`, baked in at build time — see vite.config.ts.
	 *  Must be declared inside `declare global`; this file is a module (it has an
	 *  `export`), so a top-level `declare const` would be scoped to the module only. */
	const __APP_VERSION__: string;
}

export {};
