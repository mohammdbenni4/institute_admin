<script lang="ts">
	import { LogOut, Menu, User } from '@lucide/svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Popover from '$lib/components/ui/Popover.svelte';
	import { logout } from '$lib/api/auth.svelte';
	import { goto } from '$app/navigation';

	interface Props {
		userName: string;
		roleName: string;
		onToggleSidebar?: () => void;
	}

	let { userName, roleName, onToggleSidebar }: Props = $props();

	function handleLogout() {
		logout();
		goto('/login');
	}
</script>

<header
	class="sticky top-0 z-30 flex h-14 items-center justify-between gap-3 border-b border-border bg-card px-4"
>
	<div class="flex items-center gap-3">
		<Button variant="ghost" size="icon" class="lg:hidden" onclick={onToggleSidebar}>
			<Menu class="h-5 w-5" />
		</Button>
	</div>

	<div class="flex items-center gap-2">
		<Popover align="end" class="w-48 p-1">
			{#snippet trigger({ toggle })}
				<Button variant="ghost" class="gap-2 px-2" onclick={toggle}>
					<div class="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10">
						<User class="h-4 w-4 text-primary" />
					</div>
					<div class="hidden text-right md:block">
						<p class="text-sm font-medium leading-none">{userName}</p>
						<p class="text-xs text-muted-foreground">{roleName}</p>
					</div>
				</Button>
			{/snippet}
			{#snippet children({ close })}
				<button
					type="button"
					onclick={() => {
						close();
						handleLogout();
					}}
					class="flex w-full items-center justify-end gap-2 rounded-md px-2 py-1.5 text-right text-sm text-destructive transition-colors hover:bg-accent"
				>
					<LogOut class="h-4 w-4" />
					تسجيل الخروج
				</button>
			{/snippet}
		</Popover>
	</div>
</header>
