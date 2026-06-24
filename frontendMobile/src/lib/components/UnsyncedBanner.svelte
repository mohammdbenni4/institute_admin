<script lang="ts">
	import { net, syncNow, syncState } from '$lib/offline';
	import { arabicNum } from '$lib/utils';
	import Icon from './Icon.svelte';
</script>

{#if syncState.pending > 0}
	<div class="pointer-events-none fixed inset-x-0 bottom-24 z-40 flex justify-center px-4">
		<div
			class="pointer-events-auto flex items-center gap-2.5 rounded-full border border-amber-300/60 bg-amber-50 py-2 pe-2 ps-4 shadow-lg"
		>
			<Icon name={net.online ? 'cloud_off' : 'wifi_off'} class="text-lg text-amber-600" />
			<span class="text-[12px] font-bold text-amber-800">
				{arabicNum(syncState.pending)} تغييرات غير مرفوعة
			</span>
			{#if net.online}
				<button
					onclick={() => syncNow()}
					disabled={syncState.syncing}
					class="flex items-center gap-1 rounded-full bg-primary px-3 py-1.5 text-[11px] font-bold text-white transition active:scale-95 disabled:opacity-60"
				>
					{#if syncState.syncing}
						<Icon name="progress_activity" class="animate-spin text-sm" />
						جارٍ الرفع…
					{:else}
						<Icon name="cloud_upload" class="text-sm" /> رفع الآن
					{/if}
				</button>
			{:else}
				<span class="rounded-full bg-amber-200/70 px-2.5 py-1 text-[10px] font-bold text-amber-800">
					دون اتصال
				</span>
			{/if}
		</div>
	</div>
{/if}
