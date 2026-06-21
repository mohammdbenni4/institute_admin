<script lang="ts">
	import { page } from '$app/stores';
</script>

<div class="flex min-h-screen items-center justify-center bg-muted">
	<div class="text-center">
		<h1 class="mb-4 text-4xl font-bold">{$page.status}</h1>
		<p class="mb-4 text-xl text-muted-foreground">
			{$page.status === 404 ? 'عذراً! الصفحة غير موجودة' : 'حدث خطأ ما'}
		</p>
		<a href="/" class="text-primary underline hover:text-primary/90">العودة للرئيسية</a>
	</div>
</div>
