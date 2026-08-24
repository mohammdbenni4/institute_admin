package android.print;

/**
 * Bridges to {@link PrintDocumentAdapter}'s result callbacks so a PDF can be produced
 * without going through the system print dialog.
 *
 * Why this file lives in {@code android.print}: the constructors of
 * {@code PrintDocumentAdapter.LayoutResultCallback} and {@code WriteResultCallback} are
 * package-private, so they can only be subclassed from inside that package. Declaring
 * this helper in the same package is the long-standing way every HTML-to-PDF library on
 * Android does it — it needs no reflection and no hidden APIs, only same-package access.
 *
 * The app's own printing path ({@code ReportPrinter.print}) uses the fully public
 * PrintManager API and does not depend on this class at all; only the "share as PDF"
 * path does, and it degrades to the print dialog if anything here ever stops working.
 */
public final class PrintAdapterCallbacks {

    private PrintAdapterCallbacks() {}

    /** What the caller wants to know once a stage finishes. */
    public interface Listener {
        void onSuccess();

        void onFailure(CharSequence error);
    }

    /** Receives the result of {@link PrintDocumentAdapter#onLayout}. */
    public static final class Layout extends PrintDocumentAdapter.LayoutResultCallback {
        private final Listener listener;

        public Layout(Listener listener) {
            this.listener = listener;
        }

        @Override
        public void onLayoutFinished(PrintDocumentInfo info, boolean changed) {
            listener.onSuccess();
        }

        @Override
        public void onLayoutFailed(CharSequence error) {
            listener.onFailure(error);
        }

        @Override
        public void onLayoutCancelled() {
            listener.onFailure("layout cancelled");
        }
    }

    /** Receives the result of {@link PrintDocumentAdapter#onWrite}. */
    public static final class Write extends PrintDocumentAdapter.WriteResultCallback {
        private final Listener listener;

        public Write(Listener listener) {
            this.listener = listener;
        }

        @Override
        public void onWriteFinished(PageRange[] pages) {
            if (pages == null || pages.length == 0) {
                listener.onFailure("no pages were written");
            } else {
                listener.onSuccess();
            }
        }

        @Override
        public void onWriteFailed(CharSequence error) {
            listener.onFailure(error);
        }

        @Override
        public void onWriteCancelled() {
            listener.onFailure("write cancelled");
        }
    }
}
