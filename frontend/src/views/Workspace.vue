<template>
  <div class="h-screen bg-gray-50 flex flex-col">
    <!-- ヘッダー -->
    <header class="bg-white shadow-sm border-b flex-shrink-0">
      <div class="px-4 py-3 flex justify-between items-center">
        <div class="flex items-center space-x-4">
          <button 
            @click="goBack"
            class="text-gray-500 hover:text-gray-700"
          >
            ← 戻る
          </button>
          <h1 class="text-lg font-semibold text-gray-900">
            📁 {{ sessionData.name || 'セッション' }}
          </h1>
          <span 
            :class="statusClasses[sessionData.status || 'stopped']" 
            class="text-sm font-medium"
          >
            {{ sessionData.status === 'running' ? '🟢 実行中' : '⏸️ 停止中' }}
          </span>
        </div>
        <div class="flex items-center space-x-2">
          <button 
            @click="toggleNotifications"
            :class="notificationsEnabled ? 'text-blue-600' : 'text-gray-400'"
            class="p-2 rounded-md hover:bg-gray-100"
          >
            🔔
          </button>
          <button class="text-gray-500 hover:text-gray-700">最小化</button>
          <button class="text-gray-500 hover:text-gray-700">設定</button>
          <button 
            @click="goBack"
            class="text-gray-500 hover:text-gray-700"
          >
            終了
          </button>
        </div>
      </div>
    </header>

    <!-- メインワークスペース -->
    <div class="flex-1 flex overflow-hidden">
      <!-- ターミナル側 -->
      <div class="flex-1 flex flex-col bg-black">
        <div class="bg-gray-800 px-4 py-2 text-white text-sm">
          Terminal
        </div>
        <div class="flex-1">
          <Terminal 
            :session-id="sessionData.id"
            @connected="onTerminalConnected"
            @disconnected="onTerminalDisconnected"
            @error="onTerminalError"
          />
        </div>
      </div>

      <!-- 分割線 -->
      <div class="w-1 bg-gray-300 cursor-col-resize" @mousedown="startResize"></div>

      <!-- Claude Chat側 -->
      <div class="flex-1 flex flex-col bg-white">
        <div class="bg-gray-100 px-4 py-2 text-gray-800 text-sm border-b">
          Claude Chat
        </div>
        
        <!-- チャット履歴 -->
        <div class="flex-1 overflow-y-auto p-4 space-y-4">
          <div 
            v-for="(message, index) in claudeStore.messages" 
            :key="index"
            :class="message.sender === 'user' ? 'text-right' : 'text-left'"
          >
            <div 
              :class="[
                'inline-block max-w-xs lg:max-w-md px-4 py-2 rounded-lg',
                message.sender === 'user' 
                  ? 'bg-blue-600 text-white' 
                  : message.sender === 'claude'
                  ? 'bg-gray-200 text-gray-800'
                  : message.sender === 'system'
                  ? 'bg-green-100 text-green-800'
                  : 'bg-red-100 text-red-800'
              ]"
            >
              <div class="text-sm">{{ message.content }}</div>
              <div class="text-xs opacity-75 mt-1">
                {{ new Date(message.timestamp).toLocaleTimeString('ja-JP', { 
                  hour: '2-digit', 
                  minute: '2-digit' 
                }) }}
              </div>
            </div>
          </div>
          
          <div v-if="claudeStore.messages.length === 0" class="text-center text-gray-500 py-8">
            Claudeとのチャットを開始してください
          </div>
          
          <div v-if="claudeStore.isLoading" class="text-center text-gray-500">
            Claudeが応答中...
          </div>
        </div>

        <!-- メッセージ入力 -->
        <div class="border-t p-4">
          <div class="flex space-x-2">
            <input
              v-model="newMessage"
              @keyup.enter="sendMessage"
              type="text"
              placeholder="メッセージを入力..."
              class="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button 
              @click="sendMessage"
              :disabled="!newMessage.trim() || claudeStore.isLoading"
              class="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white px-4 py-2 rounded-md font-medium"
            >
              {{ claudeStore.isLoading ? '送信中...' : '送信' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ステータスバー -->
    <footer class="bg-gray-800 text-white px-4 py-2 text-sm flex justify-between items-center flex-shrink-0">
      <div class="flex space-x-4">
        <span>📊 System: CPU 45% | Memory 62%</span>
        <span>Session: {{ sessionDuration }}</span>
      </div>
      <div class="flex space-x-2">
        <span :class="connectionStatus === 'connected' ? 'text-green-400' : 'text-red-400'">
          {{ connectionStatus === 'connected' ? '🟢 接続中' : '🔴 切断' }}
        </span>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Terminal from '../components/Terminal.vue'
import { useClaudeStore } from '../stores/claude'

const route = useRoute()
const router = useRouter()
const claudeStore = useClaudeStore()

interface ChatMessage {
  id: string
  sender: 'user' | 'claude'
  content: string
  timestamp: string
}

interface SessionData {
  id: string
  name: string
  status: 'running' | 'stopped' | 'error'
  workingDirectory?: string
}

// リアクティブデータ
const sessionData = ref<SessionData>({
  id: route.params.sessionId as string,
  name: 'プロジェクトA',
  status: 'running'
})

const newMessage = ref('')
const notificationsEnabled = ref(true)
const connectionStatus = ref<'connected' | 'disconnected'>('connected')
const sessionDuration = ref('2h 15m')

// Terminal関連は Terminal.vue コンポーネントで管理

// スタイルクラス
const statusClasses = {
  running: 'text-green-600',
  stopped: 'text-gray-500',
  error: 'text-red-600'
}

// メソッド
const goBack = () => {
  router.push('/dashboard')
}

const toggleNotifications = () => {
  notificationsEnabled.value = !notificationsEnabled.value
}

const sendMessage = async () => {
  if (!newMessage.value.trim()) return

  const message = newMessage.value
  newMessage.value = ''

  try {
    await claudeStore.sendMessage(sessionData.value.id, message)
  } catch (error: any) {
    console.error('メッセージ送信エラー:', error)
    claudeStore.addLocalMessage('error', 'メッセージの送信に失敗しました')
  }
}

const startResize = (e: MouseEvent) => {
  // TODO: 分割ペインのリサイズ実装
  console.log('リサイズ開始', e)
}

// Terminal イベントハンドラー
const onTerminalConnected = () => {
  connectionStatus.value = 'connected'
  console.log('Terminal connected')
}

const onTerminalDisconnected = () => {
  connectionStatus.value = 'disconnected'
  console.log('Terminal disconnected')
}

const onTerminalError = (message: string) => {
  console.error('Terminal error:', message)
  // TODO: エラーメッセージを表示
}

// ライフサイクル
onMounted(async () => {
  await nextTick()
  
  try {
    // Claude セッションを開始
    await claudeStore.startSession(sessionData.value.id)
    
    // メッセージ履歴を取得
    await claudeStore.fetchMessages(sessionData.value.id)
    
    console.log('ワークスペース初期化完了:', route.params.sessionId)
  } catch (error) {
    console.error('ワークスペース初期化エラー:', error)
    claudeStore.addLocalMessage('error', 'Claudeセッションの開始に失敗しました')
  }
})

onUnmounted(async () => {
  try {
    // Claude セッションを停止
    await claudeStore.stopSession(sessionData.value.id)
  } catch (error) {
    console.error('Claude セッション停止エラー:', error)
  }
  
  console.log('ワークスペース終了')
})
</script>

<style scoped>
@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
</style>