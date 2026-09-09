<script setup lang="ts">
import type { ChatSource } from '~/composables/useChat'

const props = defineProps<{ sources: ChatSource[] }>()

const expanded = ref<Set<string>>(new Set())

function key(source: ChatSource, index: number) {
  return source.chunk_id || `${source.document_id}:${index}`
}

function isExpanded(source: ChatSource, index: number) {
  return expanded.value.has(key(source, index))
}

function toggle(source: ChatSource, index: number) {
  const next = new Set(expanded.value)
  const k = key(source, index)
  if (next.has(k)) {
    next.delete(k)
  } else {
    next.add(k)
  }
  expanded.value = next
}

function basename(path: string) {
  return path.split('/').pop() || path
}
</script>

<template>
  <div v-if="props.sources.length" class="mt-3 space-y-2">
    <div class="flex items-center gap-1.5 text-xs font-medium text-(--ui-text-muted)">
      <UIcon name="i-lucide-book-open" class="size-3.5" />
      <span>Sources ({{ props.sources.length }})</span>
    </div>

    <div class="overflow-hidden divide-y divide-(--ui-border) rounded-lg border border-(--ui-border)">
      <div v-for="(source, index) in props.sources" :key="key(source, index)">
        <button
          type="button"
          class="flex w-full items-center justify-between gap-2 bg-(--ui-bg-muted) px-3 py-2 text-left transition-colors hover:bg-(--ui-bg)"
          @click="toggle(source, index)"
        >
          <span class="flex min-w-0 items-center gap-2">
            <span
              class="flex size-5 shrink-0 items-center justify-center rounded-full bg-(--ui-bg) text-[11px] font-semibold text-(--ui-text-muted)"
            >
              {{ index + 1 }}
            </span>
            <span class="truncate text-xs font-medium text-(--ui-text)">
              {{ basename(source.source) }}
            </span>
          </span>
          <UIcon
            :name="isExpanded(source, index) ? 'i-lucide-chevron-up' : 'i-lucide-chevron-down'"
            class="size-4 shrink-0 text-(--ui-text-muted)"
          />
        </button>

        <div v-if="isExpanded(source, index)" class="px-3 pb-3 pt-1">
          <p class="text-xs leading-relaxed text-(--ui-text-muted) whitespace-pre-wrap">
            {{ source.text }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
