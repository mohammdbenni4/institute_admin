<script lang="ts">
	import {
		net,
		syncNow,
		syncState,
		listPendingChanges,
		discardChange,
		type PendingChange
	} from '$lib/offline';
	import { arabicNum, formatDateShort } from '$lib/utils';
	import Icon from './Icon.svelte';

	let showing = $state(false);
	let items = $state<PendingChange[]>([]);
	let expandedId = $state<string | null>(null); // row whose old→new diff is open
	let confirmingId = $state<string | null>(null); // row awaiting delete confirmation
	let discarding = $state(false);

	async function reload() {
		items = await listPendingChanges();
	}

	async function open() {
		showing = true;
		await reload();
	}

	function close() {
		showing = false;
		expandedId = null;
		confirmingId = null;
	}

	function toggle(id: string) {
		expandedId = expandedId === id ? null : id;
	}

	async function doDiscard(id: string) {
		if (discarding) return;
		discarding = true;
		try {
			await discardChange(id);
			confirmingId = null;
			if (expandedId === id) expandedId = null;
			await reload();
		} finally {
			discarding = false;
		}
	}

	async function upload() {
		await syncNow();
		await reload();
	}

	// Keep the open sheet in sync as records upload (or arrive) in the background.
	$effect(() => {
		void syncState.pending;
		if (showing) void reload();
	});
</script>

<!-- Floating status pill: amber = pending upload, green = everything synced. -->
{#if syncState.pending > 0}
	<button
		onclick={open}
		class="fixed bottom-24 right-4 z-40 flex items-center gap-1.5 rounded-full border border-amber-300 bg-amber-50 py-2 pe-3 ps-2.5 shadow-lg transition active:scale-95"
		aria-label="عرض التغييرات غير المرفوعة"
	>
		<Icon
			name={syncState.syncing ? 'progress_activity' : net.online ? 'cloud_off' : 'wifi_off'}
			class={`text-lg text-amber-600 ${syncState.syncing ? 'animate-spin' : ''}`}
		/>
		<span
			class="min-w-[1.25rem] rounded-full bg-amber-500 px-1.5 py-0.5 text-center text-[11px] font-bold text-white"
		>
			{arabicNum(syncState.pending)}
		</span>
	</button>
{:else}
	<button
		onclick={open}
		class="fixed bottom-24 right-4 z-40 flex h-10 w-10 items-center justify-center rounded-full border border-emerald-300 bg-emerald-50 shadow-lg transition active:scale-95"
		aria-label="حالة المزامنة"
	>
		<Icon name="cloud_done" class="text-lg text-emerald-600" />
	</button>
{/if}

{#if showing}
	<button type="button" onclick={close} class="fixed inset-0 z-[60] bg-black/40" aria-label="إغلاق"
	></button>
	<div
		class="fixed inset-x-0 bottom-0 z-[61] overflow-hidden rounded-t-[2rem] bg-surface-container-lowest shadow-2xl"
		dir="rtl"
	>
		<div class="flex items-center justify-between border-b border-outline-variant/10 px-5 py-4">
			<div class="flex items-center gap-2">
				<Icon
					name={syncState.pending > 0 ? 'cloud_off' : 'cloud_done'}
					class={syncState.pending > 0 ? 'text-2xl text-amber-600' : 'text-2xl text-emerald-600'}
				/>
				<div class="flex flex-col">
					<span class="text-[15px] font-bold text-on-surface">
						{syncState.pending > 0 ? 'تغييرات غير مرفوعة' : 'كل التغييرات مرفوعة'}
					</span>
					{#if syncState.pending > 0}
						<span class="text-[11px] text-on-surface-variant/60">
							{arabicNum(syncState.pending)} سجل بانتظار الرفع
						</span>
					{/if}
				</div>
			</div>
			<button
				onclick={close}
				class="rounded-full p-2 text-on-surface-variant transition active:scale-90"
				aria-label="إغلاق"
			>
				<Icon name="close" />
			</button>
		</div>

		{#if syncState.pending === 0}
			<div class="flex flex-col items-center gap-2 px-5 py-10 text-center">
				<Icon name="cloud_done" class="text-5xl text-emerald-500" />
				<p class="text-sm font-bold text-on-surface">تمت مزامنة جميع بياناتك</p>
				<p class="text-[11px] text-on-surface-variant/60">لا توجد تغييرات محلية بانتظار الرفع.</p>
			</div>
		{:else}
			<ul class="max-h-[50vh] divide-y divide-outline-variant/10 overflow-y-auto">
				{#each items as it (it.id)}
					<li class="px-3 py-1.5">
						<div class="flex items-center gap-1">
							<!-- tap the row to reveal what changed -->
							<button
								type="button"
								onclick={() => toggle(it.id)}
								class="flex min-w-0 flex-1 items-center gap-2.5 rounded-2xl px-2 py-2 text-right transition active:bg-surface-container-low"
							>
								<Icon
									name={expandedId === it.id ? 'expand_less' : 'expand_more'}
									class="shrink-0 text-lg text-on-surface-variant/50"
								/>
								<div class="min-w-0 flex-1">
									<p class="truncate text-[14px] font-bold text-on-surface">{it.studentName}</p>
									<p class="truncate text-[11px] text-on-surface-variant/60">
										{it.localOnly ? 'سجل جديد' : 'تعديل'} · {it.detail}
									</p>
								</div>
								<span class="shrink-0 text-[11px] text-on-surface-variant/50">
									{formatDateShort(it.dateIso)}
								</span>
							</button>
							<button
								type="button"
								onclick={() => (confirmingId = confirmingId === it.id ? null : it.id)}
								class="shrink-0 rounded-full p-2 text-error transition active:scale-90"
								aria-label="حذف التغيير"
							>
								<Icon name="delete" class="text-lg" />
							</button>
						</div>

						{#if expandedId === it.id}
							<div class="mx-2 mb-1 mt-0.5 space-y-1.5 rounded-2xl bg-surface-container-low p-3">
								{#if it.changes.length === 0}
									<p class="text-[11px] text-on-surface-variant/60">لا تفاصيل إضافية.</p>
								{:else}
									{#each it.changes as c (c.label)}
										<div class="flex items-center gap-2 text-[11px]">
											<span class="w-24 shrink-0 font-bold text-on-surface-variant/70"
												>{c.label}</span
											>
											<span class="min-w-0 flex-1 truncate text-on-surface-variant/50 line-through">
												{c.old}
											</span>
											<Icon name="arrow_back" class="shrink-0 text-[13px] text-primary" />
											<span class="min-w-0 flex-1 truncate font-bold text-emerald-700">{c.new}</span
											>
										</div>
									{/each}
								{/if}
							</div>
						{/if}

						{#if confirmingId === it.id}
							<div
								class="mx-2 mb-1.5 mt-0.5 flex items-center gap-2 rounded-2xl border border-error/20 bg-error/5 p-2.5"
							>
								<span class="flex-1 text-[11px] font-bold text-error">حذف هذا التغيير؟</span>
								<button
									type="button"
									onclick={() => doDiscard(it.id)}
									disabled={discarding}
									class="rounded-full bg-error px-3 py-1.5 text-[11px] font-bold text-on-error active:scale-95 disabled:opacity-60"
								>
									حذف
								</button>
								<button
									type="button"
									onclick={() => (confirmingId = null)}
									class="rounded-full bg-surface-container-high px-3 py-1.5 text-[11px] font-bold text-on-surface-variant active:scale-95"
								>
									إلغاء
								</button>
							</div>
						{/if}
					</li>
				{/each}
			</ul>

			{#if syncState.lastError}
				<p class="px-5 pt-2 text-[11px] font-medium text-error">{syncState.lastError}</p>
			{/if}

			<div class="px-5 pb-8 pt-3">
				{#if net.online}
					<button
						onclick={upload}
						disabled={syncState.syncing}
						class="flex w-full items-center justify-center gap-2 rounded-full bg-primary py-3.5 text-sm font-bold text-white shadow-fab transition active:scale-[0.98] disabled:opacity-70"
					>
						{#if syncState.syncing}
							<Icon name="progress_activity" class="animate-spin text-xl" /> جارٍ الرفع…
						{:else}
							<Icon name="cloud_upload" class="text-xl" /> رفع الآن
						{/if}
					</button>
				{:else}
					<div
						class="flex items-center justify-center gap-2 rounded-full bg-amber-100 py-3 text-[13px] font-bold text-amber-800"
					>
						<Icon name="wifi_off" class="text-lg" /> لا يوجد اتصال — سيُرفع عند عودة الشبكة
					</div>
				{/if}
			</div>
		{/if}
	</div>
{/if}
