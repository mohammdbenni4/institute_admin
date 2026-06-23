import { browser } from '$app/environment';

const STORAGE_KEY = 'quran-theme';

function createTheme() {
	let dark = $state(false);

	function init() {
		if (!browser) return;
		const stored = localStorage.getItem(STORAGE_KEY);
		dark =
			stored === 'dark' ||
			(stored === null && window.matchMedia('(prefers-color-scheme: dark)').matches);
		applyClass();
	}

	function applyClass() {
		if (!browser) return;
		document.documentElement.classList.toggle('dark', dark);
	}

	function toggle() {
		dark = !dark;
		if (browser) {
			localStorage.setItem(STORAGE_KEY, dark ? 'dark' : 'light');
			applyClass();
		}
	}

	return {
		get dark() {
			return dark;
		},
		init,
		toggle
	};
}

export const theme = createTheme();
