<script lang="ts">
	import { onMount } from 'svelte';
	import {
		CalendarDays,
		ChevronLeft,
		ChevronRight,
		Users,
		TrendingUp,
		Search,
		X,
		CalendarCheck,
		CalendarX,
		AlertCircle,
		Clock,
		MessageCircle
	} from '@lucide/svelte';
	import {
		ApiError,
		analyticsApi,
		dailyRecordsApi,
		halaqahsApi,
		teachersApi,
		type AttendanceMatrix,
		type AttendanceMatrixStudent,
		type Halaqah,
		type Teacher
	} from '$lib/api';
	import { currentMonth, monthBounds, formatMonth } from '$lib/labels';
	import { whatsappLink } from '$lib/utils';
	import PageHeader from '$lib/components/shared/PageHeader.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Dialog from '$lib/components/ui/Dialog.svelte';

	// How many students to request at a time. The table renders exactly what the
	// server returns, so the DOM never grows past what has been asked for.
	const PAGE_SIZE = 50;

	// ─── filter state ──────────────────────────────────────────────────────────
	let month = $state(currentMonth());
	let halaqahId = $state('');
	let teacherId = $state('');
	let statusFilter = $state<'all' | 'present' | 'late' | 'absent' | 'excused'>('all');
	let selectedDay = $state<number | null>(null);
	let search = $state('');
	let sortBy = $state<'halaqah' | 'name' | 'rate-asc' | 'rate-desc'>('halaqah');

	// ─── meta data (loaded once) ───────────────────────────────────────────────
	let halaqahs = $state<Halaqah[]>([]);
	let teachers = $state<Teacher[]>([]);

	// ─── loaded data ───────────────────────────────────────────────────────────
	let loading = $state(true);
	let loadingMore = $state(false);
	let error = $state('');
	let rows = $state<AttendanceMatrixStudent[]>([]);
	let summary = $state<AttendanceMatrix | null>(null);

	const todayIso = new Date().toISOString().slice(0, 10);

	// ─── pure helpers ──────────────────────────────────────────────────────────
	function daysInMonth(m: string): number {
		const [y, mo] = m.split('-').map(Number);
		return new Date(y, mo, 0).getDate();
	}

	function isoDate(m: string, day: number): string {
		const [y, mo] = m.split('-');
		return `${y}-${mo}-${String(day).padStart(2, '0')}`;
	}

	function rateColor(rate: number): string {
		if (rate >= 80) return 'text-emerald-600 dark:text-emerald-400';
		if (rate >= 60) return 'text-amber-500 dark:text-amber-400';
		return 'text-red-500 dark:text-red-400';
	}

	function dayLabel(m: string, day: number): string {
		try {
			const d = new Date(`${isoDate(m, day)}T00:00:00`);
			return new Intl.DateTimeFormat('ar', {
				weekday: 'long',
				day: 'numeric',
				month: 'long'
			}).format(d);
		} catch {
			return String(day);
		}
	}

	/** Single-letter Arabic weekday for the compact column header. */
	function weekdayInitial(m: string, day: number): string {
		const d = new Date(`${isoDate(m, day)}T00:00:00`);
		return ['ح', 'ن', 'ث', 'ر', 'خ', 'ج', 'س'][d.getDay()] ?? '';
	}

	function isWeekend(m: string, day: number): boolean {
		const d = new Date(`${isoDate(m, day)}T00:00:00`).getDay();
		return d === 5 || d === 6; // Fri/Sat
	}

	function shiftMonth(delta: number) {
		const [y, m] = month.split('-').map(Number);
		const d = new Date(y, m - 1 + delta, 1);
		month = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
		selectedDay = null;
	}

	function statusLabel(st: string): string {
		if (st === 'P') return 'حاضر';
		if (st === 'L') return 'متأخر';
		if (st === 'E') return 'مأذون';
		if (st === 'A') return 'غائب';
		return 'لا يوجد سجل';
	}

	/** Heat-map cell colour for one packed status character. */
	function cellClass(st: string): string {
		if (st === 'P') return 'bg-emerald-500 hover:bg-emerald-600';
		// «متأخر» must not fall through to the grey "no record" colour — the student
		// was there, and drawing them as unrecorded is worse than not showing it.
		if (st === 'L') return 'bg-amber-500 hover:bg-amber-600';
		if (st === 'E') return 'bg-blue-500 hover:bg-blue-600';
		if (st === 'A') return 'bg-red-400 hover:bg-red-500';
		return 'bg-muted hover:bg-muted-foreground/20';
	}

	const days = $derived(Array.from({ length: daysInMonth(month) }, (_, i) => i + 1));

	const hasActiveFilters = $derived(
		!!(search || halaqahId || teacherId || statusFilter !== 'all' || selectedDay !== null)
	);

	const hasMore = $derived(summary ? rows.length < summary.total : false);

	function clearFilters() {
		search = '';
		halaqahId = '';
		teacherId = '';
		statusFilter = 'all';
		selectedDay = null;
	}

	// ─── data loading ──────────────────────────────────────────────────────────
	//
	// One aggregated request per filter change. The page used to fetch every daily
	// record of the month by paging `/daily-records` 200 at a time (dozens of
	// sequential round trips) and then build the matrix in the browser; the server
	// now returns one packed row per student, already filtered, sorted and paged.
	function currentQuery(offset: number) {
		const { from, to } = monthBounds(month);
		return {
			date_from: from,
			date_to: to,
			halaqah_id: halaqahId || undefined,
			teacher_id: teacherId || undefined,
			search: search.trim() || undefined,
			status: statusFilter === 'all' ? undefined : statusFilter,
			on_day: selectedDay !== null ? isoDate(month, selectedDay) : undefined,
			sort: sortBy,
			limit: PAGE_SIZE,
			offset
		};
	}

	async function loadData() {
		loading = true;
		error = '';
		try {
			const res = await analyticsApi.attendanceMatrix(currentQuery(0));
			summary = res;
			rows = res.items;
		} catch (e) {
			error = e instanceof Error ? e.message : 'تعذّر تحميل كشف الحضور';
			rows = [];
			summary = null;
		} finally {
			loading = false;
		}
	}

	async function loadMore() {
		if (loadingMore || !hasMore) return;
		loadingMore = true;
		try {
			const res = await analyticsApi.attendanceMatrix(currentQuery(rows.length));
			summary = res;
			rows = [...rows, ...res.items];
		} catch (e) {
			error = e instanceof Error ? e.message : 'تعذّر تحميل المزيد';
		} finally {
			loadingMore = false;
		}
	}

	onMount(async () => {
		const [h, t] = await Promise.all([
			halaqahsApi.list({ limit: 200 }),
			teachersApi.list({ limit: 200 })
		]);
		halaqahs = h.items;
		teachers = t.items;
	});

	// ─── Recording attendance from the admin panel ────────────────────────────
	//
	// The administration needs to grant «أذن» itself, with the reason on record. A
	// cell click opens this editor. It PATCHes the existing record rather than
	// upserting it, so the day's recitation/points are never overwritten.
	type EditState = {
		student: AttendanceMatrixStudent;
		day: number;
		date: string;
		status: 'present' | 'late' | 'excused' | 'absent';
		reason: string;
	};
	let editing = $state<EditState | null>(null);
	let editSaving = $state(false);
	let editError = $state('');

	const CHAR_TO_STATUS: Record<string, EditState['status']> = {
		P: 'present',
		L: 'late',
		E: 'excused',
		A: 'absent'
	};

	async function openCell(row: AttendanceMatrixStudent, day: number) {
		const iso = isoDate(month, day);
		const ch = row.days[day - 1] ?? '.';
		editError = '';
		editing = {
			student: row,
			day,
			date: iso,
			status: CHAR_TO_STATUS[ch] ?? 'present',
			reason: ''
		};
		// Pull the stored reason so editing an existing إذن does not silently blank it.
		try {
			const res = await dailyRecordsApi.list({
				student_id: row.student_id,
				record_date: iso,
				limit: 1
			});
			const rec = res.items[0];
			if (rec && editing) editing.reason = rec.excuse_reason ?? '';
		} catch {
			/* the editor still works without it */
		}
	}

	async function saveCell() {
		if (!editing || editSaving) return;
		const { student, date, status, reason } = editing;
		if (status === 'excused' && !reason.trim()) {
			editError = 'سبب الإذن مطلوب';
			return;
		}
		if (!student.halaqah_id) {
			editError = 'الطالب غير مسجَّل في حلقة.';
			return;
		}
		editSaving = true;
		editError = '';
		const fields = {
			present: status === 'present' || status === 'late',
			excused: status === 'excused',
			late: status === 'late',
			excuse_reason: status === 'excused' ? reason.trim() : null
		};
		try {
			const res = await dailyRecordsApi.list({
				student_id: student.student_id,
				record_date: date,
				limit: 1
			});
			const existing = res.items[0];
			if (existing) {
				// PATCH keeps the day's recitation, rating and points intact.
				await dailyRecordsApi.update(existing.id, fields);
			} else {
				if (!student.teacher_id) {
					editError = 'لا يمكن إنشاء سجل: الحلقة بلا معلم.';
					return;
				}
				await dailyRecordsApi.create({
					student_id: student.student_id,
					teacher_id: student.teacher_id,
					halaqah_id: student.halaqah_id,
					record_date: date,
					...fields
				});
			}
			editing = null;
			await loadData();
		} catch (e) {
			editError = e instanceof ApiError ? e.message : 'تعذّر حفظ الحضور.';
		} finally {
			editSaving = false;
		}
	}

	// Refetch whenever a filter changes. `search` is debounced so typing a name does
	// not fire a request per keystroke.
	let searchDebounced = $state('');
	let searchTimer: ReturnType<typeof setTimeout>;
	$effect(() => {
		const value = search;
		clearTimeout(searchTimer);
		searchTimer = setTimeout(() => (searchDebounced = value), 300);
	});

	$effect(() => {
		// Touch every input so the effect re-runs when any of them changes.
		void [month, halaqahId, teacherId, statusFilter, selectedDay, sortBy, searchDebounced];
		void loadData();
	});
</script>

<div class="space-y-5 p-4 md:p-6 lg:p-8" dir="rtl">
	<!-- ─── Header + month nav ─── -->
	<div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
		<PageHeader
			title="كشف الحضور والغياب"
			subtitle="خريطة حرارية شهرية لحضور جميع الطلاب عبر الحلقات"
		/>

		<div
			class="flex items-center gap-1 self-start rounded-xl border border-border bg-card px-2 py-1.5 shadow-sm"
		>
			<button
				onclick={() => shiftMonth(-1)}
				class="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
				title="الشهر السابق"
			>
				<ChevronRight class="h-4 w-4" />
			</button>
			<input
				type="month"
				bind:value={month}
				onchange={() => (selectedDay = null)}
				class="rounded-md bg-transparent px-2 py-0.5 text-sm font-semibold text-foreground focus:outline-none"
			/>
			<button
				onclick={() => shiftMonth(1)}
				disabled={month >= currentMonth()}
				class="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-30"
				title="الشهر القادم"
			>
				<ChevronLeft class="h-4 w-4" />
			</button>
		</div>
	</div>

	<!-- ─── Sticky filter bar ─── -->
	<div class="sticky top-14 z-30 rounded-2xl border border-border bg-card p-3 shadow-md">
		<div class="flex flex-wrap items-center gap-2">
			<div class="relative min-w-[160px] flex-1">
				<Search
					class="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground"
				/>
				<input
					type="search"
					bind:value={search}
					placeholder="بحث باسم الطالب..."
					class="h-8 w-full rounded-lg border border-input bg-background pl-3 pr-8 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
				/>
			</div>

			<select
				bind:value={halaqahId}
				onchange={() => (selectedDay = null)}
				class="h-8 rounded-lg border border-input bg-background px-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
			>
				<option value="">كل الحلقات</option>
				{#each halaqahs as h (h.id)}
					<option value={h.id}>{h.name}</option>
				{/each}
			</select>

			<select
				bind:value={teacherId}
				class="h-8 rounded-lg border border-input bg-background px-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
			>
				<option value="">كل المعلمين</option>
				{#each teachers as t (t.id)}
					<option value={t.id}>{t.full_name}</option>
				{/each}
			</select>

			<div class="flex items-center gap-0.5 rounded-lg bg-muted p-0.5">
				{#each [{ key: 'all', label: 'الكل', dot: '' }, { key: 'present', label: 'حاضر', dot: 'bg-emerald-500' }, { key: 'late', label: 'متأخر', dot: 'bg-amber-500' }, { key: 'absent', label: 'غائب', dot: 'bg-red-500' }, { key: 'excused', label: 'مأذون', dot: 'bg-blue-500' }] as tab (tab.key)}
					<button
						onclick={() => (statusFilter = tab.key as typeof statusFilter)}
						class={'flex h-7 items-center gap-1.5 rounded-md px-2.5 text-xs font-medium transition ' +
							(statusFilter === tab.key
								? 'bg-card text-foreground shadow-sm'
								: 'text-muted-foreground hover:text-foreground')}
					>
						{#if tab.dot}<span class={'h-1.5 w-1.5 flex-shrink-0 rounded-full ' + tab.dot}
							></span>{/if}
						{tab.label}
					</button>
				{/each}
			</div>

			<select
				bind:value={sortBy}
				class="h-8 rounded-lg border border-input bg-background px-2 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
			>
				<option value="halaqah">ترتيب: الحلقة</option>
				<option value="name">ترتيب: الاسم</option>
				<option value="rate-desc">أعلى حضوراً</option>
				<option value="rate-asc">أقل حضوراً</option>
			</select>

			{#if selectedDay !== null}
				<div
					class="flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary"
				>
					<CalendarDays class="h-3.5 w-3.5" />
					{dayLabel(month, selectedDay)}
					<button
						onclick={() => (selectedDay = null)}
						class="rounded-full text-primary/60 hover:text-destructive"
						title="إلغاء تحديد اليوم"
					>
						<X class="h-3 w-3" />
					</button>
				</div>
			{/if}

			{#if hasActiveFilters}
				<button
					onclick={clearFilters}
					class="h-8 rounded-lg border border-border px-3 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
				>
					مسح الفلاتر
				</button>
			{/if}
		</div>
	</div>

	{#if error}
		<p class="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
	{/if}

	<!-- ─── Summary cards (server-computed over the whole filtered set) ─── -->
	{#if summary}
		{@const s = summary}
		<div class="grid grid-cols-2 gap-3 sm:grid-cols-5">
			<div class="flex flex-col gap-1.5 rounded-xl border border-border bg-card p-4 shadow-sm">
				<div class="flex items-center gap-2 text-xs text-muted-foreground">
					<Users class="h-4 w-4" />إجمالي الطلاب
				</div>
				<p class="text-2xl font-bold text-foreground">{s.students}</p>
				<p class="text-[10px] text-muted-foreground">{formatMonth(month)}</p>
			</div>
			<div class="flex flex-col gap-1.5 rounded-xl border border-border bg-card p-4 shadow-sm">
				<div class="flex items-center gap-2 text-xs text-muted-foreground">
					<TrendingUp class="h-4 w-4" />معدل الحضور
				</div>
				<p class={'text-2xl font-bold ' + rateColor(s.average_rate)}>{s.average_rate}%</p>
				<p class="text-[10px] text-muted-foreground">
					{selectedDay !== null ? dayLabel(month, selectedDay) : 'متوسط الشهر'}
				</p>
			</div>
			<div class="flex flex-col gap-1.5 rounded-xl border border-border bg-card p-4 shadow-sm">
				<div class="flex items-center gap-2 text-xs text-muted-foreground">
					<CalendarCheck class="h-4 w-4 text-emerald-500" />إجمالي الحضور
				</div>
				<p class="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{s.total_present}</p>
				<p class="text-[10px] text-muted-foreground">
					{selectedDay !== null ? 'طالب حاضر' : 'يوم-طالب'}
				</p>
			</div>
			<div class="flex flex-col gap-1.5 rounded-xl border border-border bg-card p-4 shadow-sm">
				<div class="flex items-center gap-2 text-xs text-muted-foreground">
					<Clock class="h-4 w-4 text-amber-500" />إجمالي التأخير
				</div>
				<p class="text-2xl font-bold text-amber-600 dark:text-amber-400">{s.total_late}</p>
				<p class="text-[10px] text-muted-foreground">يوم-طالب</p>
			</div>
			<div class="flex flex-col gap-1.5 rounded-xl border border-border bg-card p-4 shadow-sm">
				<div class="flex items-center gap-2 text-xs text-muted-foreground">
					<CalendarX class="h-4 w-4 text-red-500" />إجمالي الغياب
				</div>
				<p class="text-2xl font-bold text-red-600 dark:text-red-400">{s.total_absent}</p>
				<p class="text-[10px] text-muted-foreground">
					{selectedDay !== null ? 'طالب غائب' : 'يوم-طالب'}
				</p>
			</div>
		</div>
	{/if}

	<!-- ─── Legend ─── -->
	<div
		class="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border bg-card px-4 py-2.5 shadow-sm"
	>
		<span class="text-xs font-semibold text-muted-foreground"
			>انقر على رقم اليوم لتصفية حالته · انقر على أي خانة لتسجيل الحضور أو منح إذن</span
		>
		<div class="flex items-center gap-3 text-[11px] text-muted-foreground">
			<span class="flex items-center gap-1.5"
				><span class="h-3 w-3 rounded-sm bg-emerald-500"></span>حاضر</span
			>
			<span class="flex items-center gap-1.5"
				><span class="h-3 w-3 rounded-sm bg-amber-500"></span>متأخر</span
			>
			<span class="flex items-center gap-1.5"
				><span class="h-3 w-3 rounded-sm bg-red-400"></span>غائب</span
			>
			<span class="flex items-center gap-1.5"
				><span class="h-3 w-3 rounded-sm bg-blue-500"></span>أذن</span
			>
			<span class="flex items-center gap-1.5"
				><span class="h-3 w-3 rounded-sm border border-border bg-muted"></span>لا سجل</span
			>
		</div>
	</div>

	<!-- ─── Loading skeleton ─── -->
	{#if loading}
		<div class="space-y-2 rounded-2xl border border-border bg-card p-4">
			{#each Array(10) as _, i (i)}
				<div class="flex items-center gap-3">
					<div class="h-4 w-24 animate-pulse rounded bg-muted"></div>
					<div class="h-4 w-32 animate-pulse rounded bg-muted"></div>
					<div class="flex flex-1 gap-0.5">
						{#each Array(28) as _, j (j)}
							<div class="h-6 w-6 animate-pulse rounded-sm bg-muted"></div>
						{/each}
					</div>
				</div>
			{/each}
		</div>

		<!-- ─── Empty state ─── -->
	{:else if rows.length === 0}
		<div
			class="flex flex-col items-center gap-4 rounded-2xl border border-dashed border-border py-16 text-center"
		>
			<AlertCircle class="h-10 w-10 text-muted-foreground/30" />
			<div>
				<p class="font-semibold text-foreground">لا توجد نتائج</p>
				<p class="mt-1 text-sm text-muted-foreground">
					{hasActiveFilters
						? 'جرّب تعديل الفلاتر للحصول على نتائج'
						: 'لا توجد سجلات حضور لهذا الشهر بعد'}
				</p>
			</div>
			{#if hasActiveFilters}
				<button
					onclick={clearFilters}
					class="rounded-lg border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-muted"
					>مسح جميع الفلاتر</button
				>
			{/if}
		</div>

		<!-- ─── Heatmap table ─── -->
	{:else}
		<div
			class="overflow-auto rounded-2xl border border-border bg-card shadow-sm"
			style="max-height: 72vh;"
		>
			<table class="border-separate border-spacing-0 text-sm">
				<thead>
					<tr>
						<!-- Sticky headers deliberately use an opaque background: `backdrop-blur`
						     on dozens of stuck cells is a heavy per-frame composite and was a
						     large part of the scroll jank on this page. -->
						<th
							class="sticky right-0 top-0 z-40 w-28 border-b border-l border-border bg-card px-3 py-2 text-right text-xs font-bold text-muted-foreground"
						>
							الحلقة
						</th>
						<th
							class="sticky right-28 top-0 z-40 w-28 border-b border-l border-border bg-card px-3 py-2 text-right text-xs font-bold text-muted-foreground"
						>
							المعلم
						</th>
						<th
							class="sticky right-56 top-0 z-40 w-36 border-b border-l border-border bg-card px-3 py-2 text-right text-xs font-bold text-muted-foreground"
						>
							الطالب
						</th>
						<!-- day headers -->
						{#each days as day (day)}
							{@const weekend = isWeekend(month, day)}
							{@const isToday = isoDate(month, day) === todayIso}
							<th
								class={'sticky top-0 z-20 border-b border-border px-0 py-1 text-center ' +
									(selectedDay === day ? 'bg-primary/15' : weekend ? 'bg-muted' : 'bg-card')}
							>
								<button
									onclick={() => (selectedDay = selectedDay === day ? null : day)}
									title={dayLabel(month, day)}
									class={'mx-auto flex h-9 w-7 flex-col items-center justify-center gap-0 rounded-md transition hover:bg-primary/20 ' +
										(selectedDay === day ? 'text-primary' : 'text-muted-foreground')}
								>
									<span class="text-[8px] leading-none opacity-60"
										>{weekdayInitial(month, day)}</span
									>
									<span
										class={'text-[11px] font-bold leading-tight ' +
											(isToday
												? 'flex h-4 w-4 items-center justify-center rounded-full bg-primary text-primary-foreground'
												: '')}>{day}</span
									>
								</button>
							</th>
						{/each}
						<th
							class="sticky left-0 top-0 z-40 w-16 border-b border-r border-border bg-card px-2 py-2 text-center text-xs font-bold text-muted-foreground"
						>
							تواصل
						</th>
					</tr>
				</thead>
				<tbody>
					{#each rows as row, i (row.student_id)}
						{@const wa = whatsappLink(
							row.father_number,
							`السلام عليكم، بخصوص الطالب ${row.student_name} — ${formatMonth(month)}: حضر ${row.present} من ${row.total} يوم مُسجَّل (غياب: ${row.absent}، إذن: ${row.excused}).`
						)}
						{@const newHalaqah = i === 0 || rows[i - 1].halaqah_id !== row.halaqah_id}
						<!-- `content-visibility` lets the browser skip layout and paint for rows
						     scrolled out of view — windowing without the bookkeeping of a virtual
						     list, which sticky columns make awkward. -->
						<tr class="group" style="content-visibility: auto; contain-intrinsic-size: 0 33px;">
							<td
								class={'sticky right-0 z-10 w-28 border-b border-l border-border bg-card px-3 py-2 align-middle group-hover:bg-muted/40 ' +
									(sortBy === 'halaqah' && !newHalaqah ? 'text-transparent' : '')}
							>
								{#if sortBy !== 'halaqah' || newHalaqah}
									{#if row.halaqah_id}
										<a
											href={`/admin/halaqahs/${row.halaqah_id}`}
											class="flex items-center gap-1 truncate text-xs font-semibold text-primary hover:underline"
											title={row.halaqah_name ?? ''}
										>
											<span class="truncate">{row.halaqah_name}</span>
										</a>
									{:else}
										<span class="truncate text-xs text-muted-foreground">بدون حلقة</span>
									{/if}
								{/if}
							</td>
							<td
								class={'sticky right-28 z-10 w-28 border-b border-l border-border bg-card px-3 py-2 align-middle group-hover:bg-muted/40 ' +
									(sortBy === 'halaqah' && !newHalaqah ? 'text-transparent' : '')}
							>
								{#if sortBy !== 'halaqah' || newHalaqah}
									{#if row.teacher_id}
										<!-- A halaqah can have several teachers. The link points at the
										     responsible one (the column is too narrow for several links),
										     while the text and tooltip name everyone who teaches it. -->
										<a
											href={`/admin/teachers/${row.teacher_id}`}
											class="block truncate text-xs font-medium text-primary hover:underline"
											title={row.teacher_names ?? row.teacher_name ?? ''}
										>
											{row.teacher_names ?? row.teacher_name}
										</a>
									{:else}
										<span class="truncate text-xs text-muted-foreground">—</span>
									{/if}
								{/if}
							</td>
							<td
								class="sticky right-56 z-10 w-36 border-b border-l border-border bg-card px-3 py-2 align-middle group-hover:bg-muted/40"
							>
								<a
									href={`/admin/students/${row.student_id}`}
									class="flex items-center justify-between gap-1.5 hover:underline"
								>
									<span
										class="truncate text-xs font-medium text-foreground"
										title={row.student_name}>{row.student_name}</span
									>
									<span class="flex shrink-0 items-center gap-1">
										{#if row.late > 0}
											<span
												class="rounded bg-amber-500/15 px-1 text-[9px] font-bold text-amber-600"
												title={`تأخّر ${row.late} مرة`}>{row.late}</span
											>
										{/if}
										<span class={'text-[10px] font-bold ' + rateColor(row.rate)}>{row.rate}%</span>
									</span>
								</a>
							</td>
							<!-- day cells, read straight from the packed status string -->
							{#each days as day (day)}
								{@const st = row.days[day - 1] ?? '.'}
								<td
									class={'border-b border-border px-0 py-0.5 text-center group-hover:bg-muted/40 ' +
										(selectedDay === day ? 'bg-primary/5' : '')}
								>
									<button
										onclick={() => openCell(row, day)}
										title={`${row.student_name} • ${dayLabel(month, day)}: ${statusLabel(st)} — اضغط للتعديل`}
										aria-label={`تعديل حضور ${row.student_name}`}
										class={'mx-auto block h-6 w-6 rounded-md transition hover:ring-2 hover:ring-primary ' +
											cellClass(st) +
											(selectedDay === day ? ' ring-2 ring-primary/40' : '')}
									></button>
								</td>
							{/each}
							<td
								class="sticky left-0 z-10 w-16 border-b border-r border-border bg-card px-2 py-2 text-center group-hover:bg-muted/40"
							>
								{#if wa}
									<a
										href={wa}
										target="_blank"
										rel="noopener noreferrer"
										class="mx-auto flex h-7 w-7 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-600 transition hover:bg-emerald-500 hover:text-white dark:text-emerald-400"
										title={`تواصل مع ولي أمر ${row.student_name}`}
									>
										<MessageCircle class="h-4 w-4" />
									</a>
								{:else}
									<span class="text-[10px] text-muted-foreground/40">—</span>
								{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>

		<div class="flex items-center justify-between gap-3 px-1">
			<p class="text-xs text-muted-foreground">
				عرض {rows.length} من {summary?.total ?? rows.length} طالب · {formatMonth(month)}
			</p>
			{#if hasMore}
				<button
					onclick={loadMore}
					disabled={loadingMore}
					class="rounded-lg border border-border px-4 py-2 text-xs font-medium text-foreground hover:bg-muted disabled:opacity-50"
				>
					{loadingMore ? 'جارٍ التحميل…' : 'تحميل المزيد'}
				</button>
			{/if}
		</div>
	{/if}
</div>

<!-- Record attendance / grant an إذن for one student-day -->
<Dialog open={editing !== null} onOpenChange={(v) => !v && (editing = null)} title="تسجيل الحضور">
	{#if editing}
		<div class="space-y-4" dir="rtl">
			<p class="text-sm text-muted-foreground">
				<span class="font-bold text-foreground">{editing.student.student_name}</span>
				— {dayLabel(month, editing.day)}
			</p>

			<div class="grid grid-cols-4 gap-2">
				{#each [{ k: 'present', l: 'حاضر', c: 'border-emerald-500 bg-emerald-500/10 text-emerald-600' }, { k: 'late', l: 'متأخر', c: 'border-amber-500 bg-amber-500/10 text-amber-600' }, { k: 'excused', l: 'أذن', c: 'border-blue-500 bg-blue-500/10 text-blue-600' }, { k: 'absent', l: 'غائب', c: 'border-red-500 bg-red-500/10 text-red-600' }] as opt (opt.k)}
					<button
						type="button"
						onclick={() => editing && (editing.status = opt.k as typeof editing.status)}
						class={'rounded-lg border px-2 py-2 text-xs font-semibold transition ' +
							(editing.status === opt.k
								? opt.c
								: 'border-border text-muted-foreground hover:bg-muted')}
					>
						{opt.l}
					</button>
				{/each}
			</div>

			{#if editing.status === 'excused'}
				<div class="space-y-1.5">
					<span class="text-sm font-medium text-foreground"
						>سبب الإذن <span class="text-destructive">*</span></span
					>
					<textarea
						bind:value={editing.reason}
						rows="2"
						placeholder="مثال: مراجعة طبية"
						class="w-full resize-none rounded-lg border border-input bg-background p-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
					></textarea>
					<p class="text-[11px] text-muted-foreground">تسجيل سبب الإذن إلزامي.</p>
				</div>
			{/if}

			{#if editError}
				<p class="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{editError}</p>
			{/if}

			<div class="flex justify-end gap-2">
				<Button variant="outline" onclick={() => (editing = null)}>إلغاء</Button>
				<Button onclick={saveCell} disabled={editSaving}>
					{editSaving ? 'جارٍ الحفظ…' : 'حفظ'}
				</Button>
			</div>
		</div>
	{/if}
</Dialog>
