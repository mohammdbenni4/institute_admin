<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import {
		ApiError,
		auth,
		dailyRecordsApi,
		halaqahsApi,
		studentsApi,
		type Halaqah,
		type Student
	} from '$lib/api';
	import { todayIso } from '$lib/utils';
	import TopBar from '$lib/components/TopBar.svelte';
	import BottomNav from '$lib/components/BottomNav.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import Avatar from '$lib/components/Avatar.svelte';
	import Icon from '$lib/components/Icon.svelte';

	const halaqahId = $derived($page.params.halaqahId ?? '');

	let status = $state<'loading' | 'ready' | 'error'>('loading');
	let halaqah = $state<Halaqah | null>(null);
	let students = $state<Student[]>([]);
	let recordedToday = $state<Set<string>>(new Set());
	let error = $state('');

	onMount(load);

	async function load() {
		if (!auth.teacher) return;
		status = 'loading';
		try {
			const [h, list, today] = await Promise.all([
				halaqahsApi.get(halaqahId),
				studentsApi.list({ halaqah_id: halaqahId, limit: 200 }),
				dailyRecordsApi.list({ halaqah_id: halaqahId, record_date: todayIso(), limit: 200 })
			]);
			halaqah = h;
			students = list.items;
			recordedToday = new Set(today.items.map((r) => r.student_id));
			status = 'ready';
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'تعذّر تحميل الطلاب';
			status = 'error';
		}
	}
</script>

<TopBar title={halaqah?.name ?? 'الحلقة'} subtitle="طلاب الحلقة" backHref="/halaqat">
	{#snippet actions()}
		<a
			href={`/halaqat/${halaqahId}/attendance`}
			class="flex items-center gap-1 rounded-full bg-white/15 px-3 py-1.5 text-xs font-bold transition hover:bg-white/25 active:scale-95"
		>
			<Icon name="fact_check" class="text-base" /> الحضور
		</a>
	{/snippet}
</TopBar>

<main class="mx-auto max-w-2xl px-4 pb-28 pt-20">
	{#if status === 'loading'}
		<Spinner label="جارٍ تحميل الطلاب…" />
	{:else if status === 'error'}
		<EmptyState icon="error" title="حدث خطأ" hint={error} />
	{:else if students.length === 0}
		<EmptyState icon="person_off" title="لا يوجد طلاب" hint="لا يوجد طلاب مسجّلون في هذه الحلقة." />
	{:else}
		<div class="mb-3 flex items-center justify-between px-1">
			<span class="text-[13px] font-bold text-on-surface-variant">{students.length} طالب</span>
			<span class="flex items-center gap-1 text-[11px] text-on-surface-variant/70">
				<Icon name="event_available" class="text-sm text-primary" /> سُجِّل اليوم: {recordedToday.size}
			</span>
		</div>
		<ul class="space-y-3">
			{#each students as s (s.id)}
				{@const done = recordedToday.has(s.id)}
				<li>
					<a
						href={`/halaqat/${halaqahId}/${s.id}`}
						class="flex items-center gap-3 rounded-[2rem] border border-outline-variant/10 bg-surface-container-lowest p-3.5 shadow-sm transition active:scale-[0.99]"
					>
						<Avatar name={s.full_name} />
						<div class="min-w-0 flex-1">
							<p class="truncate text-[15px] font-bold text-on-surface">{s.full_name}</p>
							<p class="truncate text-[11px] text-on-surface-variant/60">
								{s.father_name ? `الأب: ${s.father_name}` : 'سجل اليومي'}
							</p>
						</div>
						{#if done}
							<span
								class="flex items-center gap-1 rounded-full bg-primary/10 px-2.5 py-1 text-[10px] font-bold text-primary"
							>
								<Icon name="check_circle" filled class="text-sm" /> اليوم
							</span>
						{:else}
							<span
								class="flex items-center gap-1 rounded-full bg-surface-container-high px-2.5 py-1 text-[10px] font-medium text-on-surface-variant/70"
							>
								<Icon name="schedule" class="text-sm" /> بانتظار
							</span>
						{/if}
						<Icon name="chevron_left" class="text-on-surface-variant/30" />
					</a>
				</li>
			{/each}
		</ul>
	{/if}
</main>

<BottomNav />
