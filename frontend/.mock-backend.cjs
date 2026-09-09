const http = require('http')
http.createServer((req, res) => {
  if (req.url === '/chat/completion' && req.method === 'POST') {
    let body = ''
    req.on('data', c => body += c)
    req.on('end', () => {
      res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive' })
      const chunks = [
        'Hello **bold** and *italic*!',
        '\n\n- item one\n- item two\n\n```js\nconst x = 1\n```',
        '\n\n| a | b |\n|---|---|\n| 1 | 2 |',
        '\n\nDone.'
      ]
      let i = 0
      const timer = setInterval(() => {
        if (i >= chunks.length) {
          clearInterval(timer)
          res.write('data: [DONE]\n\n')
          res.end()
          return
        }
        res.write(`data: ${JSON.stringify({ choices: [{ delta: { content: chunks[i] } }] })}\n\n`)
        i++
      }, 100)
    })
  } else {
    res.writeHead(404).end()
  }
}).listen(8080, () => console.log('mock backend on 8080'))
