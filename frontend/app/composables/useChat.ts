import { ref } from 'vue'

import { fetchData } from '../utils/fetch'

export interface ChatSource {
  chunk_id: string
  document_id: string
  source: string
  score: number
  text: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: ChatSource[]
}

const messages = ref<ChatMessage[]>([])
const pending = ref(false)
const error = ref<string | null>(null)
const controller = ref<AbortController | null>(null)

export function useChat() {
  function pushMessage(role: ChatMessage['role'], content: string): ChatMessage {
    const message: ChatMessage = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      role,
      content
    }
    messages.value.push(message)
    return message
  }

  function stop() {
    controller.value?.abort()
    controller.value = null
  }

  async function send(question: string, topK?: number) {
    const trimmed = question.trim()
    if (!trimmed || pending.value) return

    error.value = null
    pending.value = true

    pushMessage('user', trimmed)
    pushMessage('assistant', '')
    const assistant = messages.value[messages.value.length - 1]

    const abort = new AbortController()
    controller.value = abort

    let buffer = ''
    let flushTimer: ReturnType<typeof setTimeout> | null = null

    const flush = () => {
      if (buffer) {
        assistant.content += buffer
        buffer = ''
      }
      flushTimer = null
    }

    const scheduleFlush = () => {
      if (flushTimer) return
      flushTimer = setTimeout(flush, 50)
    }

    try {
      const response = await fetchData('/api/chat/completion', 0, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: trimmed, top_k: topK }),
        signal: abort.signal
      })

      if (!response.ok || !response.body) {
        throw new Error(`request failed: ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let rest = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        rest += decoder.decode(value, { stream: true })

        let newlineIndex: number
        while ((newlineIndex = rest.indexOf('\n')) !== -1) {
          const line = rest.slice(0, newlineIndex).trim()
          rest = rest.slice(newlineIndex + 1)

          if (!line.startsWith('data:')) continue
          const payload = line.slice(5).trim()
          if (!payload) continue
          if (payload === '[DONE]') continue

          let data: any
          try {
            data = JSON.parse(payload)
          } catch {
            continue
          }

          const delta: string | undefined = data?.choices?.[0]?.delta?.content
          if (typeof delta === 'string' && delta) {
            buffer += delta
            scheduleFlush()
          }

          if (data?.type === 'sources' && Array.isArray(data.sources)) {
            assistant.sources = data.sources
          }
        }
      }

      flush()
    } catch (err: any) {
      flush()
      if (err?.name !== 'AbortError') {
        error.value = err?.message || 'something went wrong'
      }
    } finally {
      flushTimer && clearTimeout(flushTimer)
      pending.value = false
      controller.value = null
      if (assistant.content === '' && error.value) {
        messages.value = messages.value.filter((m) => m.id !== assistant.id)
      }
    }
  }

  function clear() {
    stop()
    messages.value = []
    error.value = null
  }

  return { messages, pending, error, send, stop, clear }
}
