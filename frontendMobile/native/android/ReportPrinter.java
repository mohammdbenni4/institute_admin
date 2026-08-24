package cloud.sarhalquran.teacher;

import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import android.print.PageRange;
import android.print.PrintAdapterCallbacks;
import android.print.PrintAttributes;
import android.print.PrintDocumentAdapter;
import android.print.PrintManager;
import android.webkit.WebView;

import androidx.core.content.FileProvider;

import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import java.io.File;

/**
 * Printing and PDF export for the monthly student report.
 *
 * Why this exists: the report is produced by `window.print()` in the browser, but
 * Android's WebView has no implementation of it — the call silently does nothing, so
 * on the phone the export button appeared to do nothing at all. Android exposes the
 * capability through PrintManager instead, and this plugin is the bridge.
 *
 * Both methods print the *live WebView*, which means the app's existing `@media print`
 * stylesheet applies unchanged: everything but `#print-report` is hidden, and the
 * Arabic/RTL layout is rendered by the same engine as on the web. No PDF library, no
 * embedded fonts, no rasterising — the output matches the web version exactly.
 */
@CapacitorPlugin(name = "ReportPrinter")
public class ReportPrinter extends Plugin {

    private static final String DEFAULT_JOB = "report";

    /** A4 at print resolution; margins are left to the platform's default. */
    private static PrintAttributes a4() {
        return new PrintAttributes.Builder()
            .setMediaSize(PrintAttributes.MediaSize.ISO_A4)
            .setResolution(new PrintAttributes.Resolution("pdf", "pdf", 600, 600))
            .setMinMargins(PrintAttributes.Margins.NO_MARGINS)
            .build();
    }

    /**
     * Open Android's print dialog for the current page. The dialog itself offers
     * "Save as PDF" (which lands in Downloads) alongside any real printer.
     */
    @PluginMethod
    public void print(final PluginCall call) {
        final String jobName = call.getString("jobName", DEFAULT_JOB);
        getActivity().runOnUiThread(() -> {
            try {
                WebView webView = getBridge().getWebView();
                PrintManager manager =
                    (PrintManager) getContext().getSystemService(Context.PRINT_SERVICE);
                if (manager == null) {
                    call.reject("Printing is not available on this device");
                    return;
                }
                manager.print(jobName, webView.createPrintDocumentAdapter(jobName), a4());
                call.resolve();
            } catch (Exception e) {
                call.reject("Could not open the print dialog: " + e.getMessage(), e);
            }
        });
    }

    /**
     * Render the current page to a PDF in the cache directory and hand it to the system
     * share sheet (WhatsApp, mail, Files…). The file goes to `cacheDir/reports`, which
     * the app's FileProvider already exposes via its `cache-path` entry, so no manifest
     * change and no storage permission is involved.
     */
    @PluginMethod
    public void sharePdf(final PluginCall call) {
        final String jobName = call.getString("jobName", DEFAULT_JOB);
        final String fileName = safeFileName(call.getString("fileName", DEFAULT_JOB));
        final String title = call.getString("title", jobName);

        getActivity().runOnUiThread(() -> {
            ParcelFileDescriptor descriptor = null;
            try {
                File dir = new File(getContext().getCacheDir(), "reports");
                if (!dir.exists() && !dir.mkdirs()) {
                    call.reject("Could not create the reports folder");
                    return;
                }
                // One file per report name: re-exporting replaces it instead of filling
                // the cache with copies.
                final File target = new File(dir, fileName);
                if (target.exists() && !target.delete()) {
                    call.reject("Could not replace the previous report file");
                    return;
                }

                final PrintDocumentAdapter adapter =
                    getBridge().getWebView().createPrintDocumentAdapter(jobName);
                final PrintAttributes attributes = a4();
                final ParcelFileDescriptor pfd = ParcelFileDescriptor.open(
                    target,
                    ParcelFileDescriptor.MODE_CREATE | ParcelFileDescriptor.MODE_READ_WRITE
                );
                descriptor = pfd;

                adapter.onLayout(
                    null,
                    attributes,
                    null,
                    new PrintAdapterCallbacks.Layout(new PrintAdapterCallbacks.Listener() {
                        @Override
                        public void onSuccess() {
                            adapter.onWrite(
                                new PageRange[] { PageRange.ALL_PAGES },
                                pfd,
                                null,
                                new PrintAdapterCallbacks.Write(
                                    new PrintAdapterCallbacks.Listener() {
                                        @Override
                                        public void onSuccess() {
                                            closeQuietly(pfd);
                                            shareFile(call, target, title);
                                        }

                                        @Override
                                        public void onFailure(CharSequence error) {
                                            closeQuietly(pfd);
                                            call.reject("Writing the PDF failed: " + error);
                                        }
                                    }
                                )
                            );
                        }

                        @Override
                        public void onFailure(CharSequence error) {
                            closeQuietly(pfd);
                            call.reject("Laying out the PDF failed: " + error);
                        }
                    }),
                    null
                );
            } catch (Exception e) {
                closeQuietly(descriptor);
                call.reject("Could not create the PDF: " + e.getMessage(), e);
            }
        });
    }

    private void shareFile(PluginCall call, File file, String title) {
        try {
            Uri uri = FileProvider.getUriForFile(
                getContext(),
                getContext().getPackageName() + ".fileprovider",
                file
            );
            Intent send = new Intent(Intent.ACTION_SEND);
            send.setType("application/pdf");
            send.putExtra(Intent.EXTRA_STREAM, uri);
            send.putExtra(Intent.EXTRA_SUBJECT, title);
            send.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);

            Intent chooser = Intent.createChooser(send, title);
            chooser.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            chooser.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            getContext().startActivity(chooser);
            call.resolve();
        } catch (Exception e) {
            call.reject("Could not open the share sheet: " + e.getMessage(), e);
        }
    }

    private static void closeQuietly(ParcelFileDescriptor pfd) {
        if (pfd == null) return;
        try {
            pfd.close();
        } catch (Exception ignored) {
            // Nothing useful to do; the PDF has already been written or failed.
        }
    }

    /** Keep the name to something every filesystem and share target accepts. */
    private static String safeFileName(String raw) {
        String base = raw == null ? DEFAULT_JOB : raw.trim();
        base = base.replaceAll("[\\\\/:*?\"<>|\\r\\n]", "-");
        if (base.isEmpty()) base = DEFAULT_JOB;
        if (base.length() > 80) base = base.substring(0, 80);
        return base.toLowerCase().endsWith(".pdf") ? base : base + ".pdf";
    }
}
