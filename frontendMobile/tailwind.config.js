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
			// Dark-green + white palette, matching the admin dashboard.
			colors: {
				primary: '#27795a',
				'on-primary': '#ffffff',
				'primary-container': '#b9e8d1',
				'on-primary-container': '#00321f',
				'primary-fixed': '#b9e8d1',
				'primary-fixed-dim': '#8fd6b4',
				secondary: '#27795a',
				'on-secondary': '#ffffff',
				'secondary-container': '#b9e8d1',
				'on-secondary-container': '#00714c',
				tertiary: '#206b4c',
				'on-tertiary': '#ffffff',
				'tertiary-container': '#9fd9bc',
				'on-tertiary-container': '#00341f',
				'tertiary-fixed': '#cdeadb',
				error: '#ba1a1a',
				'on-error': '#ffffff',
				'error-container': '#ffdad6',
				'on-error-container': '#93000a',
				background: '#ffffff',
				'on-background': '#0f1f18',
				surface: '#ffffff',
				'on-surface': '#0f1f18',
				'surface-variant': '#dde7e1',
				'on-surface-variant': '#3f4f47',
				'surface-bright': '#ffffff',
				'surface-dim': '#eef3f0',
				'surface-container-lowest': '#ffffff',
				'surface-container-low': '#f4f8f6',
				'surface-container': '#eff5f1',
				'surface-container-high': '#e7f0ea',
				'surface-container-highest': '#dfeae3',
				outline: '#6f7f76',
				'outline-variant': '#c6d6cc',
				'inverse-surface': '#1f342e',
				'inverse-on-surface': '#ddf6ec',
				'inverse-primary': '#8fd6b4',
				// Dark-green brand accents for the top bar gradient, FAB and CTAs.
				brand: {
					DEFAULT: '#27795a',
					dark: '#1c5e44',
					deep: '#124230',
					tint: '#dff0e8',
					wash: '#f4faf7'
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
