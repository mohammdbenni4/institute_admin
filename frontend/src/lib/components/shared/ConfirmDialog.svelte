<script lang="ts">
	import Dialog from '$lib/components/ui/Dialog.svelte';
	import Button from '$lib/components/ui/Button.svelte';

	interface Props {
		open?: boolean;
		title?: string;
		message?: string;
		confirmLabel?: string;
		loading?: boolean;
		onConfirm: () => void;
		onCancel: () => void;
	}

	let {
		open = $bindable(false),
		title = 'تأكيد الحذف',
		message = 'هل أنت متأكد؟ لا يمكن التراجع عن هذا الإجراء.',
		confirmLabel = 'حذف',
		loading = false,
		onConfirm,
		onCancel
	}: Props = $props();
</script>

<Dialog bind:open {title} class="max-w-sm" onOpenChange={(o) => !o && onCancel()}>
	<p class="text-sm text-muted-foreground">{message}</p>
	<div class="mt-6 flex justify-start gap-2">
		<Button variant="destructive" onclick={onConfirm} disabled={loading}>
			{loading ? 'جارٍ الحذف…' : confirmLabel}
		</Button>
		<Button variant="outline" onclick={onCancel} disabled={loading}>إلغاء</Button>
	</div>
</Dialog>
