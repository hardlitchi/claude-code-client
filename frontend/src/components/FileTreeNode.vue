<template>
  <div class="file-tree-node">
    <div
      class="file-item flex items-center py-1 px-2 hover:bg-gray-100 cursor-pointer"
      :style="{ paddingLeft: `${level * 16 + 8}px` }"
      @click="handleClick"
      @contextmenu.prevent="showContextMenu = true"
    >
      <!-- アイコン -->
      <div class="flex items-center space-x-2 flex-1">
        <component
          :is="getIcon()"
          class="w-4 h-4 flex-shrink-0"
          :class="getIconClass()"
        />
        <span class="text-sm truncate" :class="getTextClass()">
          {{ node.name }}
        </span>
        <span v-if="node.type === 'file' && node.size" class="text-xs text-gray-400 ml-auto">
          {{ formatFileSize(node.size) }}
        </span>
      </div>

      <!-- 展開/折りたたみボタン -->
      <button
        v-if="node.type === 'directory' && node.children?.length"
        @click.stop="toggleExpanded"
        class="p-1 hover:bg-gray-200 rounded"
      >
        <ChevronRightIcon
          class="w-3 h-3 transform transition-transform"
          :class="{ 'rotate-90': expanded }"
        />
      </button>
    </div>

    <!-- 子要素 -->
    <div v-if="expanded && node.children" class="children">
      <FileTreeNode
        v-for="child in sortedChildren"
        :key="child.name"
        :node="child"
        :level="level + 1"
        :session-id="sessionId"
        @file-select="$emit('file-select', $event)"
        @file-action="$emit('file-action', $event)"
      />
    </div>

    <!-- コンテキストメニュー -->
    <div
      v-if="showContextMenu"
      class="context-menu absolute bg-white border border-gray-200 rounded shadow-lg py-1 z-50"
      @click.stop
    >
      <button
        v-if="node.type === 'file'"
        @click="handleFileAction('open')"
        class="block w-full text-left px-3 py-1 text-sm hover:bg-gray-100"
      >
        開く
      </button>
      <button
        v-if="node.type === 'file'"
        @click="handleFileAction('download')"
        class="block w-full text-left px-3 py-1 text-sm hover:bg-gray-100"
      >
        ダウンロード
      </button>
      <button
        @click="handleFileAction('rename')"
        class="block w-full text-left px-3 py-1 text-sm hover:bg-gray-100"
      >
        名前変更
      </button>
      <button
        @click="handleFileAction('delete')"
        class="block w-full text-left px-3 py-1 text-sm hover:bg-gray-100 text-red-600"
      >
        削除
      </button>
    </div>

    <!-- オーバーレイ（コンテキストメニュー閉じる用） -->
    <div
      v-if="showContextMenu"
      class="fixed inset-0 z-40"
      @click="showContextMenu = false"
    ></div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  FolderIcon,
  FolderOpenIcon,
  DocumentIcon,
  DocumentTextIcon,
  PhotoIcon,
  FilmIcon,
  MusicalNoteIcon,
  ArchiveBoxIcon,
  CodeBracketIcon,
  ChevronRightIcon
} from '@heroicons/vue/24/outline'

interface FileNode {
  type: 'file' | 'directory' | 'error'
  name: string
  size?: number
  modified?: string
  extension?: string
  children?: FileNode[]
  truncated?: boolean
  error?: string
}

interface Props {
  node: FileNode
  level: number
  sessionId: string
}

const props = defineProps<Props>()

const expanded = ref(false)
const showContextMenu = ref(false)

// 計算プロパティ
const sortedChildren = computed(() => {
  if (!props.node.children) return []
  
  // ディレクトリを先に、その後ファイルをアルファベット順でソート
  return [...props.node.children].sort((a, b) => {
    if (a.type === 'directory' && b.type !== 'directory') return -1
    if (a.type !== 'directory' && b.type === 'directory') return 1
    return a.name.localeCompare(b.name)
  })
})

// メソッド
const handleClick = () => {
  if (props.node.type === 'directory') {
    toggleExpanded()
  } else if (props.node.type === 'file') {
    emit('file-select', getFullPath())
  }
}

const toggleExpanded = () => {
  expanded.value = !expanded.value
}

const handleFileAction = (action: string) => {
  showContextMenu.value = false
  
  if (action === 'open' && props.node.type === 'file') {
    emit('file-select', getFullPath())
  } else {
    emit('file-action', action, getFullPath())
  }
}

const getFullPath = (): string => {
  // ファイルの完全パスを構築（親からのパスを含む）
  // この実装では簡易的にファイル名のみを返すが、
  // 実際の実装では親パスを追跡する必要がある
  return props.node.name
}

const getIcon = () => {
  if (props.node.type === 'error') {
    return DocumentIcon
  }
  
  if (props.node.type === 'directory') {
    return expanded.value ? FolderOpenIcon : FolderIcon
  }
  
  // ファイルタイプ別のアイコン
  const extension = props.node.extension?.toLowerCase()
  
  if (!extension) return DocumentIcon
  
  // プログラミング言語
  const codeExtensions = ['.js', '.ts', '.jsx', '.tsx', '.vue', '.py', '.java', '.cpp', '.c', '.go', '.rs', '.php', '.rb', '.swift', '.kt']
  if (codeExtensions.includes(extension)) {
    return CodeBracketIcon
  }
  
  // テキストファイル
  const textExtensions = ['.txt', '.md', '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf']
  if (textExtensions.includes(extension)) {
    return DocumentTextIcon
  }
  
  // 画像ファイル
  const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico']
  if (imageExtensions.includes(extension)) {
    return PhotoIcon
  }
  
  // 動画ファイル
  const videoExtensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm']
  if (videoExtensions.includes(extension)) {
    return FilmIcon
  }
  
  // 音声ファイル
  const audioExtensions = ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma']
  if (audioExtensions.includes(extension)) {
    return MusicalNoteIcon
  }
  
  // アーカイブファイル
  const archiveExtensions = ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz']
  if (archiveExtensions.includes(extension)) {
    return ArchiveBoxIcon
  }
  
  return DocumentIcon
}

const getIconClass = () => {
  if (props.node.type === 'error') {
    return 'text-red-500'
  }
  
  if (props.node.type === 'directory') {
    return 'text-blue-500'
  }
  
  const extension = props.node.extension?.toLowerCase()
  
  // プログラミング言語
  const codeExtensions = ['.js', '.ts', '.jsx', '.tsx', '.vue', '.py', '.java', '.cpp', '.c', '.go', '.rs', '.php', '.rb', '.swift', '.kt']
  if (extension && codeExtensions.includes(extension)) {
    return 'text-green-600'
  }
  
  // 画像ファイル
  const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico']
  if (extension && imageExtensions.includes(extension)) {
    return 'text-purple-500'
  }
  
  // 動画・音声ファイル
  const mediaExtensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma']
  if (extension && mediaExtensions.includes(extension)) {
    return 'text-pink-500'
  }
  
  return 'text-gray-500'
}

const getTextClass = () => {
  if (props.node.type === 'error') {
    return 'text-red-500 italic'
  }
  
  if (props.node.type === 'directory') {
    return 'text-gray-800 font-medium'
  }
  
  return 'text-gray-700'
}

const formatFileSize = (bytes: number): string => {
  const sizes = ['B', 'KB', 'MB', 'GB']
  if (bytes === 0) return '0 B'
  
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  const size = bytes / Math.pow(1024, i)
  
  return `${size.toFixed(i === 0 ? 0 : 1)} ${sizes[i]}`
}

// エミット
const emit = defineEmits<{
  'file-select': [filePath: string]
  'file-action': [action: string, filePath: string]
}>()
</script>

<style scoped>
.file-tree-node {
  @apply relative;
}

.file-item {
  @apply select-none;
}

.context-menu {
  min-width: 150px;
}

.context-menu button {
  @apply w-full text-left;
}
</style>