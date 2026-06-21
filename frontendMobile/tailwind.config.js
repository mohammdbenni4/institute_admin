/** @type {import('tailwindcss').Config} */
export default {
	darkMode: 'class',
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			fontFamily: {
				arabic: ['"IBM Plex Sans Arabic"', 'sans-serif'],
				jakarta: ['"Plus Jakarta Sans"', 'sans-serif']
			},
			// Material 3 green palette taken from the Stitch design tokens.
			colors: {
				primary: '#006c49',
				'on-primary': '#ffffff',
				'primary-container': '#22c58b',
				'on-primary-container': '#004b32',
				'primary-fixed': '#6bfcbd',
				'primary-fixed-dim': '#49dfa2',
				secondary: '#006c49',
				'on-secondary': '#ffffff',
				'secondary-container': '#83f5bf',
				'on-secondary-container': '#00714c',
				tertiary: '#206b4c',
				'on-tertiary': '#ffffff',
				'tertiary-container': '#75bc98',
				'on-tertiary-container': '#004b32',
				'tertiary-fixed': '#a9f2cc',
				error: '#ba1a1a',
				'on-error': '#ffffff',
				'error-container': '#ffdad6',
				'on-error-container': '#93000a',
				background: '#e6fff5',
				'on-background': '#091f1a',
				surface: '#e6fff5',
				'on-surface': '#091f1a',
				'surface-variant': '#cfe8de',
				'on-surface-variant': '#3c4a42',
				'surface-bright': '#e6fff5',
				'surface-dim': '#c7dfd6',
				'surface-container-lowest': '#ffffff',
				'surface-container-low': '#e0f9ef',
				'surface-container': '#dbf3ea',
				'surface-container-high': '#d5eee4',
				'surface-container-highest': '#cfe8de',
				outline: '#6c7a71',
				'outline-variant': '#bbcabf',
				'inverse-surface': '#1f342e',
				'inverse-on-surface': '#ddf6ec',
				'inverse-primary': '#49dfa2',
				// Bright brand accents used for the top bar gradient, FAB and CTAs.
				brand: {
					DEFAULT: '#22c58b',
					dark: '#159a6b',
					deep: '#0f7a55',
					tint: '#d9fbef',
					wash: '#f2fff9'
				}
			},
			borderRadius: {
				DEFAULT: '1rem',
				lg: '2rem',
				xl: '3rem'
			},
			boxShadow: {
				stat: '0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03), inset 0 1px 0 rgba(255,255,255,0.6)',
				card: '0 20px 50px rgba(0,108,73,0.08)',
				fab: '0 8px 25px rgba(34,197,139,0.4)'
			}
		}
	},
	plugins: []
};
