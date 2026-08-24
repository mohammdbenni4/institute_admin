<script lang="ts">
	import { goto } from '$app/navigation';
	import { ApiError, login } from '$lib/api';
	import { DEMO_EMAIL, DEMO_PASSWORD, MOCK_MODE } from '$lib/mock/config';
	import { resetMockData } from '$lib/mock/data';
	import Icon from '$lib/components/Icon.svelte';
	import Loader from '$lib/components/Loader.svelte';

	let email = $state(MOCK_MODE ? DEMO_EMAIL : '');
	let password = $state(MOCK_MODE ? DEMO_PASSWORD : '');
	let showPass = $state(false);
	let loading = $state(false);
	let error = $state('');
	let resetDone = $state(false);

	function resetDemoData() {
		resetMockData();
		resetDone = true;
		setTimeout(() => (resetDone = false), 2000);
	}

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		if (loading) return;
		error = '';
		loading = true;
		try {
			await login(email.trim(), password);
			goto('/halaqat', { replaceState: true });
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'تعذّر تسجيل الدخول';
		} finally {
			loading = false;
		}
	}
</script>

<div class="relative min-h-dvh overflow-hidden bg-surface">
	<div class="app-gradient absolute inset-x-0 top-0 h-72 rounded-b-[3rem]"></div>

	<main class="relative mx-auto flex min-h-dvh max-w-md flex-col justify-center px-6 py-10">
		<div class="mb-8 flex flex-col items-center gap-3 text-white">
			<div
				class="flex h-20 w-20 items-center justify-center rounded-[2rem] border border-white/20 bg-white/15 backdrop-blur-md"
			>
				<Icon name="menu_book" class="text-4xl" />
			</div>
			<h1 class="text-2xl font-bold">صرح القرآن</h1>
			<p class="text-sm font-light text-white/80">تطبيق المعلم</p>
		</div>

		<form
			onsubmit={submit}
			class="space-y-4 rounded-[2rem] border border-white/60 bg-surface-container-lowest p-6 shadow-card"
		>
			<h2 class="text-center text-lg font-bold text-on-surface">تسجيل الدخول</h2>

			{#if error}
				<div
					class="flex items-center gap-2 rounded-2xl bg-error-container px-4 py-3 text-sm text-on-error-container"
				>
					<Icon name="error" class="text-lg" />
					<span>{error}</span>
				</div>
			{/if}

			<label class="block space-y-1.5">
				<span class="pr-1 text-[13px] font-bold text-on-surface-variant">البريد الإلكتروني</span>
				<div class="flex items-center gap-2 rounded-full bg-surface-container-low px-4">
					<Icon name="mail" class="text-lg text-on-surface-variant/60" />
					<input
						bind:value={email}
						type="email"
						required
						autocomplete="username"
						inputmode="email"
						dir="ltr"
						class="w-full bg-transparent py-3 text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none"
						placeholder="teacher@example.com"
					/>
				</div>
			</label>

			<label class="block space-y-1.5">
				<span class="pr-1 text-[13px] font-bold text-on-surface-variant">كلمة المرور</span>
				<div class="flex items-center gap-2 rounded-full bg-surface-container-low px-4">
					<Icon name="lock" class="text-lg text-on-surface-variant/60" />
					<input
						bind:value={password}
						type={showPass ? 'text' : 'password'}
						required
						autocomplete="current-password"
						dir="ltr"
						class="w-full bg-transparent py-3 text-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none"
						placeholder="••••••••"
					/>
					<button
						type="button"
						onclick={() => (showPass = !showPass)}
						class="text-on-surface-variant/60"
						aria-label="إظهار كلمة المرور"
					>
						<Icon name={showPass ? 'visibility_off' : 'visibility'} class="text-lg" />
					</button>
				</div>
			</label>

			<button
				type="submit"
				disabled={loading}
				class="flex w-full items-center justify-center gap-2 rounded-full bg-brand py-3.5 text-sm font-bold text-white shadow-fab transition active:scale-[0.98] disabled:opacity-60"
			>
				{#if loading}
					<Loader class="text-xl" />
				{/if}
				دخول
			</button>
		</form>

		{#if MOCK_MODE}
			<div
				class="mt-6 space-y-2 rounded-2xl border border-amber-500/30 bg-amber-500/10 p-3 text-center"
			>
				<p class="text-[12px] font-bold text-amber-700">
					وضع البيانات التجريبية مفعّل — لا حاجة لخادم حقيقي
				</p>
				<p class="text-[11px] text-amber-700/80" dir="ltr">
					{DEMO_EMAIL} / {DEMO_PASSWORD}
				</p>
				<button
					type="button"
					onclick={resetDemoData}
					class="text-[11px] font-bold text-amber-700 underline underline-offset-2"
				>
					{resetDone ? 'تمت إعادة التعيين ✓' : 'إعادة تعيين البيانات التجريبية'}
				</button>
			</div>
		{/if}

		<p class="mt-6 text-center text-[11px] text-on-surface-variant/50">هذا التطبيق للمعلمين فقط</p>
	</main>
</div>
