export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event)
  const backendUrl = (config.backendUrl as string).replace(/\/$/, '')

  const body = await readBody<{ question?: string; top_k?: number }>(event)

  if (!body?.question) {
    throw createError({ statusCode: 400, statusMessage: 'question is required' })
  }

  let upstream: Response
  try {
    upstream = await fetch(`${backendUrl}/chat/completion`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream'
      },
      body: JSON.stringify({ question: body.question, top_k: body.top_k })
    })
  } catch (err) {
    throw createError({
      statusCode: 502,
      statusMessage: 'backend unreachable',
      cause: err
    })
  }

  if (!upstream.ok || !upstream.body) {
    const text = await upstream.text().catch(() => '')
    throw createError({
      statusCode: upstream.status,
      statusMessage: `upstream error: ${upstream.status}`,
      data: text
    })
  }

  setResponseHeaders(event, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
    'X-Accel-Buffering': 'no'
  })

  const res = event.node.res
  const reader = upstream.body.getReader()
  const decoder = new TextDecoder()
  const encoder = new TextEncoder()

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const chunk = decoder.decode(value, { stream: true })
      res.write(encoder.encode(chunk))
    }
  } catch (err) {
    res.write(encoder.encode(`data: ${JSON.stringify({ error: 'stream interrupted' })}\n\n`))
  } finally {
    res.end()
  }
})
