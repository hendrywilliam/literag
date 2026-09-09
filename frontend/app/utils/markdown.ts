import { fromMarkdown } from 'mdast-util-from-markdown'
import { gfm } from 'micromark-extension-gfm'
import { gfmFromMarkdown } from 'mdast-util-gfm'
import type {
  Blockquote,
  Code,
  Delete,
  Emphasis,
  Heading,
  Html,
  Image,
  InlineCode,
  Link,
  List,
  ListItem,
  Nodes,
  Paragraph,
  Root,
  Strong,
  Table,
  TableCell,
  TableRow,
  Text
} from 'mdast'
import { h, reactive, type VNode } from 'vue'
import { codeToTokens, type ThemedToken } from 'shiki'

const CODE_THEME = 'github-dark'

const parseCache = new Map<string, Root>()

export function parseMarkdown(markdown: string): Root {
  const cached = parseCache.get(markdown)
  if (cached) return cached

  const root = fromMarkdown(markdown, {
    extensions: [gfm()],
    mdastExtensions: [gfmFromMarkdown()]
  })

  if (parseCache.size > 500) parseCache.clear()
  parseCache.set(markdown, root)

  return root
}

const highlightCache = reactive(new Map<string, ThemedToken[][]>())
const highlightPending = new Set<string>()

function ensureHighlighted(code: string, lang: string | null | undefined) {
  const normalized = (lang || '').trim().toLowerCase()
  const key = `${normalized}\u0000${code}`

  if (highlightCache.has(key) || highlightPending.has(key)) return
  highlightPending.add(key)

  codeToTokens(code, {
    lang: (normalized || 'text') as NonNullable<Parameters<typeof codeToTokens>[1]>['lang'],
    theme: CODE_THEME
  })
    .then((result) => {
      highlightCache.set(key, result.tokens)
    })
    .catch(() => {
      highlightCache.set(key, [])
    })
    .finally(() => {
      highlightPending.delete(key)
    })
}

const FONT_STYLE_ITALIC = 1
const FONT_STYLE_BOLD = 2
const FONT_STYLE_UNDERLINE = 4

function tokenStyle(token: ThemedToken): Record<string, string> {
  const style: Record<string, string> = {}
  if (token.color) style.color = token.color
  if (token.bgColor) style['background-color'] = token.bgColor

  const fontStyle = token.fontStyle ?? 0
  if (fontStyle & FONT_STYLE_ITALIC) style['font-style'] = 'italic'
  if (fontStyle & FONT_STYLE_BOLD) style['font-weight'] = 'bold'
  if (fontStyle & FONT_STYLE_UNDERLINE) style['text-decoration'] = 'underline'

  return style
}

function renderCodeBlock(code: string, lang: string | null | undefined): VNode {
  const normalized = (lang || '').trim().toLowerCase()
  const key = `${normalized}\u0000${code}`

  ensureHighlighted(code, normalized)

  const tokens = highlightCache.get(key)

  let inner: VNode

  if (tokens && tokens.length > 0) {
    inner = h(
      'code',
      { class: 'block font-mono text-[13px] leading-relaxed' },
      tokens.map((line) =>
        h(
          'span',
          { class: 'block min-h-[1em]' },
          line.length > 0
            ? line.map((token) => h('span', { style: tokenStyle(token) }, token.content))
            : h('br')
        )
      )
    )
  } else {
    inner = h('code', { class: 'block font-mono text-[13px] leading-relaxed' }, code || ' ')
  }

  return h(
    'div',
    { class: 'group/code relative my-3 overflow-hidden rounded-lg border border-(--ui-border)' },
    [
      h(
        'div',
        { class: 'flex items-center justify-between border-b border-(--ui-border) bg-(--ui-bg-muted) px-3 py-1.5' },
        [
          h('span', { class: 'text-xs font-medium text-(--ui-text-muted)' }, normalized || 'text'),
          h(
            'button',
            {
              type: 'button',
              class:
                'text-xs text-(--ui-text-muted) transition-colors hover:text-(--ui-text)',
              onClick: (event: MouseEvent) => {
                void copyText(code, event)
              }
            },
            'Copy'
          )
        ]
      ),
      h('pre', { class: 'overflow-x-auto bg-[#0d1117] p-3 text-(--ui-text)' }, inner)
    ]
  )
}

async function copyText(text: string, event: MouseEvent) {
  const button = event.currentTarget as HTMLButtonElement
  try {
    await navigator.clipboard.writeText(text)
    const original = button.textContent
    button.textContent = 'Copied!'
    window.setTimeout(() => {
      button.textContent = original
    }, 1500)
  } catch {
    // ignore clipboard failures
  }
}

type MdChild = VNode | string

function renderChildren(children: Nodes[]): MdChild[] {
  const out: MdChild[] = []
  for (const child of children) {
    const rendered = renderNode(child)
    if (rendered == null) continue
    if (Array.isArray(rendered)) out.push(...rendered)
    else out.push(rendered)
  }
  return out
}

function renderNode(node: Nodes): MdChild | MdChild[] | null {
  switch (node.type) {
    case 'root': {
      const root = node as Root
      return renderChildren(root.children)
    }
    case 'paragraph': {
      const p = node as Paragraph
      return h('p', { class: 'my-1.5 leading-relaxed' }, renderChildren(p.children))
    }
    case 'heading': {
      const heading = node as Heading
      const tag = `h${Math.min(Math.max(heading.depth, 1), 6)}` as 'h1'
      const sizes: Record<string, string> = {
        h1: 'text-xl font-semibold mt-4 mb-2',
        h2: 'text-lg font-semibold mt-4 mb-2',
        h3: 'text-base font-semibold mt-3 mb-1.5',
        h4: 'text-sm font-semibold mt-3 mb-1',
        h5: 'text-sm font-medium mt-2 mb-1',
        h6: 'text-xs font-medium mt-2 mb-1'
      }
      return h(tag, { class: sizes[tag] }, renderChildren(heading.children))
    }
    case 'text': {
      const text = node as Text
      return text.value
    }
    case 'strong': {
      const strong = node as Strong
      return h('strong', { class: 'font-semibold' }, renderChildren(strong.children))
    }
    case 'emphasis': {
      const emphasis = node as Emphasis
      return h('em', { class: 'italic' }, renderChildren(emphasis.children))
    }
    case 'delete': {
      const del = node as Delete
      return h('del', { class: 'line-through' }, renderChildren(del.children))
    }
    case 'inlineCode': {
      const code = node as InlineCode
      return h(
        'code',
        { class: 'rounded bg-(--ui-bg-muted) px-1 py-0.5 font-mono text-[0.85em]' },
        code.value
      )
    }
    case 'code': {
      const code = node as Code
      return renderCodeBlock(code.value, code.lang)
    }
    case 'blockquote': {
      const blockquote = node as Blockquote
      return h(
        'blockquote',
        {
          class:
            'my-2 border-l-2 border-(--ui-border-strong) pl-3 text-(--ui-text-muted)'
        },
        renderChildren(blockquote.children)
      )
    }
    case 'list': {
      const list = node as List
      const ordered = list.ordered ?? false
      if (ordered) {
        return h(
          'ol',
          {
            class: 'my-2 list-decimal space-y-1 pl-5 marker:text-(--ui-text-muted)',
            start: list.start ?? 1
          },
          renderChildren(list.children)
        )
      }
      return h(
        'ul',
        { class: 'my-2 list-disc space-y-1 pl-5 marker:text-(--ui-text-muted)' },
        renderChildren(list.children)
      )
    }
    case 'listItem': {
      const item = node as ListItem
      return h('li', { class: 'pl-1' }, renderChildren(item.children))
    }
    case 'link': {
      const link = node as Link
      return h(
        'a',
        {
          href: link.url,
          target: '_blank',
          rel: 'noopener noreferrer',
          class: 'text-(--ui-primary) underline underline-offset-2'
        },
        renderChildren(link.children)
      )
    }
    case 'image': {
      const image = node as Image
      return h('img', {
        src: image.url,
        alt: image.alt || '',
        title: image.title || undefined,
        class: 'my-2 max-w-full rounded-lg',
        loading: 'lazy'
      })
    }
    case 'thematicBreak': {
      return h('hr', { class: 'my-4 border-(--ui-border)' })
    }
    case 'break': {
      return h('br')
    }
    case 'html': {
      const html = node as Html
      return h('span', { class: 'contents', innerHTML: html.value })
    }
    case 'table': {
      const table = node as Table
      const [head, ...body] = table.children as TableRow[]
      const columnAlign = (table.align ?? []) as Array<'left' | 'right' | 'center' | null>

      const renderRow = (row: TableRow, isHead: boolean): VNode => {
        const cells = row.children as TableCell[]
        return h(
          'tr',
          {},
          cells.map((cell, index) => {
            const align = columnAlign[index]
            const alignClass =
              align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left'
            const content = renderChildren(cell.children)
            return isHead
              ? h('th', { class: `px-3 py-2 font-semibold ${alignClass}` }, content)
              : h('td', { class: `px-3 py-2 ${alignClass}` }, content)
          })
        )
      }

      return h(
        'div',
        { class: 'my-3 overflow-x-auto rounded-lg border border-(--ui-border)' },
        h(
          'table',
          { class: 'w-full border-collapse text-sm' },
          [
            head ? h('thead', { class: 'border-b border-(--ui-border) bg-(--ui-bg-muted)' }, renderRow(head, true)) : null,
            body.length > 0 ? h('tbody', { class: 'divide-y divide-(--ui-border)' }, body.map((row) => renderRow(row, false))) : null
          ]
        )
      )
    }
    case 'definition':
    case 'footnoteDefinition':
      return null
    case 'footnoteReference': {
      return h(
        'sup',
        { class: 'text-xs text-(--ui-text-muted)' },
        `[${(node as { label?: string }).label ?? ''}]`
      )
    }
    case 'linkReference':
    case 'imageReference': {
      const ref = node as { alt?: string }
      return h('span', { class: 'text-(--ui-text-muted)' }, ref.alt ?? '')
    }
    default:
      return null
  }
}

export function renderMarkdown(markdown: string): MdChild[] {
  try {
    const root = parseMarkdown(markdown)
    const rendered = renderNode(root)
    return Array.isArray(rendered) ? rendered : rendered == null ? [] : [rendered]
  } catch {
    return [h('p', {}, markdown)]
  }
}
