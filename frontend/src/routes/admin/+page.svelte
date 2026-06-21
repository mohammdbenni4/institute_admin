<script lang="ts">
	import PageHeader from '$lib/components/shared/PageHeader.svelte';
	import KPICard from '$lib/components/shared/KPICard.svelte';
	import StatusBadge from '$lib/components/shared/StatusBadge.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import {
		analyticsApi,
		halaqahsApi,
		halaqahTypesApi,
		studentsApi,
		teachersApi,
		timesApi,
		usersApi,
		type AnalyticsOverview,
		type AtRiskStudent,
		type HalaqahLeaderboard
	} from '$lib/api';
	import { currentMonth, formatMonth, monthBounds } from '$lib/labels';
	import {
		AlertTriangle,
		BookOpen,
		CalendarCheck,
		Clock,
		GraduationCap,
		Layers,
		Star,
		Trophy,
		UserCheck,
		Users
	} from '@lucide/svelte';
	import type { Component } from 'svelte';

	let month = $state(currentMonth());

	let overview = $state<AnalyticsOverview | null>(null);
	let leaderboard = $state<HalaqahLeaderboard[]>([]);
	let atRisk = $state<AtRiskStudent[]>([]);
	let loadingAnalytics = $state(true);
	let analyticsError = $state('');

	async function loadAnalytics() {
		loadingAnalytics = true;
		analyticsError = '';
		const { from, to } = monthBounds(month);
		try {
			const [ov, lb, ar] = await Promise.all([
				analyticsApi.overview({ date_from: from, date_to: to }),
				analyticsApi.leaderboard({ date_from: from, date_to: to, top: 3 }),
				analyticsApi.atRisk({ date_from: from, date_to: to })
			]);
			overview = ov;
			leaderboard = lb.items;
			atRisk = ar.items;
		} catch {
			analyticsError = 'تعذّر تحميل التحليلات. تأكد من تشغيل الخادم.';
		} finally {
			loadingAnalytics = false;
		}
	}

	$effect(() => {
		void month;
		loadAnalytics();
	});

	// Institute entity counts (loaded once).
	interface Metric {
		key: string;
		title: string;
		href: string;
		icon: Component<{ class?: string }>;
		total: number | null;
	}
	let metrics = $state<Metric[]>([
		{ key: 'users', title: 'المستخدمون', href: '/admin/users', icon: Users, total: null },
		{ key: 'teachers', title: 'المعلمون', href: '/admin/teachers', icon: UserCheck, total: null },
		{ key: 'students', title: 'الطلاب', href: '/admin/students', icon: GraduationCap, total: null },
		{ key: 'halaqahs', title: 'الحلقات', href: '/admin/halaqahs', icon: BookOpen, total: null },
		{
			key: 'types',
			title: 'أنواع الحلقات',
			href: '/admin/halaqah-types',
			icon: Layers,
			total: null
		},
		{ key: 'times', title: 'الأوقات', href: '/admin/times', icon: Clock, total: null }
	]);

	async function loadCounts() {
		try {
			const [users, teachers, students, halaqahs, types, times] = await Promise.all([
				usersApi.list({ limit: 1 }),
				teachersApi.list({ limit: 1 }),
				studentsApi.list({ limit: 1 }),
				halaqahsApi.list({ limit: 1 }),
				halaqahTypesApi.list({ limit: 1 }),
				timesApi.list({ limit: 1 })
			]);
			const totals: Record<string, number> = {
				users: users.total,
				teachers: teachers.total,
				students: students.total,
				halaqahs: halaqahs.total,
				types: types.total,
				times: times.total
			};
			metrics = metrics.map((m) => ({ ...m, total: totals[m.key] ?? 0 }));
		} catch {
			/* analytics error banner already covers a down server */
		}
	}

	$effect(() => {
		loadCounts();
	});

	const rankStyles = [
		'bg-amber-100 text-amber-700',
		'bg-slate-200 text-slate-600',
		'bg-orange-100 text-orange-700'
	];
</script>

<div class="page-container">
	<PageHeader title="لوحة التحكم" subtitle="نظرة عامة وتحليلات الأداء">
		{#snippet actions()}
			<div class="flex items-center gap-2">
				<span class="text-sm text-muted-foreground">{formatMonth(month)}</span>
				<Input type="month" bind:value={month} class="w-40" aria-label="الشهر" />
			</div>
		{/snippet}
	</PageHeader>

	{#if analyticsError}
		<p class="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{analyticsError}</p>
	{/if}

	<!-- Overview KPIs -->
	<div class="grid grid-cols-2 gap-4 lg:grid-cols-4">
		<KPICard title="سجلات الشهر" value={overview ? overview.records : '…'} icon={CalendarCheck} />
		<KPICard
			title="نسبة الحضور"
			value={overview ? `${Math.round(overview.attendance_rate * 100)}%` : '…'}
			icon={CalendarCheck}
			subtitle={overview ? `${overview.present} حاضر · ${overview.absent} غائب` : ''}
		/>
		<KPICard title="مجموع النقاط" value={overview ? overview.total_points : '…'} icon={Star} />
		<KPICard
			title="الطلاب النشطون"
			value={overview ? overview.active_students : '…'}
			icon={Users}
			subtitle="سُجِّل لهم هذا الشهر"
		/>
	</div>

	<!-- Best students per halaqah -->
	<div>
		<div class="mb-3 flex items-center gap-2">
			<Trophy class="h-5 w-5 text-amber-500" />
			<h2 class="section-title">الأفضل في كل حلقة</h2>
		</div>
		{#if loadingAnalytics}
			<div class="glass-card p-8 text-center text-muted-foreground">جارٍ التحميل…</div>
		{:else if leaderboard.length === 0}
			<div class="glass-card p-8 text-center text-muted-foreground">
				لا توجد سجلات في هذا الشهر بعد.
			</div>
		{:else}
			<div class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
				{#each leaderboard as board (board.halaqah_id)}
					<div class="glass-card p-5">
						<div class="mb-3 flex items-center gap-2 border-b border-border/60 pb-3">
							<BookOpen class="h-4 w-4 text-primary" />
							<p class="font-bold text-foreground">{board.halaqah_name}</p>
						</div>
						<ol class="space-y-2">
							{#each board.students as s (s.student_id)}
								<li>
									<a
										href={`/admin/students/${s.student_id}`}
										class="flex items-center gap-3 rounded-xl px-2 py-1.5 transition-colors hover:bg-muted/40"
									>
										<span
											class={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold ${rankStyles[s.rank - 1] ?? 'bg-muted text-muted-foreground'}`}
										>
											{s.rank}
										</span>
										<span class="min-w-0 flex-1 truncate text-sm font-medium">{s.student_name}</span
										>
										<span class="flex items-center gap-1 text-sm font-bold text-primary">
											{s.total_points}<Star class="h-3.5 w-3.5" />
										</span>
									</a>
								</li>
							{/each}
						</ol>
					</div>
				{/each}
			</div>
		{/if}
	</div>

	<!-- At-risk students -->
	<div>
		<div class="mb-3 flex items-center gap-2">
			<AlertTriangle class="h-5 w-5 text-red-500" />
			<h2 class="section-title">الطلاب المتعثرون</h2>
		</div>
		{#if loadingAnalytics}
			<div class="glass-card p-8 text-center text-muted-foreground">جارٍ التحميل…</div>
		{:else if atRisk.length === 0}
			<div class="glass-card p-8 text-center text-muted-foreground">
				لا يوجد طلاب متعثرون هذا الشهر 👍
			</div>
		{:else}
			<div class="glass-card divide-y divide-border/50">
				{#each atRisk as s (s.student_id)}
					<a
						href={`/admin/students/${s.student_id}`}
						class="flex items-center justify-between gap-3 p-4 transition-colors hover:bg-muted/30"
					>
						<div class="min-w-0">
							<p class="truncate font-medium text-foreground">{s.student_name}</p>
							<p class="truncate text-xs text-muted-foreground">{s.halaqah_name}</p>
						</div>
						<div class="flex flex-wrap items-center justify-end gap-1.5">
							{#each s.reasons as reason (reason)}
								<StatusBadge label={reason} tone="danger" />
							{/each}
						</div>
					</a>
				{/each}
			</div>
		{/if}
	</div>

	<!-- Institute data counts -->
	<div>
		<h2 class="section-title mb-3">بيانات المعهد</h2>
		<div class="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
			{#each metrics as metric (metric.key)}
				<a href={metric.href} class="block transition-transform hover:-translate-y-0.5">
					<KPICard
						title={metric.title}
						value={metric.total === null ? '…' : metric.total}
						icon={metric.icon}
					/>
				</a>
			{/each}
		</div>
	</div>
</div>
