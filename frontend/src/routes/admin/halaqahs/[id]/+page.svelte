<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import PageHeader from '$lib/components/shared/PageHeader.svelte';
	import KPICard from '$lib/components/shared/KPICard.svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import {
		ApiError,
		dailyRecordsApi,
		halaqahsApi,
		studentsApi,
		type DailyRecord,
		type Halaqah,
		type Student
	} from '$lib/api';
	import { currentMonth, formatMonth, monthBounds } from '$lib/labels';
	import { cn } from '$lib/utils';
	import { ArrowRight, BookOpen, CalendarCheck, Star, Trophy, Users } from '@lucide/svelte';

	let id = $derived($page.params.id ?? '');

	let halaqah = $state<Halaqah | null>(null);
	let students = $state<Student[]>([]);
	let records = $state<DailyRecord[]>([]);
	let month = $state(currentMonth());
	let loadingRecords = $state(true);
	let error = $state('');

	async function loadHalaqah() {
		error = '';
		try {
			halaqah = await halaqahsApi.get(id);
			students = (await studentsApi.list({ halaqah_id: id, limit: 200 })).items;
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'تعذّر تحميل الحلقة.';
		}
	}

	async function loadRecords() {
		loadingRecords = true;
		const { from, to } = monthBounds(month);
		try {
			records = (
				await dailyRecordsApi.list({ halaqah_id: id, date_from: from, date_to: to, limit: 200 })
			).items;
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'تعذّر تحميل السجلات.';
		} finally {
			loadingRecords = false;
		}
	}

	$effect(() => {
		if (id) loadHalaqah();
	});
	$effect(() => {
		if (id) {
			void month;
			loadRecords();
		}
	});

	let kpis = $derived.by(() => {
		const sessions = records.length;
		const present = records.filter((r) => r.present).length;
		const points = records.reduce((s, r) => s + r.total_points, 0);
		return {
			sessions,
			attendance: sessions ? Math.round((present / sessions) * 100) : 0,
			points
		};
	});

	// Top students this month by total points.
	let leaderboard = $derived.by(() => {
		const map = new Map<
			string,
			{ name: string; points: number; present: number; sessions: number }
		>();
		const names = new Map(students.map((s) => [s.id, s.full_name]));
		for (const r of records) {
			const cur = map.get(r.student_id) ?? {
				name: names.get(r.student_id) ?? '—',
				points: 0,
				present: 0,
				sessions: 0
			};
			cur.points += r.total_points;
			cur.sessions += 1;
			cur.present += r.present ? 1 : 0;
			map.set(r.student_id, cur);
		}
		return [...map.entries()]
			.map(([student_id, v]) => ({ student_id, ...v }))
			.sort((a, b) => b.points - a.points)
			.slice(0, 5);
	});

	let daysInMonth = $derived.by(() => {
		const [y, m] = month.split('-').map(Number);
		return new Date(y, m, 0).getDate();
	});

	// student_id -> day (1..n) -> attendance state
	type AttendanceState = 'present' | 'absent' | 'excused';
	let attendance = $derived.by(() => {
		const map = new Map<string, Map<number, AttendanceState>>();
		for (const r of records) {
			const day = Number(r.record_date.slice(8, 10));
			if (!map.has(r.student_id)) map.set(r.student_id, new Map());
			const state: AttendanceState = r.present ? 'present' : r.excused ? 'excused' : 'absent';
			map.get(r.student_id)!.set(day, state);
		}
		return map;
	});

	const rankStyles = [
		'bg-amber-100 text-amber-700',
		'bg-slate-200 text-slate-600',
		'bg-orange-100 text-orange-700'
	];

	function cellClass(studentId: string, day: number): string {
		const state = attendance.get(studentId)?.get(day);
		if (state === undefined) return 'bg-muted/40';
		if (state === 'present') return 'bg-emerald-400';
		if (state === 'excused') return 'bg-blue-400';
		return 'bg-red-300';
	}
</script>

<div class="page-container">
	<PageHeader
		title={halaqah?.name ?? 'ملف الحلقة'}
		subtitle={halaqah ? `المعلم: ${halaqah.teacher_name}` : ''}
		breadcrumbs={[{ label: 'لوحة التحكم' }, { label: 'الحلقات' }, { label: halaqah?.name ?? '…' }]}
	>
		{#snippet actions()}
			<Button variant="outline" onclick={() => goto('/admin/halaqahs')}>
				<ArrowRight class="h-4 w-4" />رجوع
			</Button>
		{/snippet}
	</PageHeader>

	{#if error}
		<p class="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
	{/if}

	<!-- Info -->
	<div class="glass-card p-5">
		<dl class="grid grid-cols-2 gap-x-8 gap-y-2 text-sm sm:grid-cols-4">
			<div>
				<dt class="text-muted-foreground">النوع</dt>
				<dd class="font-medium">{halaqah?.halaqah_type_name ?? '—'}</dd>
			</div>
			<div>
				<dt class="text-muted-foreground">المستوى</dt>
				<dd class="font-medium">{halaqah?.level ?? '—'}</dd>
			</div>
			<div>
				<dt class="text-muted-foreground">الفئة العمرية</dt>
				<dd class="font-medium">{halaqah?.age ?? '—'}</dd>
			</div>
			<div>
				<dt class="text-muted-foreground">عدد الطلاب</dt>
				<dd class="font-medium">{halaqah?.number_of_students ?? students.length}</dd>
			</div>
		</dl>
	</div>

	<!-- Month selector -->
	<div class="flex flex-wrap items-center gap-3">
		<label for="month" class="text-sm font-medium text-muted-foreground">الشهر</label>
		<Input id="month" type="month" bind:value={month} class="w-44" />
		<span class="text-sm text-muted-foreground">{formatMonth(month)}</span>
	</div>

	<!-- KPIs -->
	<div class="grid grid-cols-2 gap-4 lg:grid-cols-4">
		<KPICard title="عدد الطلاب" value={students.length} icon={Users} />
		<KPICard title="عدد السجلات" value={kpis.sessions} icon={CalendarCheck} />
		<KPICard title="نسبة الحضور" value={`${kpis.attendance}%`} icon={CalendarCheck} />
		<KPICard title="مجموع النقاط" value={kpis.points} icon={Star} />
	</div>

	<!-- Leaderboard -->
	<div class="glass-card p-5">
		<div class="mb-3 flex items-center gap-2">
			<Trophy class="h-5 w-5 text-amber-500" />
			<h2 class="section-title text-base">الأفضل هذا الشهر</h2>
		</div>
		{#if leaderboard.length === 0}
			<p class="text-sm text-muted-foreground">لا توجد سجلات في هذا الشهر.</p>
		{:else}
			<ol class="space-y-2">
				{#each leaderboard as s, i (s.student_id)}
					<li>
						<a
							href={`/admin/students/${s.student_id}`}
							class="flex items-center gap-3 rounded-xl px-2 py-1.5 transition-colors hover:bg-muted/40"
						>
							<span
								class={cn(
									'flex h-7 w-7 items-center justify-center rounded-full text-xs font-bold',
									rankStyles[i] ?? 'bg-muted text-muted-foreground'
								)}>{i + 1}</span
							>
							<span class="min-w-0 flex-1 truncate text-sm font-medium">{s.name}</span>
							<span class="text-xs text-muted-foreground">حضور {s.present}/{s.sessions}</span>
							<span class="flex items-center gap-1 text-sm font-bold text-primary"
								>{s.points}<Star class="h-3.5 w-3.5" /></span
							>
						</a>
					</li>
				{/each}
			</ol>
		{/if}
	</div>

	<!-- Attendance heatmap -->
	<div class="glass-card p-5">
		<div class="mb-3 flex flex-wrap items-center justify-between gap-2">
			<div class="flex items-center gap-2">
				<BookOpen class="h-5 w-5 text-primary" />
				<h2 class="section-title text-base">خريطة الحضور</h2>
			</div>
			<div class="flex items-center gap-3 text-xs text-muted-foreground">
				<span class="flex items-center gap-1"
					><span class="h-3 w-3 rounded-sm bg-emerald-400"></span>حاضر</span
				>
				<span class="flex items-center gap-1"
					><span class="h-3 w-3 rounded-sm bg-blue-400"></span>أذن</span
				>
				<span class="flex items-center gap-1"
					><span class="h-3 w-3 rounded-sm bg-red-300"></span>غائب</span
				>
				<span class="flex items-center gap-1"
					><span class="h-3 w-3 rounded-sm bg-muted/40"></span>لا يوجد</span
				>
			</div>
		</div>
		{#if loadingRecords}
			<p class="text-sm text-muted-foreground">جارٍ التحميل…</p>
		{:else if students.length === 0}
			<p class="text-sm text-muted-foreground">لا يوجد طلاب.</p>
		{:else}
			<div class="overflow-x-auto">
				<div class="min-w-max space-y-1">
					<!-- day header -->
					<div class="flex items-center gap-1">
						<span class="w-32 shrink-0"></span>
						{#each Array(daysInMonth) as _, d (d)}
							<span class="w-4 text-center text-[8px] text-muted-foreground">{d + 1}</span>
						{/each}
					</div>
					{#each students as s (s.id)}
						<div class="flex items-center gap-1">
							<a
								href={`/admin/students/${s.id}`}
								class="w-32 shrink-0 truncate text-xs font-medium text-primary hover:underline"
								>{s.full_name}</a
							>
							{#each Array(daysInMonth) as _, d (d)}
								<span class={cn('h-4 w-4 rounded-sm', cellClass(s.id, d + 1))} title={`${d + 1}`}
								></span>
							{/each}
						</div>
					{/each}
				</div>
			</div>
		{/if}
	</div>
</div>
