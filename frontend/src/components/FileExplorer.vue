<template>
  <div class="file-explorer h-full flex flex-col">
    <!-- ヘッダー -->
    <div class="file-explorer-header bg-gray-100 p-3 border-b">
      <div class="flex items-center justify-between">
        <h3 class="text-sm font-medium text-gray-700">ファイルエクスプローラー</h3>
        <div class="flex space-x-2">
          <button
            @click="refreshFileTree"
            class="text-gray-500 hover:text-gray-700 p-1 rounded"
            title="更新"
          >
            <RefreshIcon class="w-4 h-4" />
          </button>
          <button
            @click="showCreateModal = true"
            class="text-gray-500 hover:text-gray-700 p-1 rounded"
            title="新規作成"
          >
            <PlusIcon class="w-4 h-4" />
          </button>
        </div>
      </div>
      
      <!-- パンくずリスト -->
      <div class="mt-2 text-xs text-gray-500">
        <span v-for="(part, index) in breadcrumbs" :key="index">
          <button
            @click="navigateToPath(getBreadcrumbPath(index))"
            class="hover:text-gray-700"
          >
            {{ part }}
          </button>
          <span v-if="index < breadcrumbs.length - 1" class="mx-1">/</span>
        </span>
      </div>
    </div>

    <!-- ファイルツリー -->
    <div class="file-tree flex-1 overflow-auto">
      <div v-if="loading" class="p-4 text-center text-gray-500">
        読み込み中...
      </div>
      <div v-else-if="error" class="p-4 text-center text-red-500">
        {{ error }}
      </div>
      <FileTreeNode
        v-else-if="fileTree"
        :node="fileTree"
        :level="0"
        :session-id="sessionId"
        @file-select="onFileSelect"
        @file-action="onFileAction"
      />
    </div>

    <!-- 新規作成モーダル -->
    <Modal v-if="showCreateModal" @close="showCreateModal = false">
      <template #header>
        <h3 class="text-lg font-medium">新規作成</h3>
      </template>
      <template #body>
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              種類
            </label>
            <select
              v-model="createForm.type"
              class="w-full p-2 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="file">ファイル</option>
              <option value="directory">ディレクトリ</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              名前
            </label>
            <input
              v-model="createForm.name"
              type="text"
              class="w-full p-2 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
              placeholder="ファイル名またはディレクトリ名"
              @keyup.enter="createFileOrDirectory"
            />
          </div>
        </div>
      </template>
      <template #footer>
        <div class="flex justify-end space-x-2">
          <button
            @click="showCreateModal = false"
            class="px-4 py-2 text-gray-600 hover:text-gray-800"
          >
            キャンセル
          </button>
          <button
            @click="createFileOrDirectory"
            :disabled="!createForm.name"
            class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            作成
          </button>
        </div>
      </template>
    </Modal>

    <!-- ファイルアップロードエリア -->
    <div
      class="upload-area border-t p-3"
      @drop="onDrop"
      @dragover.prevent
      @dragenter.prevent
    >
      <div class="text-xs text-gray-500 text-center">
        ファイルをドラッグ&ドロップ、または
        <label class="text-blue-600 hover:underline cursor-pointer">
          <input
            ref="fileInput"
            type="file"
            multiple
            class="hidden"
            @change="onFileSelect"
          />
          ここをクリック
        </label>
        してアップロード
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useFileStore } from '@/stores/files'
import { useWebSocketStore } from '@/stores/websocket'
import FileTreeNode from './FileTreeNode.vue'
import Modal from './Modal.vue'
import { RefreshIcon, PlusIcon } from '@heroicons/vue/24/outline'

interface Props {
  sessionId: string
}

const props = defineProps<Props>()

const fileStore = useFileStore()
const websocketStore = useWebSocketStore()

const currentPath = ref('')
const loading = ref(false)
const error = ref('')
const showCreateModal = ref(false)
const createForm = ref({
  type: 'file',
  name: ''
})

const fileInput = ref<HTMLInputElement>()

// 計算プロパティ
const fileTree = computed(() => fileStore.fileTree)
const breadcrumbs = computed(() => {
  if (!currentPath.value) return ['root']
  return ['root', ...currentPath.value.split('/').filter(Boolean)]
})

// WebSocket イベントリスナー
watch(
  () => websocketStore.lastMessage,
  (message) => {
    if (message && message.type?.startsWith('file_')) {
      // ファイル変更通知を受信した場合、ツリーを更新
      refreshFileTree()
    }
  }
)

onMounted(() => {
  loadFileTree()
  // ファイル監視を開始
  startFileWatching()
})

// メソッド
const loadFileTree = async () => {
  loading.value = true
  error.value = ''
  
  try {
    await fileStore.loadFileTree(props.sessionId, currentPath.value)
  } catch (err: any) {
    error.value = err.message || 'ファイルツリーの読み込みに失敗しました'
  } finally {
    loading.value = false
  }
}

const refreshFileTree = () => {
  loadFileTree()
}

const navigateToPath = (path: string) => {
  currentPath.value = path
  loadFileTree()
}

const getBreadcrumbPath = (index: number) => {
  if (index === 0) return ''
  return breadcrumbs.value.slice(1, index + 1).join('/')
}

const onFileSelect = (filePath: string) => {
  // ファイル選択イベントを親コンポーネントに伝播
  emit('file-select', filePath)
}

const onFileAction = (action: string, filePath: string) => {
  // ファイルアクション（削除、リネームなど）を処理
  switch (action) {
    case 'delete':
      deleteFile(filePath)
      break
    case 'download':
      downloadFile(filePath)
      break
  }
}

const createFileOrDirectory = async () => {
  if (!createForm.value.name) return
  
  try {
    const fullPath = currentPath.value
      ? `${currentPath.value}/${createForm.value.name}`
      : createForm.value.name
    
    await fileStore.createFileOrDirectory(
      props.sessionId,
      fullPath,
      createForm.value.type
    )
    
    showCreateModal.value = false
    createForm.value.name = ''
    refreshFileTree()
  } catch (err: any) {
    error.value = err.message || '作成に失敗しました'
  }
}

const deleteFile = async (filePath: string) => {
  if (!confirm('本当に削除しますか？')) return
  
  try {
    await fileStore.deleteFileOrDirectory(props.sessionId, filePath)
    refreshFileTree()
  } catch (err: any) {
    error.value = err.message || '削除に失敗しました'
  }
}

const downloadFile = (filePath: string) => {
  fileStore.downloadFile(props.sessionId, filePath)
}

const onDrop = (event: DragEvent) => {
  event.preventDefault()
  const files = event.dataTransfer?.files
  if (files) {
    uploadFiles(Array.from(files))
  }
}

const onFileSelectFromInput = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files) {
    uploadFiles(Array.from(target.files))
  }
}

const uploadFiles = async (files: File[]) => {
  for (const file of files) {
    try {
      await fileStore.uploadFile(props.sessionId, currentPath.value, file)
    } catch (err: any) {
      error.value = `${file.name}: ${err.message || 'アップロードに失敗しました'}`
    }
  }
  refreshFileTree()
  
  // ファイル入力をリセット
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

const startFileWatching = async () => {
  try {
    await fileStore.startFileWatching(props.sessionId)
  } catch (err: any) {
    console.warn('ファイル監視の開始に失敗:', err.message)
  }
}

// エミット
const emit = defineEmits<{
  'file-select': [filePath: string]
}>()
</script>

<style scoped>
.file-explorer {
  @apply bg-white border-r border-gray-200;
}

.upload-area {
  transition: background-color 0.2s;
}

.upload-area:hover {
  @apply bg-gray-50;
}

.upload-area.drag-over {
  @apply bg-blue-50 border-blue-300;
}
</style>