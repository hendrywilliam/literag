<script setup lang="ts">
const { clear, messages } = useChat()
</script>

<template>
  <aside class="flex h-full w-60 shrink-0 flex-col border-r border-(--ui-border) bg-(--ui-bg-muted)">
    <div class="flex items-center gap-2 px-4 py-4">
      <UIcon name="i-lucide-book-open" class="size-5 text-(--ui-text-muted)" />
      <span class="text-sm font-semibold text-(--ui-text)">Literag</span>
    </div>

    <div class="px-3 pb-3">
      <UButton
        block
        color="primary"
        icon="i-lucide-plus"
        label="New chat"
        :disabled="!messages.length"
        @click="clear"
      />
    </div>

    <nav class="flex flex-1 flex-col gap-1 px-3">
      <UButton
        block
        color="neutral"
        variant="ghost"
        icon="i-lucide-message-square"
        label="Chat"
        class="justify-start"
        to="/"
      />
    </nav>

    <div class="px-4 py-3 text-xs text-(--ui-text-muted)">
      Retrieval-augmented assistant
    </div>
  </aside>
</template>
