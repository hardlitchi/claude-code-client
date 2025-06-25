<template>
  <div class="process-output bg-white border rounded-lg">
    <!-- ヘッダー -->
    <div class="flex items-center justify-between p-3 border-b bg-gray-50">
      <div class="flex items-center space-x-3">
        <h4 class="font-medium text-gray-800">プロセス出力</h4>
        
        <!-- プロセス状態インジケーター -->
        <div class="flex items-center space-x-2">
          <div 
            v-if="buildProcess"
            class="flex items-center space-x-1 text-xs"
          >
            <div 
              class="w-2 h-2 rounded-full"
              :class="getBuildStatusColor(buildProcess.status)"
            ></div>
            <span>ビルド: {{ getBuildStatusText(buildProcess.status) }}</span>
            <span v-if="buildProcess.endTime" class="text-gray-500">
              ({{ projectStore.formatBuildDuration(buildProcess) }})
            </span>
          </div>
          
          <div 
            v-if="deployProcess"
            class="flex items-center space-x-1 text-xs"
          >
            <div 
              class="w-2 h-2 rounded-full"
              :class="getDeployStatusColor(deployProcess.status)"
            ></div>
            <span>デプロイ: {{ getDeployStatusText(deployProcess.status) }}</span>
            <span v-if="deployProcess.endTime" class="text-gray-500">
              ({{ projectStore.formatDeployDuration(deployProcess) }})
            </span>
          </div>
        </div>
      </div>
      
      <div class="flex items-center space-x-2">
        <!-- 自動スクロール切り替え -->
        <label class="flex items-center text-xs text-gray-600">
          <input
            v-model="autoScroll"
            type="checkbox"
            class="mr-1 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          自動スクロール
        </label>
        
        <!-- クリアボタン -->
        <button
          @click="clearOutput"
          class="text-xs text-gray-500 hover:text-gray-700 px-2 py-1 rounded"
          title="出力をクリア"
        >
          クリア
        </button>
        
        <!-- 閉じるボタン -->
        <button
          @click="$emit('close')"
          class="text-gray-500 hover:text-gray-700 p-1 rounded"
          title="閉じる"
        >
          <XMarkIcon class="w-4 h-4" />
        </button>
      </div>
    </div>
    
    <!-- 出力エリア -->
    <div class="output-container h-64 overflow-auto bg-gray-900 text-green-400 font-mono text-xs">
      <div ref="outputRef" class="p-3 space-y-1">
        <!-- ビルド出力 -->
        <div v-if="buildProcess?.output.length">
          <div class="text-yellow-400 font-bold mb-1">
            🔨 ビルド出力:
          </div>
          <div 
            v-for="(line, index) in buildProcess.output" 
            :key="`build-${index}`"
            class="whitespace-pre-wrap"
            :class="getLineClass(line)"
          >
            {{ line }}
          </div>
        </div>
        
        <!-- デプロイ出力 -->
        <div v-if="deployProcess?.output.length">
          <div class="text-blue-400 font-bold mb-1 mt-3">
            🚀 デプロイ出力:
          </div>
          <div 
            v-for="(line, index) in deployProcess.output" 
            :key="`deploy-${index}`"
            class="whitespace-pre-wrap"
            :class="getLineClass(line)"
          >
            {{ line }}
          </div>
        </div>
        
        <!-- 出力がない場合 -->
        <div v-if="!hasOutput" class="text-gray-500 text-center py-8">
          プロセス出力がまだありません
        </div>
      </div>
    </div>
    
    <!-- フッター（成功/失敗の詳細情報） -->
    <div v-if="showFooter" class="border-t bg-gray-50 p-3">
      <div class="flex items-center justify-between">
        <!-- 結果サマリー -->
        <div class="flex items-center space-x-4 text-sm">
          <div v-if="buildProcess?.endTime" class="flex items-center space-x-1">
            <component
              :is="buildProcess.success ? CheckCircleIcon : XCircleIcon"
              class="w-4 h-4"
              :class="buildProcess.success ? 'text-green-600' : 'text-red-600'"
            />
            <span>
              ビルド{{ buildProcess.success ? '成功' : '失敗' }}
              <span v-if="buildProcess.returnCode !== undefined" class="text-gray-500">
                (終了コード: {{ buildProcess.returnCode }})
              </span>
            </span>
          </div>
          
          <div v-if="deployProcess?.endTime" class="flex items-center space-x-1">
            <component
              :is="deployProcess.success ? CheckCircleIcon : XCircleIcon"
              class="w-4 h-4"
              :class="deployProcess.success ? 'text-green-600' : 'text-red-600'"
            />
            <span>
              デプロイ{{ deployProcess.success ? '成功' : '失敗' }}
            </span>
          </div>
        </div>
        
        <!-- アクセスURL -->
        <div v-if="deployProcess?.url" class="flex items-center space-x-2">
          <span class="text-sm text-gray-600">アクセスURL:</span>
          <a
            :href="deployProcess.url"
            target="_blank"
            class="text-blue-600 hover:text-blue-800 text-sm font-medium"
          >
            {{ deployProcess.url }}
          </a>
          <button
            @click="copyToClipboard(deployProcess.url)"
            class="text-gray-500 hover:text-gray-700 p-1"
            title="URLをコピー"
          >
            <ClipboardIcon class="w-3 h-3" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useProjectStore } from '@/stores/projects'
import {
  XMarkIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClipboardIcon
} from '@heroicons/vue/24/outline'

interface Props {
  buildProcess?: any
  deployProcess?: any
}

const props = defineProps<Props>()

const projectStore = useProjectStore()

const outputRef = ref<HTMLElement>()
const autoScroll = ref(true)

// 計算プロパティ
const hasOutput = computed(() => {
  return (props.buildProcess?.output.length > 0) || (props.deployProcess?.output.length > 0)
})

const showFooter = computed(() => {
  return props.buildProcess?.endTime || props.deployProcess?.endTime
})

// 出力が更新されたら自動スクロール
watch(
  [() => props.buildProcess?.output, () => props.deployProcess?.output],
  () => {
    if (autoScroll.value) {
      nextTick(() => {
        scrollToBottom()
      })
    }
  },
  { deep: true }
)

// メソッド
const scrollToBottom = () => {
  if (outputRef.value) {
    const container = outputRef.value.parentElement
    if (container) {
      container.scrollTop = container.scrollHeight
    }
  }
}

const getBuildStatusColor = (status: string) => {
  switch (status) {
    case 'running': return 'bg-yellow-500 animate-pulse'
    case 'completed': return 'bg-green-500'
    case 'error': return 'bg-red-500'
    default: return 'bg-gray-500'
  }
}

const getDeployStatusColor = (status: string) => {
  switch (status) {
    case 'running': return 'bg-blue-500 animate-pulse'
    case 'completed': return 'bg-green-500'
    case 'error': return 'bg-red-500'
    default: return 'bg-gray-500'
  }
}

const getBuildStatusText = (status: string) => {
  switch (status) {
    case 'running': return '実行中'
    case 'completed': return '完了'
    case 'error': return 'エラー'
    default: return '待機中'
  }
}

const getDeployStatusText = (status: string) => {
  switch (status) {
    case 'running': return '実行中'
    case 'completed': return '完了'
    case 'error': return 'エラー'
    default: return '待機中'
  }
}

const getLineClass = (line: string) => {
  // 出力行のスタイリング
  if (line.includes('✅') || line.includes('SUCCESS') || line.includes('successfully')) {
    return 'text-green-400'
  }
  if (line.includes('❌') || line.includes('ERROR') || line.includes('FAILED') || line.includes('failed')) {
    return 'text-red-400'
  }
  if (line.includes('⚠️') || line.includes('WARNING') || line.includes('warning')) {
    return 'text-yellow-400'
  }
  if (line.includes('🌐') || line.includes('http://') || line.includes('https://')) {
    return 'text-blue-400'
  }
  if (line.startsWith('npm ') || line.startsWith('pip ') || line.startsWith('docker ')) {
    return 'text-purple-400'
  }
  return 'text-green-400'
}

const clearOutput = () => {
  // プロセス出力をクリア（ストアから削除）
  if (props.buildProcess?.sessionId) {
    projectStore.clearBuildProcess(props.buildProcess.sessionId)
  }
  if (props.deployProcess?.sessionId) {
    projectStore.clearDeployProcess(props.deployProcess.sessionId)
  }
}

const copyToClipboard = async (text: string) => {
  try {
    await navigator.clipboard.writeText(text)
    // 簡単な成功フィードバック
    console.log('URLをクリップボードにコピーしました')
  } catch (error) {
    console.error('クリップボードへのコピーに失敗しました:', error)
  }
}

// エミット
defineEmits<{
  close: []
}>()
</script>

<style scoped>
.process-output {
  max-height: 500px;
}

.output-container {
  background-color: #1a202c;
}

.output-container::-webkit-scrollbar {
  width: 8px;
}

.output-container::-webkit-scrollbar-track {
  background: #2d3748;
}

.output-container::-webkit-scrollbar-thumb {
  background: #4a5568;
  border-radius: 4px;
}

.output-container::-webkit-scrollbar-thumb:hover {
  background: #718096;
}
</style>