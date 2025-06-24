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
            <button class="text-gray-500 hover:text-gray-700">設定</button>
            <button class="text-gray-500 hover:text-gray-700">プロフィール</button>
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
              @click="createNewSession"
              class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium"
            >
              + 新しいセッション作成
            </button>
          </div>

          <div class="grid gap-4">
            <div 
              v-for="session in sessions" 
              :key="session.id"
              class="bg-white p-6 rounded-lg shadow border"
            >
              <div class="flex justify-between items-start">
                <div class="flex-1">
                  <div class="flex items-center space-x-2 mb-2">
                    <span class="text-lg">📁</span>
                    <h4 class="text-lg font-medium text-gray-900">{{ session.name }}</h4>
                    <span :class="statusClasses[session.status]">
                      {{ session.status === 'running' ? '🟢 実行中' : '⏸️ 停止中' }}
                    </span>
                  </div>
                  <p class="text-sm text-gray-600 mb-2">{{ session.path }}</p>
                  <p class="text-sm text-gray-500">最終更新: {{ session.lastUpdated }}</p>
                </div>
                <div class="flex space-x-2">
                  <button 
                    @click="openSession(session.id)"
                    class="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded text-sm"
                  >
                    開く
                  </button>
                  <button 
                    @click="deleteSession(session.id)"
                    class="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded text-sm"
                  >
                    削除
                  </button>
                </div>
              </div>
            </div>

            <div v-if="sessions.length === 0" class="text-center py-8 text-gray-500">
              アクティブなセッションがありません
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

interface Session {
  id: string
  name: string
  path: string
  status: 'running' | 'stopped'
  lastUpdated: string
}

const sessions = ref<Session[]>([
  {
    id: '1',
    name: 'プロジェクトA',
    path: '/home/user/projectA (main)',
    status: 'running',
    lastUpdated: '5分前'
  },
  {
    id: '2',
    name: 'ウェブアプリB',
    path: '/home/user/webapp (dev)',
    status: 'stopped',
    lastUpdated: '1時間前'
  }
])

const stats = ref({
  sessionCount: 2,
  totalTime: '12h',
  notifications: 8,
  lastLogin: '今日'
})

const statusClasses = {
  running: 'text-green-600',
  stopped: 'text-gray-500'
}

const createNewSession = () => {
  // TODO: 新しいセッション作成の実装
  console.log('新しいセッション作成')
}

const openSession = (sessionId: string) => {
  router.push(`/workspace/${sessionId}`)
}

const deleteSession = (sessionId: string) => {
  // TODO: セッション削除の実装
  sessions.value = sessions.value.filter(s => s.id !== sessionId)
}

const handleLogout = () => {
  router.push('/login')
}

onMounted(() => {
  // TODO: セッション一覧の取得
  console.log('ダッシュボード初期化')
})
</script>