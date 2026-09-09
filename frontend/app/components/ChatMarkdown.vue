<script lang="ts">
import { defineComponent, h } from 'vue'
import { renderMarkdown } from '~/utils/markdown'

export default defineComponent({
  name: 'ChatMarkdown',
  props: {
    content: {
      type: String,
      required: true
    }
  },
  setup(props) {
    return () => h('div', { class: 'markdown-body text-[15px] text-(--ui-text)' }, renderMarkdown(props.content))
  }
})
</script>
