// Producing the monthly report, on the web and inside the Android app.
//
// On the web the export is simply `window.print()` over the `#print-report` container
// (see the `@media print` rules in app.css), and the browser's dialog offers
// "Save as PDF".
//
// Android's WebView has **no implementation of `window.print()`** — the call returns
// immediately and nothing happens: no dialog, no error, no file. That is why the export
// button appeared completely dead in the APK while working fine in the browser. The
// platform exposes printing through PrintManager instead, which the app's own
// `ReportPrinter` plugin bridges (native/android/ReportPrinter.java).
//
// The native path prints the live WebView, so the very same print stylesheet applies and
// the Arabic/RTL report comes out identical to the web version — no PDF library, no font
// embedding, no rasterising.

import { Capacitor, registerPlugin } from '@capacitor/core';

interface ReportPrinterPlugin {
	/** Open the system print dialog (its "Save as PDF" writes to Downloads). */
	print(options: { jobName?: string }): Promise<void>;
	/** Render to a PDF and hand it to the share sheet (WhatsApp, mail, Files…). */
	sharePdf(options: { jobName?: string; fileName?: string; title?: string }): Promise<void>;
}

const ReportPrinter = registerPlugin<ReportPrinterPlugin>('ReportPrinter');

/** True inside the Android app, false in any browser. */
export function isNativeApp(): boolean {
	return Capacitor.isNativePlatform();
}

/** Let the freshly rendered #print-report DOM flush before the print job reads it. */
function nextFrame(): Promise<void> {
	return new Promise((resolve) => setTimeout(resolve, 50));
}

/**
 * Print / save the report. Opens the browser's print dialog on the web and Android's
 * print dialog (which includes "Save as PDF") in the app.
 */
export async function printReport(jobName: string): Promise<void> {
	await nextFrame();
	if (!isNativeApp()) {
		window.print();
		return;
	}
	await ReportPrinter.print({ jobName });
}

/**
 * Share the report as a PDF file. Native only — on the web there is no share sheet to
 * hand a file to, so this falls back to the print dialog and its "Save as PDF".
 */
export async function shareReportPdf(fileName: string, title: string): Promise<void> {
	await nextFrame();
	if (!isNativeApp()) {
		window.print();
		return;
	}
	try {
		await ReportPrinter.sharePdf({ jobName: title, fileName, title });
	} catch (e) {
		// Generating the file is the more fragile of the two paths. Rather than leave the
		// teacher with a dead button, fall back to the print dialog — its "Save as PDF"
		// reaches the same result in one extra tap.
		console.warn('sharePdf failed, falling back to the print dialog', e);
		await ReportPrinter.print({ jobName: title });
	}
}

/** A filesystem- and share-safe report name, e.g. «تقرير حلقة النور 2026-08». */
export function reportFileName(halaqahName: string, from: string, to: string): string {
	const sameMonth = from.slice(0, 7) === to.slice(0, 7);
	const period = sameMonth ? from.slice(0, 7) : `${from}_${to}`;
	const name = `تقرير-${halaqahName}-${period}`;
	return `${name.replace(/[\\/:*?"<>|\s]+/g, '-')}.pdf`;
}
