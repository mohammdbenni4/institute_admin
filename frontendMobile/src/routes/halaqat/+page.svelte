<script lang="ts">
	import { onMount } from 'svelte';
	import { ApiError, auth, type Halaqah } from '$lib/api';
	import { repo } from '$lib/offline';
	import TopBar from '$lib/components/TopBar.svelte';
	import BottomNav from '$lib/components/BottomNav.svelte';
	import Spinner from '$lib/components/Spinner.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import Icon from '$lib/components/Icon.svelte';

	let status = $state<'loading' | 'ready' | 'error'>('loading');
	let items = $state<Halaqah[]>([]);
	let error = $state('');

	onMount(load);

	async function load() {
		const teacher = auth.teacher;
		if (!teacher) return; // guard is redirecting to /login
		status = 'loading';
		try {
			items = await repo.listHalaqahs(teacher.id);
			status = 'ready';
		} catch (e) {
			error = e instanceof ApiError ? e.message : 'تعذّر تحميل الحلقات';
			status = 'error';
		}
	}
</script>

<TopBar title="حلقاتي" subtitle={auth.teacher?.full_name ?? ''} />

<main class="mx-auto max-w-2xl px-4 pb-28 pt-20">
	{#if status === 'loading'}
		<Spinner label="جارٍ تحميل الحلقات…" />
	{:else if status === 'error'}
		<EmptyState icon="error" title="حدث خطأ" hint={error} />
	{:else if items.length === 0}
		<EmptyState icon="school" title="لا توجد حلقات" hint="لم تُسنَد إليك أي حلقة بعد." />
	{:else}
		<ul class="space-y-3">
			{#each items as h (h.id)}
				<li>
					<a
						href={`/halaqat/${h.id}`}
						class="flex items-center gap-4 rounded-[2rem] border border-outline-variant/10 bg-surface-container-lowest p-4 shadow-sm transition active:scale-[0.99]"
					>
						<div
							class="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary"
						>
							<Icon name="groups" filled class="text-2xl" />
						</div>
						<div class="min-w-0 flex-1">
							<p class="truncate text-[15px] font-bold text-on-surface">{h.name}</p>
							<p class="truncate text-[11px] text-on-surface-variant/70">
								{h.halaqah_type_name}{h.level ? ` · ${h.level}` : ''}
							</p>
						</div>
						<div class="flex flex-col items-center px-1">
							<span class="text-lg font-bold leading-none text-primary">{h.number_of_students}</span
							>
							<span class="mt-0.5 text-[9px] text-on-surface-variant/60">طالب</span>
						</div>
						<Icon name="chevron_left" class="text-on-surface-variant/30" />
					</a>
				</li>
			{/each}
		</ul>
	{/if}
</main>

<BottomNav />
