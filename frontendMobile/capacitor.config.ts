import type { CapacitorConfig } from '@capacitor/cli';

// Static SPA bundle (adapter-static, BUILD_TARGET=app) is emitted to `build/`.
const config: CapacitorConfig = {
	appId: 'cloud.sarhalquran.teacher',
	appName: 'صرح القرآن — المعلم',
	webDir: 'build',
	android: {
		// Allow the WebView to call the (HTTPS) production API.
		allowMixedContent: false
	},
	plugins: {
		LocalNotifications: {
			smallIcon: 'ic_stat_notify',
			iconColor: '#27795a'
		}
	}
};

export default config;
