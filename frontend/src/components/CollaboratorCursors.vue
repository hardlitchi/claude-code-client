<template>
  <div class="collaborator-cursors absolute inset-0 pointer-events-none">
    <!-- 各協力者のカーソル -->
    <div
      v-for="cursor in visibleCursors"
      :key="cursor.userId"
      class="cursor-indicator absolute"
      :style="getCursorStyle(cursor)"
    >
      <!-- カーソルライン -->
      <div 
        class="cursor-line w-0.5 h-5"
        :style="{ backgroundColor: cursor.color }"
      ></div>
      
      <!-- ユーザー名バッジ -->
      <div 
        class="cursor-badge absolute top-0 left-1 px-2 py-1 text-xs text-white rounded shadow-lg whitespace-nowrap transform -translate-y-full pointer-events-auto"
        :style="{ backgroundColor: cursor.color }"
      >
        {{ cursor.username }}
      </div>
      
      <!-- 選択範囲ハイライト -->
      <div
        v-if="cursor.selection"
        class="selection-highlight absolute"
        :style="getSelectionStyle(cursor)"
      ></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useCollaborationStore } from '@/stores/collaboration'

interface Props {
  editorRef?: HTMLElement
  currentFilePath?: string
}

const props = defineProps<Props>()

const collaborationStore = useCollaborationStore()

// カーソル表示状態
const visibleCursors = ref<Array<{
  userId: number
  username: string
  line: number
  column: number
  color: string
  x: number
  y: number
  selection?: {
    startLine: number
    startColumn: number
    endLine: number
    endColumn: number
  }
}>>([])

// ユーザーごとの色
const userColors = [
  '#ef4444', // red-500
  '#3b82f6', // blue-500
  '#10b981', // emerald-500
  '#f59e0b', // amber-500
  '#8b5cf6', // violet-500
  '#ec4899', // pink-500
  '#06b6d4', // cyan-500
  '#84cc16'  // lime-500
]

const colorMap = new Map<number, string>()

// 計算プロパティ
const activeParticipants = computed(() => collaborationStore.activeParticipants)

// カーソル位置の更新を監視
watch(
  [activeParticipants, () => props.currentFilePath],
  () => {
    updateVisibleCursors()
  },
  { deep: true }
)

onMounted(() => {
  updateVisibleCursors()
  
  // エディターのスクロールイベントを監視
  if (props.editorRef) {
    props.editorRef.addEventListener('scroll', updateVisibleCursors)
  }
})

onBeforeUnmount(() => {
  if (props.editorRef) {
    props.editorRef.removeEventListener('scroll', updateVisibleCursors)
  }
})

// メソッド
const updateVisibleCursors = () => {
  if (!props.editorRef || !props.currentFilePath) {
    visibleCursors.value = []
    return
  }

  const cursors: typeof visibleCursors.value = []

  activeParticipants.value.forEach(participant => {
    const cursor = collaborationStore.getUserCursor(participant.user.id)
    
    if (!cursor || cursor.file_path !== props.currentFilePath) {
      return // 現在のファイル以外のカーソルは表示しない
    }

    // ユーザーに色を割り当て
    if (!colorMap.has(participant.user.id)) {
      const colorIndex = colorMap.size % userColors.length
      colorMap.set(participant.user.id, userColors[colorIndex])
    }

    const position = getPixelPosition(cursor.line, cursor.column)
    if (position) {
      cursors.push({
        userId: participant.user.id,
        username: participant.user.username,
        line: cursor.line,
        column: cursor.column,
        color: colorMap.get(participant.user.id)!,
        x: position.x,
        y: position.y,
        selection: cursor.selection
      })
    }
  })

  visibleCursors.value = cursors
}

const getPixelPosition = (line: number, column: number): { x: number; y: number } | null => {
  if (!props.editorRef) return null

  try {
    // Monaco Editor の場合の位置計算
    const lineHeight = 18 // デフォルトの行高さ
    const charWidth = 8   // デフォルトの文字幅
    
    // エディターのスクロール位置を考慮
    const scrollTop = props.editorRef.scrollTop || 0
    const scrollLeft = props.editorRef.scrollLeft || 0
    
    const x = (column - 1) * charWidth - scrollLeft
    const y = (line - 1) * lineHeight - scrollTop
    
    // エディター領域内に表示されているかチェック
    const editorRect = props.editorRef.getBoundingClientRect()
    if (y < 0 || y > editorRect.height || x < 0 || x > editorRect.width) {
      return null // 表示範囲外
    }
    
    return { x, y }
  } catch (error) {
    console.warn('カーソル位置計算エラー:', error)
    return null
  }
}

const getCursorStyle = (cursor: typeof visibleCursors.value[0]) => {
  return {
    left: `${cursor.x}px`,
    top: `${cursor.y}px`,
    zIndex: 1000
  }
}

const getSelectionStyle = (cursor: typeof visibleCursors.value[0]) => {
  if (!cursor.selection) return {}

  const startPos = getPixelPosition(cursor.selection.startLine, cursor.selection.startColumn)
  const endPos = getPixelPosition(cursor.selection.endLine, cursor.selection.endColumn)

  if (!startPos || !endPos) return {}

  // 選択範囲のハイライト表示
  const left = Math.min(startPos.x, endPos.x)
  const top = Math.min(startPos.y, endPos.y)
  const width = Math.abs(endPos.x - startPos.x)
  const height = Math.abs(endPos.y - startPos.y)

  return {
    left: `${left}px`,
    top: `${top}px`,
    width: `${width}px`,
    height: `${height}px`,
    backgroundColor: cursor.color,
    opacity: 0.3,
    zIndex: 999
  }
}

// 協力者のカーソル情報を外部から更新するメソッド
const updateCursor = (userId: number, line: number, column: number, selection?: any) => {
  const participant = activeParticipants.value.find(p => p.user.id === userId)
  if (participant) {
    // ストアのカーソル情報を更新
    collaborationStore.userCursors.set(userId, {
      file_path: props.currentFilePath,
      line,
      column,
      selection
    })
    
    updateVisibleCursors()
  }
}

// 外部公開メソッド
defineExpose({
  updateCursor,
  updateVisibleCursors
})
</script>

<style scoped>
.collaborator-cursors {
  pointer-events: none;
}

.cursor-indicator {
  transition: all 0.1s ease;
}

.cursor-line {
  animation: blink 1s infinite;
}

.cursor-badge {
  font-family: ui-monospace, 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace;
  font-size: 10px;
  transform: translateY(-100%);
  margin-top: -2px;
}

.selection-highlight {
  border-radius: 2px;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0.3; }
}

/* 画面サイズに応じたレスポンシブ調整 */
@media (max-width: 768px) {
  .cursor-badge {
    font-size: 8px;
    padding: 1px 4px;
  }
}
</style>