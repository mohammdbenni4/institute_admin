<script lang="ts">
	// A small bottom-sheet confirmation. Used for the two nav actions that cannot be
	// undone: signing out (which wipes the offline cache) and closing the app.
	import type { Snippet } from 'svelte';
	import Icon from './Icon.svelte';

	let {
		open = $bindable(false),
		title,
		message,
		confirmLabel = 'تأكيد',
		cancelLabel = 'إلغاء',
		tone = 'primary',
		icon = 'warning',
		onConfirm,
		extra
	}: {
		open?: boolean;
		title: string;
		message: string;
		confirmLabel?: string;
		cancelLabel?: string;
		tone?: 'primary' | 'danger';
		icon?: string;
		onConfirm: () => void;
		/** Optional slot for a warning the caller wants to show above the buttons. */
		extra?: Snippet;
	} = $props();

	function confirm() {
		open = false;
		onConfirm();
	}
</script>

{#if open}
	<button
		type="button"
		onclick={() => (open = false)}
		class="fixed inset-0 z-[70] bg-black/40"
		aria-label="إلغاء"
	></button>
	<div
		class="fixed inset-x-0 bottom-0 z-[71] space-y-4 rounded-t-[2rem] bg-surface-container-lowest p-6 pb-10 shadow-2xl"
		dir="rtl"
		role="dialog"
		aria-modal="true"
	>
		<div class="flex items-start gap-3">
			<span
				class={'flex h-11 w-11 shrink-0 items-center justify-center rounded-full ' +
					(tone === 'danger' ? 'bg-error/10 text-error' : 'bg-primary/10 text-primary')}
			>
				<Icon name={icon} class="text-2xl" />
			</span>
			<div class="min-w-0 flex-1">
				<p class="text-[16px] font-bold text-on-surface">{title}</p>
				<p class="mt-1 text-[13px] leading-relaxed text-on-surface-variant/80">{message}</p>
			</div>
		</div>

		{#if extra}{@render extra()}{/if}

		<div class="flex gap-2 pt-1">
			<button
				type="button"
				onclick={() => (open = false)}
				class="flex-1 rounded-full bg-surface-container-high py-3 text-sm font-bold text-on-surface-variant active:scale-[0.98]"
			>
				{cancelLabel}
			</button>
			<button
				type="button"
				onclick={confirm}
				class={'flex-1 rounded-full py-3 text-sm font-bold text-white active:scale-[0.98] ' +
					(tone === 'danger' ? 'bg-error' : 'bg-brand')}
			>
				{confirmLabel}
			</button>
		</div>
	</div>
{/if}
