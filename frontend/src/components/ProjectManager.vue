<template>
  <div class="project-manager h-full flex flex-col">
    <!-- ヘッダー -->
    <div class="project-header bg-gray-100 border-b p-3">
      <div class="flex items-center justify-between">
        <h3 class="text-sm font-medium text-gray-700">プロジェクト管理</h3>
        <div class="flex space-x-2">
          <button
            @click="refreshProjectStatus"
            :disabled="loading"
            class="text-gray-500 hover:text-gray-700 p-1 rounded disabled:opacity-50"
            title="状態更新"
          >
            <RefreshIcon class="w-4 h-4" />
          </button>
          <button
            @click="showCreateModal = true"
            class="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            新規プロジェクト
          </button>
        </div>
      </div>
    </div>

    <!-- プロジェクト状態表示 -->
    <div class="project-status flex-1 overflow-auto">
      <div v-if="loading" class="p-4 text-center text-gray-500">
        読み込み中...
      </div>
      
      <div v-else-if="!projectStore.isProjectDirectory(currentProject)" class="p-4">
        <div class="text-center text-gray-500 mb-4">
          <FolderIcon class="w-12 h-12 mx-auto mb-2 text-gray-300" />
          <p>プロジェクトが見つかりません</p>
          <p class="text-xs">テンプレートから新しいプロジェクトを作成してください</p>
        </div>
      </div>

      <div v-else class="p-4 space-y-4">
        <!-- プロジェクト情報 -->
        <div class="bg-white border rounded-lg p-4">
          <div class="flex items-center justify-between mb-3">
            <h4 class="font-medium text-gray-800">{{ currentProject.config?.name }}</h4>
            <span class="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
              {{ currentProject.config?.template }}
            </span>
          </div>
          
          <p v-if="currentProject.config?.description" class="text-sm text-gray-600 mb-3">
            {{ currentProject.config.description }}
          </p>
          
          <div class="grid grid-cols-2 gap-3 text-xs text-gray-500">
            <div>
              <span class="font-medium">作成者:</span> {{ currentProject.config?.created_by }}
            </div>
            <div>
              <span class="font-medium">作成日:</span> 
              {{ formatDate(currentProject.config?.created_at) }}
            </div>
          </div>
        </div>

        <!-- Docker状態 -->
        <div class="bg-white border rounded-lg p-4">
          <h4 class="font-medium text-gray-800 mb-3 flex items-center">
            <CubeIcon class="w-4 h-4 mr-2" />
            Docker状態
          </h4>
          
          <div class="flex items-center justify-between">
            <div class="flex items-center space-x-2">
              <div 
                class="w-2 h-2 rounded-full"
                :class="dockerStatus.running ? 'bg-green-500' : 'bg-gray-300'"
              ></div>
              <span class="text-sm">
                {{ dockerStatus.running ? '実行中' : '停止中' }}
              </span>
              <span v-if="dockerStatus.status" class="text-xs text-gray-500">
                ({{ dockerStatus.status }})
              </span>
            </div>
            
            <button
              v-if="dockerStatus.running"
              @click="stopContainer"
              class="px-3 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700"
            >
              停止
            </button>
          </div>
          
          <div v-if="dockerStatus.container_name" class="mt-2 text-xs text-gray-500">
            コンテナ名: {{ dockerStatus.container_name }}
          </div>
        </div>

        <!-- ビルド・デプロイ操作 -->
        <div class="bg-white border rounded-lg p-4">
          <h4 class="font-medium text-gray-800 mb-3 flex items-center">
            <WrenchScrewdriverIcon class="w-4 h-4 mr-2" />
            ビルド・デプロイ
          </h4>
          
          <div class="grid grid-cols-2 gap-3">
            <!-- ビルドボタン -->
            <button
              @click="buildProject"
              :disabled="projectStore.isBuilding"
              class="flex items-center justify-center px-3 py-2 text-sm bg-yellow-600 text-white rounded hover:bg-yellow-700 disabled:opacity-50"
            >
              <PlayIcon v-if="!projectStore.isBuilding" class="w-4 h-4 mr-1" />
              <ArrowPathIcon v-else class="w-4 h-4 mr-1 animate-spin" />
              {{ projectStore.isBuilding ? 'ビルド中...' : 'ビルド' }}
            </button>

            <!-- ローカルデプロイボタン -->
            <button
              @click="deployLocal"
              :disabled="projectStore.isDeploying"
              class="flex items-center justify-center px-3 py-2 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
            >
              <RocketLaunchIcon v-if="!projectStore.isDeploying" class="w-4 h-4 mr-1" />
              <ArrowPathIcon v-else class="w-4 h-4 mr-1 animate-spin" />
              ローカル実行
            </button>

            <!-- Dockerデプロイボタン -->
            <button
              @click="deployDocker"
              :disabled="projectStore.isDeploying"
              class="flex items-center justify-center px-3 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 col-span-2"
            >
              <CubeIcon v-if="!projectStore.isDeploying" class="w-4 h-4 mr-1" />
              <ArrowPathIcon v-else class="w-4 h-4 mr-1 animate-spin" />
              Dockerデプロイ
            </button>
          </div>
        </div>

        <!-- プロセス出力 -->
        <ProcessOutput
          v-if="showProcessOutput"
          :build-process="buildProcess"
          :deploy-process="deployProcess"
          @close="showProcessOutput = false"
        />
      </div>
    </div>

    <!-- プロジェクト作成モーダル -->
    <ProjectCreateModal
      v-if="showCreateModal"
      :session-id="sessionId"
      @close="showCreateModal = false"
      @created="onProjectCreated"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useProjectStore } from '@/stores/projects'
import { useWebSocketStore } from '@/stores/websocket'
import ProjectCreateModal from './ProjectCreateModal.vue'
import ProcessOutput from './ProcessOutput.vue'
import {
  RefreshIcon,
  FolderIcon,
  CubeIcon,
  WrenchScrewdriverIcon,
  PlayIcon,
  RocketLaunchIcon,
  ArrowPathIcon
} from '@heroicons/vue/24/outline'

interface Props {
  sessionId: string
  projectPath?: string
}

const props = defineProps<Props>()

const projectStore = useProjectStore()
const websocketStore = useWebSocketStore()

const loading = ref(false)
const showCreateModal = ref(false)
const showProcessOutput = ref(false)

// 計算プロパティ
const currentProject = computed(() => projectStore.currentProject)
const dockerStatus = computed(() => projectStore.getDockerStatus(currentProject.value))
const buildProcess = computed(() => projectStore.getBuildProcess(props.sessionId))
const deployProcess = computed(() => projectStore.getDeployProcess(props.sessionId))

// WebSocket メッセージ監視
watch(
  () => websocketStore.lastMessage,
  (message) => {
    if (message?.type?.startsWith('build_') || message?.type?.startsWith('deploy_')) {
      projectStore.handleWebSocketMessage(message)
      showProcessOutput.value = true
    } else if (message?.type === 'project_created') {
      projectStore.handleWebSocketMessage(message)
      refreshProjectStatus()
    }
  }
)

onMounted(() => {
  refreshProjectStatus()
})

// メソッド
const refreshProjectStatus = async () => {
  loading.value = true
  try {
    await projectStore.getProjectStatus(props.sessionId, props.projectPath)
  } catch (error: any) {
    console.error('プロジェクト状態取得エラー:', error)
  } finally {
    loading.value = false
  }
}

const buildProject = async () => {
  try {
    await projectStore.buildProject(props.sessionId, props.projectPath)
    showProcessOutput.value = true
  } catch (error: any) {
    alert(`ビルドエラー: ${error.message}`)
  }
}

const deployLocal = async () => {
  try {
    await projectStore.deployProject(props.sessionId, 'local', props.projectPath)
    showProcessOutput.value = true
  } catch (error: any) {
    alert(`デプロイエラー: ${error.message}`)
  }
}

const deployDocker = async () => {
  try {
    const config = { port: '8000' } // デフォルトポート
    await projectStore.deployProject(props.sessionId, 'docker', props.projectPath, {}, config)
    showProcessOutput.value = true
  } catch (error: any) {
    alert(`Dockerデプロイエラー: ${error.message}`)
  }
}

const stopContainer = async () => {
  if (!dockerStatus.value.container_name) return
  
  try {
    await projectStore.stopDockerContainer(dockerStatus.value.container_name)
    await refreshProjectStatus()
  } catch (error: any) {
    alert(`コンテナ停止エラー: ${error.message}`)
  }
}

const onProjectCreated = () => {
  showCreateModal.value = false
  refreshProjectStatus()
}

const formatDate = (dateString?: string): string => {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleString('ja-JP')
}
</script>

<style scoped>
.project-manager {
  @apply bg-gray-50;
}

.project-status {
  @apply bg-gray-50;
}
</style>