# Loaded by `vite build --mode app` (the Capacitor/APK build only).
# Baked into the bundle because a static SPA has no server to resolve $env/dynamic/public.
# Point this at the production API the device should reach.
VITE_API_BASE_URL=https://srv1013493.hstgr.cloud/api/v1

# Must be set here too. SvelteKit bakes `$env/dynamic/public` into a static build,
# and Vite loads plain `.env` in every mode — so a localhost value left there for
# local development would otherwise win over VITE_API_BASE_URL and ship an APK that
# talks to the developer's laptop.
PUBLIC_API_BASE_URL=https://srv1013493.hstgr.cloud/api/v1

# Demo/mock mode must be forced OFF for the same reason: a developer who left
# PUBLIC_MOCK_MODE=true in `.env` while working on the UI would otherwise ship an
# APK that serves fake students from the browser and never contacts the server.
# Both spellings are pinned — PUBLIC_ for $env/dynamic/public, VITE_ for the
# import.meta.env fallback (see src/lib/mock/config.ts).
PUBLIC_MOCK_MODE=false
VITE_MOCK_MODE=false
