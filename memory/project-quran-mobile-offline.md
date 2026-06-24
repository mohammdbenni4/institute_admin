---
name: project-quran-mobile-offline
description: "Quran teacher mobile — offline-first (Dexie + outbox) + Capacitor APK packaging, as of 2026-06-24"
metadata: 
  node_type: memory
  type: project
  originSessionId: e0748365-d297-4bf6-a0c0-c35dc29b6cc7
---

The teacher mobile app (`frontendMobile/`, see [[project-quran-overview]]) was made **offline-first and APK-packagable** on 2026-06-24.

**Packaging (Capacitor):** dual build. Default `vite build` keeps adapter-auto (web/VPS). `npm run build:app` (= `BUILD_TARGET=app vite build --mode app`) uses **@sveltejs/adapter-static** SPA (`fallback: index.html`, ssr already off) → `build/`, which Capacitor bundles. `capacitor.config.ts` appId `cloud.sarhalquran.teacher`, `webDir: 'build'`. Scripts: `cap:sync`, `cap:android`. The APK's API URL is **baked** via `.env.app` → `VITE_API_BASE_URL` (a static SPA has no server, so `$env/dynamic/public` is empty on device); `client.ts` falls back dyn-env → `import.meta.env.VITE_API_BASE_URL` → localhost.
- **Caveat:** env has Node 20, but Capacitor **8 CLI needs Node 22** → pinned the whole `@capacitor/*` toolchain to **v7**. If upgrading, bump Node first.
- **Not done here:** `npx cap add android` (generates `android/`, gitignored) needs Android Studio/JDK/SDK — run on a dev machine, then `npm run cap:android`. App icon/splash + keystore signing also pending.

**Offline layer (`src/lib/offline/`, hand-rolled Dexie + outbox, last-write-wins):**
- `db.ts` — Dexie `teacher-offline`: tables halaqahs/students/records/problems/meta. `records` keyed by `id` with unique compound `&[student_id+record_date]` (mirrors server UNIQUE(student,date)); `CachedRecord` adds `dirty:0|1`, `localOnly:0|1`, `problem_ids?`. `clearOfflineData()` wipes on logout (PII).
- `repo.ts` — the **only** data API the UI uses (pages no longer call `$lib/api` directly). Reads = **network-first, cache fallback**; writes (`upsertDailyRecord`, `setAttendance`) update the local mirror + optimistic scores (reuses `computeScores`) + mark dirty + `void syncNow()`.
- `sync.ts` — `pushDirty()` drains dirty records (update by id, or find-by-natural-key→patch/post for `localOnly`), replaces local with server truth. `syncNow()` no-op offline/while syncing.
- `net.svelte.ts` — `net.online` rune via Capacitor Network (native) / browser online events (web) + `onReconnect`.
- `notify.ts` — Capacitor LocalNotifications (native only). `index.ts` `initOffline()` (called in `+layout`): on reconnect with pending>0 → OS notification (teacher taps → sync); does **not** auto-sync.
- UI: `UnsyncedBanner.svelte` (reactive "N تغييرات غير مرفوعة — رفع الآن"), offline-tolerant auth guard (`loadCurrentUser` keeps session from cached profile on network error; only logs out on real ApiError 401).

**Known v1 limits:** background sync only while app is open/foreground (Android WebView limitation; `@capacitor/background-runner` deferred). No idempotent natural-key upsert endpoint on the backend yet — sync does list→patch/post instead (works, chattier). Encryption-at-rest deferred (relies on device + clear-on-logout). Verified via check/lint/both builds; **not** run on a real device yet.

**Release APK built ON the VPS (2026-06-24)** ([[reference-quran-deploy]]): installed JDK 21 + Android SDK at `/root/Android/Sdk` (platform-35, build-tools 35). Built in an isolated `git worktree` at **`/root/apk-build`** (detached `origin/main`, leaves the live checkout untouched): `npm install && npm run build:app && npx cap add android` (android/ is gitignored, regenerated each time), then `./gradlew assembleRelease`, then sign with **zipalign + apksigner** (Gradle has no signingConfig → produces `app-release-unsigned.apk`).
- **Release keystore: `/root/keystores/sarh-quran-release.jks`**, alias `sarhquran`, storepass=keypass `SarhQuranTeacher2026`, validity 10000d. **Back it up — losing it blocks future Play-Store updates.** appId `cloud.sarhalquran.teacher`, minSdk 23, targetSdk 35, signed v1+v2+v3.
- **Distribution:** signed APK copied into BOTH apps' `build/client/sarh-quran-teacher.apk` + `pm2 restart` → downloadable at **`https://srv1013493.hstgr.cloud/sarh-quran-teacher.apk`** (admin/443) and `:8080/...` (mobile). API URL is baked at build via `.env.app` (`VITE_API_BASE_URL=https://srv1013493.hstgr.cloud/api/v1`), confirmed in the bundle. (These copies are wiped on the next frontend rebuild — re-copy after redeploys.)
- Still **debug-ish for Play Store**: it's a self-signed release; app icon/splash are Capacitor defaults.
- **CORS gotcha (cost a debugging round):** the APK's WebView origin is **`https://localhost`** (Capacitor default `androidScheme: https`), NOT a srv… origin. The backend `CORS_ORIGINS` (in `backend/.env`, read by pydantic settings → `CORSMiddleware`) must include `https://localhost` (+ `capacitor://localhost`, `http://localhost`) or login silently fails in the app while the web app works. Fixed 2026-06-24 (added them, `systemctl restart institute_api.service`). Symptom was "app not responding" on login; the baked API URL was already correct. This is **server-side** — no APK rebuild needed to fix CORS.
