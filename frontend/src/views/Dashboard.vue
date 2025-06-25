<template>
  <div class="min-h-screen bg-gray-50">
    <!-- ヘッダー -->
    <header class="bg-white shadow">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-16">
          <div class="flex items-center">
            <h1 class="text-xl font-semibold text-gray-900">
              Claude Code Client
            </h1>
          </div>
          <div class="flex items-center space-x-4">
            <router-link to="/settings" class="text-gray-500 hover:text-gray-700">設定</router-link>
            <router-link to="/profile" class="text-gray-500 hover:text-gray-700">プロフィール</router-link>
            <button class="text-gray-500 hover:text-gray-700" @click="handleLogout">
              ログアウト
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- メインコンテンツ -->
    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div class="px-4 py-6 sm:px-0">
        <div class="mb-6">
          <h2 class="text-2xl font-bold text-gray-900 mb-2">📊 ダッシュボード</h2>
        </div>

        <!-- アクティブセッション -->
        <div class="mb-8">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900">🚀 アクティブセッション</h3>
            <button 
              @click="showCreateModal = true"
              class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium"
            >
              + 新しいセッション作成
            </button>
          </div>

          <div class="grid gap-4">
            <div 
              v-for="session in sessionsStore.sessions" 
              :key="session.session_id"
              class="bg-white p-6 rounded-lg shadow border"
            >
              <div class="flex justify-between items-start">
                <div class="flex-1">
                  <div class="flex items-center space-x-2 mb-2">
                    <span class="text-lg">📁</span>
                    <h4 class="text-lg font-medium text-gray-900">{{ session.name }}</h4>
                    <span :class="statusClasses[session.status]">
                      {{ session.status === 'running' ? '🟢 実行中' : session.status === 'error' ? '⚠️ エラー' : '⏸️ 停止中' }}
                    </span>
                  </div>
                  <p class="text-sm text-gray-600 mb-2">{{ session.working_directory || '/home/user/project' }}</p>
                  <p class="text-sm text-gray-500">最終更新: {{ formatLastUpdated(session.last_accessed) }}</p>
                  <p v-if="session.description" class="text-sm text-gray-500">{{ session.description }}</p>
                </div>
                <div class="flex space-x-2">
                  <button 
                    @click="openSession(session.session_id)"
                    class="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded text-sm"
                  >
                    開く
                  </button>
                  <button 
                    @click="deleteSession(session.session_id)"
                    class="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded text-sm"
                  >
                    削除
                  </button>
                </div>
              </div>
            </div>

            <div v-if="sessionsStore.sessions.length === 0 && !sessionsStore.isLoading" class="text-center py-8 text-gray-500">
              アクティブなセッションがありません
            </div>
            
            <div v-if="sessionsStore.isLoading" class="text-center py-8 text-gray-500">
              読み込み中...
            </div>
          </div>
        </div>

        <!-- 使用統計 -->
        <div class="bg-white p-6 rounded-lg shadow border">
          <h3 class="text-lg font-medium text-gray-900 mb-4">📈 使用統計</h3>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div class="text-center">
              <div class="text-2xl font-bold text-blue-600">{{ stats.sessionCount }}</div>
              <div class="text-sm text-gray-600">セッション数</div>
            </div>
            <div class="text-center">
              <div class="text-2xl font-bold text-green-600">{{ stats.totalTime }}</div>
              <div class="text-sm text-gray-600">総使用時間</div>
            </div>
            <div class="text-center">
              <div class="text-2xl font-bold text-purple-600">{{ stats.notifications }}</div>
              <div class="text-sm text-gray-600">通知回数</div>
            </div>
            <div class="text-center">
              <div class="text-2xl font-bold text-gray-600">{{ stats.lastLogin }}</div>
              <div class="text-sm text-gray-600">最終ログイン</div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- セッション作成モーダル -->
    <div v-if="showCreateModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg p-6 w-full max-w-md">
        <h3 class="text-lg font-medium text-gray-900 mb-4">新しいセッション作成</h3>
        
        <form @submit.prevent="createNewSession" class="space-y-4">
          <div>
            <label for="sessionName" class="block text-sm font-medium text-gray-700 mb-1">
              セッション名 *
            </label>
            <input
              id="sessionName"
              v-model="newSessionName"
              type="text"
              required
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="例: プロジェクトA"
            />
          </div>
          
          <div>
            <label for="sessionDescription" class="block text-sm font-medium text-gray-700 mb-1">
              説明
            </label>
            <textarea
              id="sessionDescription"
              v-model="newSessionDescription"
              rows="3"
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="セッションの説明を入力してください"
            ></textarea>
          </div>
          
          <div>
            <label for="workingDirectory" class="block text-sm font-medium text-gray-700 mb-1">
              ワーキングディレクトリ
            </label>
            <div class="flex space-x-2">
              <input
                id="workingDirectory"
                v-model="newSessionWorkingDirectory"
                type="text"
                class="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                :placeholder="`例: /home/${authStore.user?.username}/my-project`"
              />
              <button
                type="button"
                @click="selectDirectory"
                class="px-3 py-2 bg-gray-100 border border-gray-300 rounded-md hover:bg-gray-200 text-sm"
              >
                📁 選択
              </button>
            </div>
            <p class="text-xs text-gray-500 mt-1">
              空白の場合は自動でディレクトリが作成されます
            </p>
          </div>
          
          <div class="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              @click="showCreateModal = false"
              class="px-4 py-2 text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300"
            >
              キャンセル
            </button>
            <button
              type="submit"
              :disabled="!newSessionName.trim() || sessionsStore.isLoading"
              class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {{ sessionsStore.isLoading ? '作成中...' : '作成' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useSessionsStore } from '../stores/sessions'

const router = useRouter()
const authStore = useAuthStore()
const sessionsStore = useSessionsStore()

// 新規セッション作成用
const showCreateModal = ref(false)
const newSessionName = ref('')
const newSessionDescription = ref('')
const newSessionWorkingDirectory = ref('')

// 計算されたプロパティ
const stats = computed(() => ({
  sessionCount: sessionsStore.sessions.length,
  totalTime: '12h', // TODO: 実際の使用時間計算
  notifications: 8, // TODO: 実際の通知数
  lastLogin: '今日'
}))

const statusClasses = {
  running: 'text-green-600',
  stopped: 'text-gray-500',
  error: 'text-red-600'
}

const formatLastUpdated = (dateString: string): string => {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / (1000 * 60))
  
  if (diffMins < 60) {
    return `${diffMins}分前`
  } else if (diffMins < 1440) {
    return `${Math.floor(diffMins / 60)}時間前`
  } else {
    return `${Math.floor(diffMins / 1440)}日前`
  }
}

const createNewSession = async () => {
  if (!newSessionName.value.trim()) return
  
  try {
    // ワーキングディレクトリの決定（ユーザー指定がない場合は自動生成）
    const workingDir = newSessionWorkingDirectory.value.trim() || 
      `/home/${authStore.user?.username}/${newSessionName.value.toLowerCase().replace(/\s+/g, '-')}`
    
    await sessionsStore.createSession({
      name: newSessionName.value,
      description: newSessionDescription.value || undefined,
      working_directory: workingDir
    })
    
    // フォームをリセット
    newSessionName.value = ''
    newSessionDescription.value = ''
    newSessionWorkingDirectory.value = ''
    showCreateModal.value = false
  } catch (error) {
    console.error('セッション作成エラー:', error)
    alert('セッションの作成に失敗しました')
  }
}

const openSession = (sessionId: string) => {
  router.push(`/workspace/${sessionId}`)
}

const deleteSession = async (sessionId: string) => {
  if (!confirm('このセッションを削除しますか？')) return
  
  try {
    await sessionsStore.deleteSession(sessionId)
  } catch (error) {
    console.error('セッション削除エラー:', error)
    alert('セッションの削除に失敗しました')
  }
}

// ディレクトリ選択機能
const selectDirectory = () => {
  // TODO: ファイルシステムブラウザーやネイティブディレクトリ選択機能の実装
  // 現在は簡易的なプロンプトで対応
  const selectedPath = prompt(
    'ワーキングディレクトリのパスを入力してください',
    newSessionWorkingDirectory.value || `/home/${authStore.user?.username}/`
  )
  
  if (selectedPath !== null) {
    newSessionWorkingDirectory.value = selectedPath
  }
}

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}

onMounted(async () => {
  try {
    await sessionsStore.fetchSessions()
  } catch (error) {
    console.error('セッション一覧取得エラー:', error)
  }
})
</script>