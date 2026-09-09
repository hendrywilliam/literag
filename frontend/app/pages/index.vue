<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'

const { messages, pending, error, send, stop, clear } = useChat()

const input = ref('')
const containerRef = ref<HTMLElement | null>(null)

const status = computed(() => (pending.value ? 'streaming' : error.value ? 'error' : 'ready'))

async function scrollToBottom() {
  await nextTick()
  const el = containerRef.value
  if (el) el.scrollTop = el.scrollHeight
}

watch(
  () => messages.value.map((m) => m.content).join(''),
  () => scrollToBottom()
)

function onSubmit() {
  const question = input.value
  if (!question.trim() || pending.value) return
  input.value = ''
  void send(question)
}

function onReload() {
  const last = [...messages.value].reverse().find((m) => m.role === 'user')
  if (!last) return
  messages.value = messages.value.filter((m) => m.id !== last.id)
  void send(last.content)
}
</script>

<template>
  <div class="flex h-dvh flex-col">
    <header class="flex items-center justify-between border-b border-(--ui-border) px-4 py-3">
      <div class="flex items-center gap-2">
        <UIcon name="i-lucide-bot" class="size-5 text-(--ui-primary)" />
        <h1 class="text-sm font-semibold">Literag Assistant</h1>
      </div>
      <UButton
        v-if="messages.length"
        icon="i-lucide-trash-2"
        size="sm"
        color="neutral"
        variant="ghost"
        aria-label="Clear conversation"
        @click="clear"
      />
    </header>

    <main
      ref="containerRef"
      class="flex-1 overflow-y-auto"
    >
      <div class="mx-auto flex max-w-3xl flex-col gap-4 px-4 py-6">
        <div
          v-if="!messages.length && !pending"
          class="flex flex-col items-center justify-center gap-3 py-16 text-center"
        >
          <UIcon name="i-lucide-sparkles" class="size-8 text-(--ui-primary)" />
          <p class="text-sm text-(--ui-text-muted)">
            Ask me anything. I'll answer based on the provided context.
          </p>
        </div>

        <template v-for="message in messages" :key="message.id">
          <UChatMessage
            :id="message.id"
            :role="message.role"
            :content="message.content"
            :parts="[]"
            :variant="message.role === 'user' ? 'soft' : 'naked'"
            :side="message.role === 'user' ? 'right' : 'left'"
            :avatar="message.role === 'assistant' ? { icon: 'i-lucide-bot' } : undefined"
          >
            <template v-if="message.role === 'assistant'" #content>
              <UChatShimmer
                v-if="pending && message.content === ''"
                text="Thinking"
                class="text-(--ui-text-muted)"
              />
              <template v-else>
                <ChatMarkdown :content="message.content" />
                <ChatSources v-if="message.sources?.length" :sources="message.sources" />
              </template>
            </template>
          </UChatMessage>
        </template>

        <div v-if="error" class="flex items-center gap-2 text-sm text-(--ui-error)">
          <UIcon name="i-lucide-alert-circle" class="size-4" />
          <span>{{ error }}</span>
        </div>
      </div>
    </main>

    <footer class="border-t border-(--ui-border) px-4 py-3">
      <div class="mx-auto max-w-3xl">
        <UChatPrompt
          v-model="input"
          :loading="pending"
          :disabled="pending"
          placeholder="Ask a question…"
          submit-on-enter
          autofocus
          @submit="onSubmit"
        >
          <template #footer>
            <UChatPromptSubmit
              :status="status"
              @stop="stop"
              @reload="onReload"
            />
          </template>
        </UChatPrompt>
        <p class="mt-1.5 text-center text-xs text-(--ui-text-muted)">
          Press Enter to send, Shift+Enter for a new line.
        </p>
      </div>
    </footer>
  </div>
</template>
