<script lang="ts">
	import { goto } from '$app/navigation';
	import Button from '$lib/components/ui/Button.svelte';
	import Input from '$lib/components/ui/Input.svelte';
	import Label from '$lib/components/ui/Label.svelte';
	import { ApiError } from '$lib/api';
	import { auth, isSuperAdmin, login, logout } from '$lib/api/auth.svelte';
	import { BookOpen, Lock, Mail } from '@lucide/svelte';

	let email = $state('');
	let password = $state('');
	let error = $state('');
	let submitting = $state(false);

	// Already signed in as a super admin? Skip the form.
	$effect(() => {
		if (auth.loaded && isSuperAdmin(auth.user)) goto('/admin');
	});

	async function handleLogin(event: SubmitEvent) {
		event.preventDefault();
		if (submitting) return;
		error = '';
		submitting = true;
		try {
			const user = await login(email, password);
			if (!isSuperAdmin(user)) {
				logout();
				error = 'هذه اللوحة مخصصة للمدير العام فقط.';
				return;
			}
			await goto('/admin');
		} catch (err) {
			error =
				err instanceof ApiError ? err.message : 'تعذّر تسجيل الدخول. تحقّق من الاتصال بالخادم.';
		} finally {
			submitting = false;
		}
	}
</script>

<div
	class="flex min-h-screen items-center justify-center bg-gradient-to-br from-background via-accent/30 to-background p-4"
>
	<div class="w-full max-w-md">
		<div class="mb-8 text-center">
			<div class="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
				<BookOpen class="h-8 w-8 text-primary" />
			</div>
			<h1 class="text-2xl font-bold text-foreground">نظام إدارة المعهد</h1>
			<p class="mt-1 text-sm text-muted-foreground">تسجيل دخول المدير العام</p>
		</div>

		<div class="glass-card space-y-5 p-6">
			<form onsubmit={handleLogin} class="space-y-4">
				<div class="space-y-2">
					<Label for="email">البريد الإلكتروني</Label>
					<div class="relative">
						<Mail class="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
						<Input
							id="email"
							type="email"
							bind:value={email}
							placeholder="example@institute.com"
							class="pr-9"
							required
						/>
					</div>
				</div>
				<div class="space-y-2">
					<Label for="password">كلمة المرور</Label>
					<div class="relative">
						<Lock class="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
						<Input
							id="password"
							type="password"
							bind:value={password}
							placeholder="••••••••"
							class="pr-9"
							required
						/>
					</div>
				</div>

				{#if error}
					<p class="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
				{/if}

				<Button type="submit" class="w-full" disabled={submitting}>
					{submitting ? 'جارٍ تسجيل الدخول…' : 'تسجيل الدخول'}
				</Button>
			</form>
		</div>
	</div>
</div>
