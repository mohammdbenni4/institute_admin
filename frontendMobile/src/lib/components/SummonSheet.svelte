<script lang="ts">
	// Raise a «استدعاء ولي الأمر» for one student. The request is queued locally and
	// uploaded by the sync engine, so it works with no signal in the classroom.
	import { net, repo } from '$lib/offline';
	import Icon from './Icon.svelte';
	import Loader from './Loader.svelte';

	let {
		open = $bindable(false),
		studentId,
		studentName,
		halaqahId,
		onDone
	}: {
		open?: boolean;
		studentId: string;
		studentName: string;
		halaqahId: string;
		onDone?: (message: string) => void;
	} = $props();

	let reason = $state('');
	let saving = $state(false);
	let error = $state('');

	async function submit() {
		if (saving) return;
		if (!reason.trim()) {
			error = 'اكتب سبب الاستدعاء';
			return;
		}
		saving = true;
		error = '';
		try {
			await repo.requestParentSummon({
				student_id: studentId,
				student_name: studentName,
				halaqah_id: halaqahId,
				reason
			});
			open = false;
			reason = '';
			onDone?.(net.online ? 'تم إرسال طلب الاستدعاء' : 'حُفظ الطلب — سيُرسل عند توفر الاتصال');
		} catch {
			error = 'تعذّر حفظ الطلب';
		} finally {
			saving = false;
		}
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
		class="fixed inset-x-0 bottom-0 z-[71] space-y-4 rounded-t-[2rem] bg-surface-container-lowest p-5 pb-10 shadow-2xl"
		dir="rtl"
		role="dialog"
		aria-modal="true"
	>
		<div class="flex items-center gap-2">
			<Icon name="groups" class="text-2xl text-primary" />
			<div class="min-w-0 flex-1">
				<p class="text-[16px] font-bold text-on-surface">استدعاء ولي الأمر</p>
				<p class="truncate text-[12px] text-on-surface-variant/70">{studentName}</p>
			</div>
			<button
				type="button"
				onclick={() => (open = false)}
				class="rounded-full p-2 text-on-surface-variant active:scale-90"
				aria-label="إغلاق"
			>
				<Icon name="close" />
			</button>
		</div>

		<div class="space-y-1.5">
			<span class="pr-1 text-[13px] font-bold text-on-surface-variant">سبب الاستدعاء</span>
			<textarea
				bind:value={reason}
				rows="3"
				placeholder="مثال: تكرار الغياب وعدم إنجاز الواجب"
				class="w-full resize-none rounded-2xl bg-surface-container-low p-3.5 text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-2 focus:ring-primary/20"
			></textarea>
			{#if error}<p class="pr-1 text-[12px] font-bold text-error">{error}</p>{/if}
		</div>

		<p class="text-[11px] leading-relaxed text-on-surface-variant/60">
			يصل الطلب إلى إدارة المعهد، وتستطيع متابعة حالته من صفحة «استدعاء ولي أمر».
		</p>

		<button
			type="button"
			onclick={submit}
			disabled={saving}
			class="flex w-full items-center justify-center gap-2 rounded-full bg-brand py-3.5 text-sm font-bold text-white active:scale-[0.98] disabled:opacity-70"
		>
			{#if saving}<Loader class="text-lg" />{:else}<Icon name="mail" class="text-lg" />{/if}
			إرسال الطلب
		</button>
	</div>
{/if}
