<template>
  <div class="h-screen bg-gray-50 flex flex-col">
    <!-- ヘッダー -->
    <header class="bg-white shadow-sm border-b flex-shrink-0">
      <div class="px-2 md:px-4 py-2 md:py-3 flex justify-between items-center">
        <div class="flex items-center space-x-1 md:space-x-4 min-w-0 flex-1">
          <button 
            @click="goBack"
            class="text-gray-500 hover:text-gray-700 p-1 md:p-0"
          >
            ← 戻る
          </button>
          <h1 class="text-sm md:text-lg font-semibold text-gray-900 truncate">
            📁 {{ sessionData.name || 'セッション' }}
          </h1>
          <span 
            :class="statusClasses[sessionData.status || 'stopped']" 
            class="text-xs md:text-sm font-medium whitespace-nowrap"
          >
            {{ sessionData.status === 'running' ? '🟢 実行中' : '⏸️ 停止中' }}
          </span>
        </div>
        
        <!-- デスクトップメニュー -->
        <div class="hidden md:flex items-center space-x-2">
          <button 
            @click="toggleNotifications"
            :class="notificationsEnabled ? 'text-blue-600' : 'text-gray-400'"
            class="p-2 rounded-md hover:bg-gray-100"
          >
            🔔
          </button>
          <button class="text-gray-500 hover:text-gray-700">最小化</button>
          <router-link to="/settings" class="text-gray-500 hover:text-gray-700">設定</router-link>
          <button 
            @click="goBack"
            class="text-gray-500 hover:text-gray-700"
          >
            終了
          </button>
        </div>
        
        <!-- モバイルメニューボタン -->
        <button
          @click="showMobileMenu = !showMobileMenu"
          class="md:hidden p-2 text-gray-500"
        >
          ⋮
        </button>
      </div>
      
      <!-- モバイルメニュー -->
      <div 
        v-if="showMobileMenu"
        class="md:hidden bg-white border-t border-gray-200 px-4 py-2 space-y-2"
      >
        <button 
          @click="toggleNotifications"
          :class="notificationsEnabled ? 'text-blue-600' : 'text-gray-400'"
          class="block w-full text-left py-2"
        >
          🔔 通知設定
        </button>
        <router-link 
          to="/settings" 
          class="block text-gray-500 py-2"
          @click="showMobileMenu = false"
        >
          ⚙️ 設定
        </router-link>
        <button 
          @click="goBack"
          class="block text-gray-500 py-2 w-full text-left"
        >
          🚪 終了
        </button>
      </div>
    </header>

    <!-- メインワークスペース -->
    <div class="flex-1 flex overflow-hidden">
      <!-- ターミナル側 -->
      <div class="flex-1 flex flex-col bg-black">
        <!-- ターミナルヘッダー（モバイル対応） -->
        <div class="bg-gray-800 px-2 md:px-4 py-2 text-white text-xs md:text-sm flex justify-between items-center">
          <span>Terminal</span>
          <!-- モバイル用キーボードボタン -->
          <button
            v-if="isMobile"
            @click="showVirtualKeyboard = !showVirtualKeyboard"
            class="md:hidden text-white bg-gray-700 px-2 py-1 rounded text-xs"
          >
            ⌨️ キーボード
          </button>
        </div>
        
        <div class="flex-1 relative">
          <Terminal 
            :sessionId="sessionData.id"
            :currentUser="currentUser"
            :userSubscription="userSubscription"
            @connected="onTerminalConnected"
            @disconnected="onTerminalDisconnected"
            @error="onTerminalError"
          />
          
          <!-- バーチャルキーボード（モバイル用） -->
          <div 
            v-if="showVirtualKeyboard && isMobile"
            class="absolute bottom-0 left-0 right-0 bg-gray-800 border-t border-gray-600 p-2 z-10"
          >
            <div class="grid grid-cols-4 gap-1 mb-2">
              <button
                v-for="key in virtualKeys.special"
                :key="key.label"
                @click="sendKey(key.value)"
                class="bg-gray-700 text-white text-xs py-2 px-1 rounded"
              >
                {{ key.label }}
              </button>
            </div>
            <div class="grid grid-cols-8 gap-1">
              <button
                v-for="key in virtualKeys.common"
                :key="key"
                @click="sendKey(key)"
                class="bg-gray-700 text-white text-xs py-2 px-1 rounded"
              >
                {{ key }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ステータスバー（モバイル対応） -->
    <footer class="bg-gray-800 text-white px-2 md:px-4 py-1 md:py-2 text-xs md:text-sm flex-shrink-0">
      <!-- デスクトップ表示 -->
      <div class="hidden md:flex justify-between items-center w-full">
        <div class="flex space-x-4">
          <span>📊 System: CPU 45% | Memory 62%</span>
          <span>Session: {{ sessionDuration }}</span>
        </div>
        <div class="flex space-x-2">
          <span :class="connectionStatus === 'connected' ? 'text-green-400' : 'text-red-400'">
            {{ connectionStatus === 'connected' ? '🟢 接続中' : '🔴 切断' }}
          </span>
        </div>
      </div>
      
      <!-- モバイル表示 -->
      <div class="md:hidden flex justify-between items-center w-full">
        <span>{{ sessionDuration }}</span>
        <span :class="connectionStatus === 'connected' ? 'text-green-400' : 'text-red-400'">
          {{ connectionStatus === 'connected' ? '🟢' : '🔴' }}
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
import { useSessionsStore } from '../stores/sessions'
import { useAuthStore } from '../stores/auth'
import axios from 'axios'

const route = useRoute()
const router = useRouter()
const claudeStore = useClaudeStore()
const authStore = useAuthStore()

// ユーザー・サブスクリプション情報
const currentUser = ref(null)
const userSubscription = ref(null)

// モバイル対応
const showMobileMenu = ref(false)
const showVirtualKeyboard = ref(false)
const isMobile = ref(false)

// バーチャルキーボード
const virtualKeys = {
  special: [
    { label: 'Tab', value: '\t' },
    { label: 'Esc', value: '\x1b' },
    { label: 'Ctrl+C', value: '\x03' },
    { label: 'Ctrl+D', value: '\x04' }
  ],
  common: ['ls', 'cd', 'pwd', 'clear', 'exit', 'mkdir', 'rm', 'cp']
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

// セッション詳細を取得する関数
const loadSessionData = async () => {
  try {
    const sessionsStore = useSessionsStore()
    const session = await sessionsStore.getSession(route.params.sessionId as string)
    sessionData.value.name = session.name
    sessionData.value.status = session.status
    sessionData.value.workingDirectory = session.working_directory
  } catch (error) {
    console.error('セッションデータ取得エラー:', error)
  }
}

// ユーザー・サブスクリプション情報を取得
const loadUserData = async () => {
  try {
    // 現在のユーザー情報を取得
    currentUser.value = authStore.user
    
    // サブスクリプション情報を取得
    const response = await axios.get('/api/subscriptions/current', {
      headers: {
        'Authorization': `Bearer ${authStore.token}`
      }
    })
    userSubscription.value = response.data
  } catch (error) {
    console.error('ユーザーデータ取得エラー:', error)
  }
}

// モバイル検出
const checkMobile = () => {
  isMobile.value = window.innerWidth < 768 || /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
}

// バーチャルキーボード機能
const sendKey = (key: string) => {
  // Terminal コンポーネントにキー送信
  // WebSocket経由でバックエンドに送信される
  const event = new CustomEvent('virtual-key', { detail: key })
  window.dispatchEvent(event)
}

// 画面向き変更対応
const handleResize = () => {
  checkMobile()
  // モバイルメニューを閉じる
  if (!isMobile.value) {
    showMobileMenu.value = false
    showVirtualKeyboard.value = false
  }
}
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
  
  // モバイル検出と初期化
  checkMobile()
  window.addEventListener('resize', handleResize)
  
  try {
    // セッションデータを読み込み
    await loadSessionData()
    
    // ユーザー・サブスクリプション情報を読み込み
    await loadUserData()
    
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
    // イベントリスナーのクリーンアップ
    window.removeEventListener('resize', handleResize)
    
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