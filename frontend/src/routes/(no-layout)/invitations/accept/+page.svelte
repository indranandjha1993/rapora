<script>
  let { data, form } = $props();
</script>

<svelte:head><title>Accept invitation | Rapora</title></svelte:head>

<div class="flex min-h-screen flex-col items-center justify-center bg-[color:var(--bg-app,#f7f7f8)] px-4">
  <div class="mb-8 flex items-center gap-2">
    <span class="text-2xl font-bold text-[color:var(--text-primary,#1f2937)]">Rapora</span>
  </div>

  <div class="w-full max-w-md rounded-2xl border border-black/5 bg-white p-8 shadow-sm">
    {#if data.error}
      <h1 class="text-center text-xl font-semibold text-[#1f2937]">Invitation problem</h1>
      <p class="mt-3 text-center text-sm text-gray-500">{data.error}</p>
      <a
        href="/login"
        class="mt-6 block w-full rounded-md bg-[#1f2937] py-3 text-center text-sm font-semibold text-white"
      >
        Go to sign in
      </a>
    {:else if data.invite}
      <h1 class="text-center text-xl font-semibold text-[#1f2937]">You're invited</h1>
      <p class="mt-3 text-center text-sm text-gray-600">
        You've been invited to join
        <strong class="text-[#1f2937]">{data.invite.org_name}</strong>
        as <strong class="text-[#1f2937]">{data.invite.role}</strong>.
      </p>
      <p class="mt-1 text-center text-xs text-gray-400">{data.invite.email}</p>

      {#if form?.error}
        <p class="mt-4 rounded-md bg-red-50 px-3 py-2 text-center text-sm text-red-600">
          {form.error}
        </p>
      {/if}

      <form method="POST" class="mt-6">
        <input type="hidden" name="token" value={data.token} />
        <button
          type="submit"
          class="w-full rounded-md bg-[#EA580C] py-3 text-sm font-semibold text-white transition hover:bg-[#c2410c]"
        >
          Accept invitation
        </button>
      </form>
      <a href="/login" class="mt-3 block text-center text-xs text-gray-400 hover:text-gray-600">
        Not now
      </a>
    {/if}
  </div>
</div>
