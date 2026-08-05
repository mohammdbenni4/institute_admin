<script lang="ts">
	// «استدعاء ولي أمر» — the teacher's own requests and their live status.
	import { onMount } from 'svelte';
	import { auth } from '$lib/api';
	import { net, repo, syncState } from '$lib/offline';
	import { formatDateArabic } from '$lib/utils';
	import TopBar from '$lib/components/TopBar.svelte';
	import BottomNav from '$lib/components/BottomNav.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import Icon from '$lib/components/Icon.svelte';

	let status = $state<'loading' | 'ready' | 'error'>('loading');
	let items = $state<repo.SummonEntry[]>([]);
	let error = $state('');

	async function load() {
		if (!auth.teacher) return;
		try {
			items = await repo.listSummons();
			status = 'ready';
		} catch {
			error = 'تعذّر تحميل الطلبات';
			status = 'error';
		}
	}

	onMount(load);

	// Re-read once a queued request has been uploaded, so it swaps to its real status.
	$effect(() => {
		void syncState.pending;
		if (status === 'ready') void load();
	});

	/** Colour per stage of the workflow. */
	function tone(s: repo.SummonEntry['status']): string {
		if (s === 'completed') return 'bg-emerald-500/10 text-emerald-700 border-emerald-500/30';
		if (s === 'reviewing') return 'bg-amber-500/10 text-amber-700 border-amber-500/30';
		if (s === 'queued')
			return 'bg-surface-container-high text-on-surface-variant/70 border-outline-variant/30';
		return 'bg-primary/10 text-primary border-primary/30';
	}

	function stageIcon(s: repo.SummonEntry['status']): string {
		if (s === 'completed') return 'task_alt';
		if (s === 'reviewing') return 'history';
		if (s === 'queued') return 'cloud_upload';
		return 'mail';
	}
</script>

<TopBar title="استدعاء ولي أمر" subtitle="طلباتك وحالتها" backHref="/halaqat" />

<main class="mx-auto max-w-2xl space-y-3 px-3 pb-28 pt-[4.5rem]" dir="rtl">
	{#if status === 'loading'}
		<Spinner label="جارٍ التحميل…" />
	{:else if status === 'error'}
		<EmptyState icon="error" title="حدث خطأ" hint={error} />
	{:else if items.length === 0}
		<EmptyState
			icon="groups"
			title="لا توجد طلبات"
			hint="يمكنك طلب استدعاء ولي أمر من صفحة الطالب."
		/>
	{:else}
		{#if !net.online}
			<p
				class="rounded-2xl border border-amber-300 bg-amber-50 px-4 py-2.5 text-[12px] font-bold text-amber-800"
			>
				لا يوجد اتصال — الحالات المعروضة قد لا تكون محدّثة.
			</p>
		{/if}

		{#each items as item (item.id)}
			<section
				class="space-y-3 rounded-3xl border border-outline-variant/15 bg-surface-container-lowest p-4 shadow-card"
			>
				<div class="flex items-start gap-2">
					<div class="min-w-0 flex-1">
						<p class="truncate text-[15px] font-bold text-on-surface">{item.studentName}</p>
						{#if item.halaqahName}
							<p class="truncate text-[11px] text-on-surface-variant/60">{item.halaqahName}</p>
						{/if}
					</div>
					<span
						class={'flex shrink-0 items-center gap-1 rounded-full border px-2.5 py-1 text-[10px] font-bold ' +
							tone(item.status)}
					>
						<Icon name={stageIcon(item.status)} class="text-[13px]" />
						{item.statusLabel}
					</span>
				</div>

				<div class="rounded-2xl bg-surface-container-low p-3">
					<p class="text-[10px] font-medium text-on-surface-variant/50">سبب الطلب</p>
					<p class="text-[13px] leading-relaxed text-on-surface">{item.reason}</p>
				</div>

				{#if item.adminResponse}
					<div class="rounded-2xl border border-emerald-500/25 bg-emerald-500/5 p-3">
						<p class="flex items-center gap-1 text-[10px] font-bold text-emerald-700">
							<Icon name="check_circle" filled class="text-[13px]" /> رد الإدارة
						</p>
						<p class="mt-0.5 text-[13px] leading-relaxed text-on-surface">{item.adminResponse}</p>
					</div>
				{/if}

				<p class="text-[10px] text-on-surface-variant/50">
					{formatDateArabic(item.createdAt.slice(0, 10))}
				</p>
			</section>
		{/each}
	{/if}
</main>

<BottomNav />
