<template>
  <div class="code-editor h-full flex flex-col">
    <!-- エディターヘッダー -->
    <div class="editor-header bg-gray-100 border-b p-3">
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-3">
          <h3 class="text-sm font-medium text-gray-700">
            {{ currentFile || '新しいファイル' }}
          </h3>
          <span v-if="isDirty" class="text-orange-500 text-xs">●</span>
          <span v-if="readonly" class="text-xs text-gray-500 bg-gray-200 px-2 py-1 rounded">
            読み取り専用
          </span>
        </div>
        
        <div class="flex items-center space-x-2">
          <!-- 言語選択 -->
          <select
            v-model="selectedLanguage"
            @change="changeLanguage"
            class="text-xs border border-gray-300 rounded px-2 py-1"
          >
            <option v-for="lang in supportedLanguages" :key="lang.id" :value="lang.id">
              {{ lang.name }}
            </option>
          </select>
          
          <!-- テーマ選択 -->
          <select
            v-model="selectedTheme"
            @change="changeTheme"
            class="text-xs border border-gray-300 rounded px-2 py-1"
          >
            <option value="vs">Light</option>
            <option value="vs-dark">Dark</option>
            <option value="hc-black">High Contrast</option>
          </select>
          
          <!-- 保存ボタン -->
          <button
            @click="saveFile"
            :disabled="!isDirty || readonly || saving"
            class="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {{ saving ? '保存中...' : '保存' }}
          </button>
          
          <!-- フォーマットボタン -->
          <button
            @click="formatCode"
            :disabled="readonly"
            class="px-3 py-1 text-xs bg-gray-600 text-white rounded hover:bg-gray-700 disabled:opacity-50"
          >
            フォーマット
          </button>
        </div>
      </div>
      
      <!-- ファイル情報 -->
      <div v-if="fileInfo" class="mt-2 text-xs text-gray-500">
        <span>サイズ: {{ formatFileSize(fileInfo.size) }}</span>
        <span class="mx-2">•</span>
        <span>最終更新: {{ formatDate(fileInfo.modified) }}</span>
        <span v-if="fileInfo.encoding" class="mx-2">•</span>
        <span v-if="fileInfo.encoding">エンコーディング: {{ fileInfo.encoding }}</span>
      </div>
    </div>
    
    <!-- Monaco Editor -->
    <div class="editor-container flex-1">
      <div ref="editorRef" class="w-full h-full"></div>
    </div>
    
    <!-- ステータスバー -->
    <div class="status-bar bg-gray-50 border-t px-3 py-1 text-xs text-gray-600">
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-4">
          <span>行 {{ cursorPosition.line }} 列 {{ cursorPosition.column }}</span>
          <span>{{ selectedLanguage }}</span>
          <span v-if="editorStats.characters">文字数: {{ editorStats.characters }}</span>
          <span v-if="editorStats.lines">行数: {{ editorStats.lines }}</span>
        </div>
        
        <div class="flex items-center space-x-4">
          <span v-if="isDirty" class="text-orange-600">未保存の変更があります</span>
          <span v-if="autoSave" class="text-green-600">自動保存: ON</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as monaco from 'monaco-editor'
import { useFileStore } from '@/stores/files'
import { useWebSocketStore } from '@/stores/websocket'

interface Props {
  sessionId: string
  filePath?: string
  readonly?: boolean
  autoSave?: boolean
  autoSaveInterval?: number
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false,
  autoSave: true,
  autoSaveInterval: 30000 // 30秒
})

const fileStore = useFileStore()
const websocketStore = useWebSocketStore()

const editorRef = ref<HTMLElement>()
let editor: monaco.editor.IStandaloneCodeEditor | null = null
let autoSaveTimer: number | null = null

const currentFile = ref('')
const isDirty = ref(false)
const saving = ref(false)
const selectedLanguage = ref('plaintext')
const selectedTheme = ref('vs')
const cursorPosition = ref({ line: 1, column: 1 })
const editorStats = ref({ characters: 0, lines: 0 })
const fileInfo = ref<any>(null)

// サポートされる言語リスト
const supportedLanguages = [
  { id: 'plaintext', name: 'Plain Text' },
  { id: 'javascript', name: 'JavaScript' },
  { id: 'typescript', name: 'TypeScript' },
  { id: 'python', name: 'Python' },
  { id: 'java', name: 'Java' },
  { id: 'cpp', name: 'C++' },
  { id: 'c', name: 'C' },
  { id: 'csharp', name: 'C#' },
  { id: 'go', name: 'Go' },
  { id: 'rust', name: 'Rust' },
  { id: 'php', name: 'PHP' },
  { id: 'ruby', name: 'Ruby' },
  { id: 'swift', name: 'Swift' },
  { id: 'kotlin', name: 'Kotlin' },
  { id: 'html', name: 'HTML' },
  { id: 'css', name: 'CSS' },
  { id: 'scss', name: 'SCSS' },
  { id: 'json', name: 'JSON' },
  { id: 'xml', name: 'XML' },
  { id: 'yaml', name: 'YAML' },
  { id: 'markdown', name: 'Markdown' },
  { id: 'shell', name: 'Shell' },
  { id: 'sql', name: 'SQL' },
  { id: 'dockerfile', name: 'Dockerfile' }
]

// ファイル拡張子から言語を推測
const getLanguageFromExtension = (filePath: string): string => {
  const extension = filePath.split('.').pop()?.toLowerCase()
  
  const extensionMap: Record<string, string> = {
    'js': 'javascript',
    'jsx': 'javascript',
    'ts': 'typescript',
    'tsx': 'typescript',
    'vue': 'vue',
    'py': 'python',
    'java': 'java',
    'cpp': 'cpp',
    'cc': 'cpp',
    'cxx': 'cpp',
    'c': 'c',
    'cs': 'csharp',
    'go': 'go',
    'rs': 'rust',
    'php': 'php',
    'rb': 'ruby',
    'swift': 'swift',
    'kt': 'kotlin',
    'html': 'html',
    'htm': 'html',
    'css': 'css',
    'scss': 'scss',
    'sass': 'scss',
    'json': 'json',
    'xml': 'xml',
    'yaml': 'yaml',
    'yml': 'yaml',
    'md': 'markdown',
    'sh': 'shell',
    'bash': 'shell',
    'zsh': 'shell',
    'sql': 'sql',
    'dockerfile': 'dockerfile'
  }
  
  return extensionMap[extension || ''] || 'plaintext'
}

// WebSocket メッセージ監視
watch(
  () => websocketStore.lastMessage,
  (message) => {
    if (message?.type === 'file_updated' && message.file_path === currentFile.value) {
      // 他のユーザーがファイルを更新した場合の通知
      if (confirm('このファイルが他のユーザーによって更新されました。再読み込みしますか？')) {
        loadFile(currentFile.value)
      }
    }
  }
)

// ファイルパスの変更を監視
watch(
  () => props.filePath,
  (newPath) => {
    if (newPath) {
      loadFile(newPath)
    }
  },
  { immediate: true }
)

onMounted(async () => {
  await initializeEditor()
  
  if (props.filePath) {
    await loadFile(props.filePath)
  }
  
  if (props.autoSave) {
    startAutoSave()
  }
})

onBeforeUnmount(() => {
  if (autoSaveTimer) {
    clearInterval(autoSaveTimer)
  }
  
  if (editor) {
    editor.dispose()
  }
})

// メソッド
const initializeEditor = async () => {
  if (!editorRef.value) return
  
  // Monaco Editor の初期化
  editor = monaco.editor.create(editorRef.value, {
    value: '',
    language: selectedLanguage.value,
    theme: selectedTheme.value,
    automaticLayout: true,
    fontSize: 14,
    lineNumbers: 'on',
    roundedSelection: false,
    scrollBeyondLastLine: false,
    readOnly: props.readonly,
    minimap: {
      enabled: true
    },
    scrollbar: {
      vertical: 'visible',
      horizontal: 'visible'
    },
    wordWrap: 'on',
    formatOnPaste: true,
    formatOnType: true
  })
  
  // エディターイベントリスナー
  editor.onDidChangeModelContent(() => {
    isDirty.value = true
    updateEditorStats()
  })
  
  editor.onDidChangeCursorPosition((e) => {
    cursorPosition.value = {
      line: e.position.lineNumber,
      column: e.position.column
    }
  })
  
  // キーボードショートカット
  editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
    saveFile()
  })
  
  editor.addCommand(monaco.KeyMod.Shift | monaco.KeyMod.Alt | monaco.KeyCode.KeyF, () => {
    formatCode()
  })
}

const loadFile = async (filePath: string) => {
  if (!editor) return
  
  try {
    const content = await fileStore.getFileContent(props.sessionId, filePath)
    
    if (content.type === 'binary') {
      alert('バイナリファイルは編集できません')
      return
    }
    
    editor.setValue(content.content)
    currentFile.value = filePath
    fileInfo.value = content
    isDirty.value = false
    
    // 言語の自動検出
    const detectedLanguage = getLanguageFromExtension(filePath)
    selectedLanguage.value = detectedLanguage
    changeLanguage()
    
    updateEditorStats()
    
  } catch (error: any) {
    alert(`ファイル読み込みエラー: ${error.message}`)
  }
}

const saveFile = async () => {
  if (!editor || !currentFile.value || !isDirty.value || props.readonly) return
  
  saving.value = true
  
  try {
    const content = editor.getValue()
    await fileStore.updateFileContent(
      props.sessionId,
      currentFile.value,
      content,
      fileInfo.value?.encoding || 'utf-8'
    )
    
    isDirty.value = false
    
    // WebSocket経由で保存通知
    const message = {
      type: 'file_saved',
      file_path: currentFile.value,
      timestamp: new Date().toISOString()
    }
    websocketStore.sendMessage(message)
    
  } catch (error: any) {
    alert(`保存エラー: ${error.message}`)
  } finally {
    saving.value = false
  }
}

const formatCode = async () => {
  if (!editor || props.readonly) return
  
  try {
    await editor.getAction('editor.action.formatDocument')?.run()
  } catch (error) {
    console.warn('フォーマット機能が利用できません:', error)
  }
}

const changeLanguage = () => {
  if (!editor) return
  
  const model = editor.getModel()
  if (model) {
    monaco.editor.setModelLanguage(model, selectedLanguage.value)
  }
}

const changeTheme = () => {
  monaco.editor.setTheme(selectedTheme.value)
}

const updateEditorStats = () => {
  if (!editor) return
  
  const model = editor.getModel()
  if (model) {
    editorStats.value = {
      characters: model.getValueLength(),
      lines: model.getLineCount()
    }
  }
}

const startAutoSave = () => {
  if (autoSaveTimer) {
    clearInterval(autoSaveTimer)
  }
  
  autoSaveTimer = setInterval(() => {
    if (isDirty.value && !props.readonly) {
      saveFile()
    }
  }, props.autoSaveInterval)
}

const formatFileSize = (bytes: number): string => {
  const sizes = ['B', 'KB', 'MB', 'GB']
  if (bytes === 0) return '0 B'
  
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  const size = bytes / Math.pow(1024, i)
  
  return `${size.toFixed(i === 0 ? 0 : 1)} ${sizes[i]}`
}

const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleString('ja-JP')
}

// エクスポート
defineExpose({
  loadFile,
  saveFile,
  formatCode,
  getValue: () => editor?.getValue() || '',
  setValue: (value: string) => editor?.setValue(value),
  focus: () => editor?.focus(),
  isDirty: () => isDirty.value
})
</script>

<style scoped>
.code-editor {
  @apply bg-white;
}

.editor-container {
  position: relative;
}

/* Monaco Editor のスタイル調整 */
:deep(.monaco-editor) {
  font-family: 'Fira Code', 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
}

:deep(.monaco-editor .margin) {
  background-color: #f8f9fa;
}

:deep(.monaco-editor .current-line) {
  border: none !important;
  background-color: rgba(0, 123, 255, 0.1) !important;
}
</style>