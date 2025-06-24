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
        <div ref="terminalContainer" class="flex-1 p-2">
          <!-- xterm.js がここにマウントされます -->
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
            v-for="message in chatHistory" 
            :key="message.id"
            :class="message.sender === 'user' ? 'text-right' : 'text-left'"
          >
            <div 
              :class="[
                'inline-block max-w-xs lg:max-w-md px-4 py-2 rounded-lg',
                message.sender === 'user' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-200 text-gray-800'
              ]"
            >
              <div class="text-sm">{{ message.content }}</div>
              <div class="text-xs opacity-75 mt-1">{{ message.timestamp }}</div>
            </div>
          </div>
          
          <div v-if="chatHistory.length === 0" class="text-center text-gray-500 py-8">
            Claudeとのチャットを開始してください
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
              :disabled="!newMessage.trim()"
              class="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 text-white px-4 py-2 rounded-md font-medium"
            >
              送信
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

const route = useRoute()
const router = useRouter()

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

const chatHistory = ref<ChatMessage[]>([
  {
    id: '1',
    sender: 'claude',
    content: 'こんにちは！Claude Code セッションへようこそ。何かお手伝いできることはありますか？',
    timestamp: '10:30'
  }
])

const newMessage = ref('')
const notificationsEnabled = ref(true)
const connectionStatus = ref<'connected' | 'disconnected'>('connected')
const sessionDuration = ref('2h 15m')

// Terminal関連
const terminalContainer = ref<HTMLElement>()

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

const sendMessage = () => {
  if (!newMessage.value.trim()) return

  const userMessage: ChatMessage = {
    id: Date.now().toString(),
    sender: 'user',
    content: newMessage.value,
    timestamp: new Date().toLocaleTimeString('ja-JP', { 
      hour: '2-digit', 
      minute: '2-digit' 
    })
  }

  chatHistory.value.push(userMessage)
  newMessage.value = ''

  // 仮のClaude返答
  setTimeout(() => {
    const claudeMessage: ChatMessage = {
      id: (Date.now() + 1).toString(),
      sender: 'claude',
      content: 'ご質問ありがとうございます。現在このメッセージは仮の応答です。実際のClaude Code統合は次のフェーズで実装予定です。',
      timestamp: new Date().toLocaleTimeString('ja-JP', { 
        hour: '2-digit', 
        minute: '2-digit' 
      })
    }
    chatHistory.value.push(claudeMessage)
  }, 1000)
}

const startResize = (e: MouseEvent) => {
  // TODO: 分割ペインのリサイズ実装
  console.log('リサイズ開始', e)
}

const initializeTerminal = async () => {
  // TODO: xterm.js の初期化
  // 現在は仮実装
  if (terminalContainer.value) {
    terminalContainer.value.innerHTML = `
      <div style="color: #00ff00; font-family: monospace; padding: 10px;">
        <div>$ cd /home/user/projectA</div>
        <div>$ ls -la</div>
        <div>total 24</div>
        <div>drwxr-xr-x  3 user  staff   96 Nov 24 10:30 .</div>
        <div>drwxr-xr-x  4 user  staff  128 Nov 24 10:30 ..</div>
        <div>-rw-r--r--  1 user  staff  120 Nov 24 10:30 README.md</div>
        <div>$ <span style="animation: blink 1s infinite;">■</span></div>
      </div>
    `
  }
}

// ライフサイクル
onMounted(async () => {
  await nextTick()
  initializeTerminal()
  
  // TODO: セッション情報の取得
  console.log('ワークスペース初期化:', route.params.sessionId)
})

onUnmounted(() => {
  // TODO: WebSocket接続の切断、リソースのクリーンアップ
  console.log('ワークスペース終了')
})
</script>

<style scoped>
@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
</style>