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
		MessageCircle
	} from '@lucide/svelte';
	import {
		dailyRecordsApi,
		halaqahsApi,
		studentsApi,
		teachersApi,
		type DailyRecord,
		type Halaqah,
		type Student,
		type Teacher
	} from '$lib/api';
	import { currentMonth, monthBounds, formatMonth } from '$lib/labels';
	import { whatsappLink } from '$lib/utils';
	import PageHeader from '$lib/components/shared/PageHeader.svelte';

	// ─── filter state ──────────────────────────────────────────────────────────
	let month = $state(currentMonth());
	let halaqahId = $state('');
	let teacherId = $state('');
	let statusFilter = $state<'all' | 'present' | 'absent' | 'excused'>('all');
	let selectedDay = $state<number | null>(null);
	let search = $state('');
	let sortBy = $state<'halaqah' | 'name' | 'rate-asc' | 'rate-desc'>('halaqah');

	// ─── meta data (loaded once) ───────────────────────────────────────────────
	let halaqahs = $state<Halaqah[]>([]);
	let teachers = $state<Teacher[]>([]);

	// ─── loaded data ───────────────────────────────────────────────────────────
	let loading = $state(true);
	let students = $state<Student[]>([]);
	let records = $state<DailyRecord[]>([]);

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

	function attendanceStatus(r: DailyRecord): 'present' | 'excused' | 'absent' {
		if (r.present) return 'present';
		if (r.excused) return 'excused';
		return 'absent';
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
		return st === 'present'
			? 'حاضر'
			: st === 'excused'
				? 'مأذون'
				: st === 'absent'
					? 'غائب'
					: 'لا يوجد سجل';
	}

	// ─── attendance row type ───────────────────────────────────────────────────
	type StudentRow = {
		student: Student;
		halaqahId: string;
		halaqahName: string;
		teacherId: string;
		teacherName: string;
		recordsByDate: Map<string, DailyRecord>;
		stats: { present: number; absent: number; excused: number; total: number; rate: number };
	};

	const halaqahMap = $derived.by(() => {
		const m = new Map<string, Halaqah>();
		for (const h of halaqahs) m.set(h.id, h);
		return m;
	});

	/** Halaqahs taught by the currently-selected teacher (for filtering students). */
	const teacherHalaqahIds = $derived.by(() => {
		if (!teacherId) return null;
		return new Set(halaqahs.filter((h) => h.teacher_id === teacherId).map((h) => h.id));
	});

	// ─── derived: attendance matrix ────────────────────────────────────────────
	const attendanceMatrix = $derived.by((): Map<string, StudentRow> => {
		const result = new Map<string, StudentRow>();

		for (const s of students) {
			// When filtering by teacher, only keep students of that teacher's halaqahs.
			if (teacherHalaqahIds && !teacherHalaqahIds.has(s.halaqah_id ?? '')) continue;
			const h = halaqahMap.get(s.halaqah_id ?? '');
			result.set(s.id, {
				student: s,
				halaqahId: s.halaqah_id ?? '',
				halaqahName: h?.name ?? 'بدون حلقة',
				teacherId: h?.teacher_id ?? '',
				teacherName: h?.teacher_name ?? '—',
				recordsByDate: new Map(),
				stats: { present: 0, absent: 0, excused: 0, total: 0, rate: 0 }
			});
		}

		for (const r of records) {
			const entry = result.get(r.student_id);
			if (!entry) continue;
			entry.recordsByDate.set(r.record_date, r);
			entry.stats[attendanceStatus(r)]++;
			entry.stats.total++;
		}

		for (const entry of result.values()) {
			const { present, total } = entry.stats;
			entry.stats.rate = total > 0 ? Math.round((present / total) * 100) : 0;
		}

		return result;
	});

	const days = $derived(Array.from({ length: daysInMonth(month) }, (_, i) => i + 1));

	// ─── derived: filtered + sorted rows ──────────────────────────────────────
	const filteredRows = $derived.by((): StudentRow[] => {
		let rows = [...attendanceMatrix.values()];

		if (search.trim()) {
			const q = search.trim();
			rows = rows.filter((r) => r.student.full_name.includes(q));
		}

		if (selectedDay !== null && statusFilter !== 'all') {
			const dateStr = isoDate(month, selectedDay);
			rows = rows.filter((r) => {
				const rec = r.recordsByDate.get(dateStr);
				if (statusFilter === 'absent') return !rec || attendanceStatus(rec) === 'absent';
				if (!rec) return false;
				return attendanceStatus(rec) === statusFilter;
			});
		} else if (selectedDay === null && statusFilter !== 'all') {
			rows = rows.filter((r) => {
				if (statusFilter === 'present') return r.stats.present > 0;
				if (statusFilter === 'absent') return r.stats.absent > 0;
				if (statusFilter === 'excused') return r.stats.excused > 0;
				return true;
			});
		}

		rows.sort((a, b) => {
			if (sortBy === 'name') return a.student.full_name.localeCompare(b.student.full_name, 'ar');
			if (sortBy === 'rate-asc') return a.stats.rate - b.stats.rate;
			if (sortBy === 'rate-desc') return b.stats.rate - a.stats.rate;
			const hc = a.halaqahName.localeCompare(b.halaqahName, 'ar');
			return hc !== 0 ? hc : a.student.full_name.localeCompare(b.student.full_name, 'ar');
		});

		return rows;
	});

	const hasActiveFilters = $derived(
		!!(search || halaqahId || teacherId || statusFilter !== 'all' || selectedDay !== null)
	);

	function clearFilters() {
		search = '';
		halaqahId = '';
		teacherId = '';
		statusFilter = 'all';
		selectedDay = null;
	}

	// ─── derived: summary stats ────────────────────────────────────────────────
	const summary = $derived.by(() => {
		const rows = filteredRows;
		const count = rows.length;
		const totalPresent = rows.reduce((s, r) => s + r.stats.present, 0);
		const totalAbsent = rows.reduce((s, r) => s + r.stats.absent, 0);
		const totalExcused = rows.reduce((s, r) => s + r.stats.excused, 0);
		const avgRate = count > 0 ? Math.round(rows.reduce((s, r) => s + r.stats.rate, 0) / count) : 0;

		let dayPresent = 0,
			dayAbsent = 0,
			dayExcused = 0;
		if (selectedDay !== null) {
			const dateStr = isoDate(month, selectedDay);
			for (const r of rows) {
				const rec = r.recordsByDate.get(dateStr);
				if (!rec) {
					dayAbsent++;
					continue;
				}
				const st = attendanceStatus(rec);
				if (st === 'present') dayPresent++;
				else if (st === 'excused') dayExcused++;
				else dayAbsent++;
			}
		}

		return {
			count,
			totalPresent,
			totalAbsent,
			totalExcused,
			avgRate,
			dayPresent,
			dayAbsent,
			dayExcused
		};
	});

	// ─── data loading ──────────────────────────────────────────────────────────
	async function fetchAll<T>(
		fetcher: (offset: number) => Promise<{ items: T[]; total: number }>
	): Promise<T[]> {
		const PAGE = 200;
		const first = await fetcher(0);
		let items = first.items;
		let offset = PAGE;
		while (items.length < first.total) {
			const pageRes = await fetcher(offset);
			items = items.concat(pageRes.items);
			offset += PAGE;
			if (pageRes.items.length === 0) break;
		}
		return items;
	}

	onMount(async () => {
		const [h, t] = await Promise.all([
			fetchAll((offset) => halaqahsApi.list({ limit: 200, offset })),
			fetchAll((offset) => teachersApi.list({ limit: 200, offset }))
		]);
		halaqahs = h;
		teachers = t;
	});

	$effect(() => {
		loadData(month, halaqahId);
	});

	async function loadData(m: string, hid: string) {
		loading = true;
		const { from, to } = monthBounds(m);
		try {
			const [recs, studs] = await Promise.all([
				fetchAll((offset) =>
					dailyRecordsApi.list({
						date_from: from,
						date_to: to,
						halaqah_id: hid || undefined,
						limit: 200,
						offset
					})
				),
				fetchAll((offset) => studentsApi.list({ halaqah_id: hid || undefined, limit: 200, offset }))
			]);
			records = recs;
			students = studs;
		} finally {
			loading = false;
		}
	}

	// ─── heatmap cell styling ──────────────────────────────────────────────────
	function cellClass(st: string): string {
		if (st === 'present') return 'bg-emerald-500 hover:bg-emerald-600';
		if (st === 'excused') return 'bg-blue-500 hover:bg-blue-600';
		if (st === 'absent') return 'bg-red-400 hover:bg-red-500';
		return 'bg-muted hover:bg-muted-foreground/20';
	}
</script>

<div class="space-y-5" dir="rtl">
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
	<div
		class="sticky top-0 z-30 rounded-2xl border border-border bg-card/95 p-3 shadow-md backdrop-blur-sm"
	>
		<div class="flex flex-wrap items-center gap-2">
			<div class="relative min-w-[160px] flex-1">
				<Search
					class="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground"
				/>
				<input
					type="search"
					bind:value={search}
					placeholder="بحث باسم الطالب..."
					class="h-8 w-full rounded-lg border border-input bg-background pr-8 pl-3 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
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
				{#each [{ key: 'all', label: 'الكل', dot: '' }, { key: 'present', label: 'حاضر', dot: 'bg-emerald-500' }, { key: 'absent', label: 'غائب', dot: 'bg-red-500' }, { key: 'excused', label: 'مأذون', dot: 'bg-blue-500' }] as tab (tab.key)}
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

	<!-- ─── Summary cards ─── -->
	{#if !loading}
		{@const s = summary}
		<div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
			<div class="flex flex-col gap-1.5 rounded-xl border border-border bg-card p-4 shadow-sm">
				<div class="flex items-center gap-2 text-xs text-muted-foreground">
					<Users class="h-4 w-4" />إجمالي الطلاب
				</div>
				<p class="text-2xl font-bold text-foreground">{s.count}</p>
				<p class="text-[10px] text-muted-foreground">{formatMonth(month)}</p>
			</div>
			<div class="flex flex-col gap-1.5 rounded-xl border border-border bg-card p-4 shadow-sm">
				<div class="flex items-center gap-2 text-xs text-muted-foreground">
					<TrendingUp class="h-4 w-4" />معدل الحضور
				</div>
				<p class={'text-2xl font-bold ' + rateColor(s.avgRate)}>{s.avgRate}%</p>
				<p class="text-[10px] text-muted-foreground">
					{selectedDay !== null ? dayLabel(month, selectedDay) : 'متوسط الشهر'}
				</p>
			</div>
			<div class="flex flex-col gap-1.5 rounded-xl border border-border bg-card p-4 shadow-sm">
				<div class="flex items-center gap-2 text-xs text-muted-foreground">
					<CalendarCheck class="h-4 w-4 text-emerald-500" />إجمالي الحضور
				</div>
				<p class="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
					{selectedDay !== null ? s.dayPresent : s.totalPresent}
				</p>
				<p class="text-[10px] text-muted-foreground">
					{selectedDay !== null ? 'طالب حاضر' : 'يوم-طالب'}
				</p>
			</div>
			<div class="flex flex-col gap-1.5 rounded-xl border border-border bg-card p-4 shadow-sm">
				<div class="flex items-center gap-2 text-xs text-muted-foreground">
					<CalendarX class="h-4 w-4 text-red-500" />إجمالي الغياب
				</div>
				<p class="text-2xl font-bold text-red-600 dark:text-red-400">
					{selectedDay !== null ? s.dayAbsent : s.totalAbsent}
				</p>
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
			>انقر على رقم اليوم في رأس الجدول لتصفية حالة ذلك اليوم</span
		>
		<div class="flex items-center gap-3 text-[11px] text-muted-foreground">
			<span class="flex items-center gap-1.5"
				><span class="h-3 w-3 rounded-sm bg-emerald-500"></span>حاضر</span
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
	{:else if filteredRows.length === 0}
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
						<!-- halaqah header (sticky right + top) -->
						<th
							class="sticky right-0 top-0 z-40 w-28 border-b border-l border-border bg-muted/60 px-3 py-2 text-right text-xs font-bold text-muted-foreground backdrop-blur"
						>
							الحلقة
						</th>
						<!-- teacher header (sticky right offset + top) -->
						<th
							class="sticky right-28 top-0 z-40 w-28 border-b border-l border-border bg-muted/60 px-3 py-2 text-right text-xs font-bold text-muted-foreground backdrop-blur"
						>
							المعلم
						</th>
						<!-- student header (sticky right offset + top) -->
						<th
							class="sticky right-56 top-0 z-40 w-36 border-b border-l border-border bg-muted/60 px-3 py-2 text-right text-xs font-bold text-muted-foreground backdrop-blur"
						>
							الطالب
						</th>
						<!-- day headers -->
						{#each days as day (day)}
							{@const weekend = isWeekend(month, day)}
							{@const isToday = isoDate(month, day) === todayIso}
							<th
								class={'sticky top-0 z-20 border-b border-border px-0 py-1 text-center backdrop-blur ' +
									(selectedDay === day ? 'bg-primary/15' : weekend ? 'bg-muted/70' : 'bg-muted/40')}
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
						<!-- contact header (sticky left + top) -->
						<th
							class="sticky left-0 top-0 z-40 w-16 border-b border-r border-border bg-muted/60 px-2 py-2 text-center text-xs font-bold text-muted-foreground backdrop-blur"
						>
							تواصل
						</th>
					</tr>
				</thead>
				<tbody>
					{#each filteredRows as row, i (row.student.id)}
						{@const wa = whatsappLink(
							row.student.father_number,
							`السلام عليكم، بخصوص الطالب ${row.student.full_name} — ${formatMonth(month)}: حضر ${row.stats.present} من ${row.stats.total} يوم مُسجَّل (غياب: ${row.stats.absent}، إذن: ${row.stats.excused}).`
						)}
						{@const newHalaqah = i === 0 || filteredRows[i - 1].halaqahId !== row.halaqahId}
						<tr class="group">
							<!-- halaqah cell (sticky right) -->
							<td
								class={'sticky right-0 z-10 w-28 border-b border-l border-border bg-card px-3 py-2 align-middle group-hover:bg-muted/40 ' +
									(sortBy === 'halaqah' && !newHalaqah ? 'text-transparent' : '')}
							>
								{#if sortBy !== 'halaqah' || newHalaqah}
									{#if row.halaqahId}
										<a
											href={`/admin/halaqahs/${row.halaqahId}`}
											class="flex items-center gap-1 truncate text-xs font-semibold text-primary hover:underline"
											title={row.halaqahName}
										>
											<span class="truncate">{row.halaqahName}</span>
										</a>
									{:else}
										<span class="truncate text-xs text-muted-foreground">{row.halaqahName}</span>
									{/if}
								{/if}
							</td>
							<!-- teacher cell (sticky right offset) -->
							<td
								class={'sticky right-28 z-10 w-28 border-b border-l border-border bg-card px-3 py-2 align-middle group-hover:bg-muted/40 ' +
									(sortBy === 'halaqah' && !newHalaqah ? 'text-transparent' : '')}
							>
								{#if sortBy !== 'halaqah' || newHalaqah}
									{#if row.teacherId}
										<a
											href={`/admin/teachers/${row.teacherId}`}
											class="truncate text-xs font-medium text-primary hover:underline"
											title={row.teacherName}
										>
											{row.teacherName}
										</a>
									{:else}
										<span class="truncate text-xs text-muted-foreground">{row.teacherName}</span>
									{/if}
								{/if}
							</td>
							<!-- student cell (sticky right offset) -->
							<td
								class="sticky right-56 z-10 w-36 border-b border-l border-border bg-card px-3 py-2 align-middle group-hover:bg-muted/40"
							>
								<a
									href={`/admin/students/${row.student.id}`}
									class="flex items-center justify-between gap-1.5 hover:underline"
								>
									<span
										class="truncate text-xs font-medium text-foreground"
										title={row.student.full_name}>{row.student.full_name}</span
									>
									<span class={'shrink-0 text-[10px] font-bold ' + rateColor(row.stats.rate)}
										>{row.stats.rate}%</span
									>
								</a>
							</td>
							<!-- day cells -->
							{#each days as day (day)}
								{@const rec = row.recordsByDate.get(isoDate(month, day))}
								{@const st = rec ? attendanceStatus(rec) : 'empty'}
								<td
									class={'border-b border-border px-0 py-0.5 text-center group-hover:bg-muted/40 ' +
										(selectedDay === day ? 'bg-primary/5' : '')}
								>
									<div
										title={`${row.student.full_name} • ${dayLabel(month, day)}: ${statusLabel(st)}`}
										class={'mx-auto h-6 w-6 rounded-md transition ' +
											cellClass(st) +
											(selectedDay === day ? ' ring-2 ring-primary/40' : '')}
									></div>
								</td>
							{/each}
							<!-- contact cell (sticky left) -->
							<td
								class="sticky left-0 z-10 w-16 border-b border-r border-border bg-card px-2 py-2 text-center group-hover:bg-muted/40"
							>
								{#if wa}
									<a
										href={wa}
										target="_blank"
										rel="noopener noreferrer"
										class="mx-auto flex h-7 w-7 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-600 transition hover:bg-emerald-500 hover:text-white dark:text-emerald-400"
										title={`تواصل مع ولي أمر ${row.student.full_name}`}
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

		<p class="px-1 text-xs text-muted-foreground">
			عرض {filteredRows.length} طالب · {formatMonth(month)}
		</p>
	{/if}
</div>
