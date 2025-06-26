<template>
  <div class="terminal-container h-full">
    <!-- ターミナルタイプ切り替えタブ（モバイル対応） -->
    <div class="terminal-tabs bg-gray-800 border-b border-gray-700">
      <div class="flex overflow-x-auto">
        <button
          v-for="tab in availableTabs"
          :key="tab.type"
          @click="switchTerminalType(tab.type)"
          :class="[
            'px-2 md:px-4 py-2 text-xs md:text-sm font-medium border-b-2 transition-colors whitespace-nowrap flex-shrink-0',
            currentTerminalType === tab.type
              ? 'text-green-400 border-green-400 bg-gray-700'
              : 'text-gray-300 border-transparent hover:text-white hover:border-gray-500'
          ]"
          :disabled="tab.disabled"
        >
          <div class="flex items-center space-x-1 md:space-x-2">
            <span :class="tab.icon" class="text-xs md:text-sm"></span>
            <span class="hidden sm:inline">{{ tab.label }}</span>
            <span class="sm:hidden">{{ tab.label.split('ターミナル')[0] }}</span>
            <span v-if="tab.badge" :class="tab.badgeClass">{{ tab.badge }}</span>
          </div>
        </button>
      </div>
    </div>
    
    <!-- ターミナル本体 -->
    <div class="h-full terminal-content">
      <!-- 基本ターミナル（フルワイズ） -->
      <div 
        v-show="currentTerminalType === 'basic'"
        class="h-full w-full flex"
      >
        <div 
          ref="basicTerminalElement" 
          class="h-full w-full"
        ></div>
      </div>
      
      <!-- Claude統合ターミナル（フルワイズ） -->
      <div 
        v-show="currentTerminalType === 'claude'"
        class="h-full w-full flex"
      >
        <div 
          ref="claudeTerminalElement" 
          class="h-full w-full"
        ></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'

interface Props {
  sessionId: string
  userSubscription?: any
  currentUser?: any
}

const props = defineProps<Props>()

// 各ターミナルタイプの要素参照
const basicTerminalElement = ref<HTMLElement>()
const claudeTerminalElement = ref<HTMLElement>()

// ターミナルタイプ管理
const currentTerminalType = ref<'basic' | 'claude'>('basic')

// 各ターミナルタイプの独立したインスタンス
interface TerminalInstance {
  terminal: Terminal | null
  fitAddon: FitAddon | null
  websocket: WebSocket | null
  isInitialized: boolean
}

const terminalInstances = ref<Record<'basic' | 'claude', TerminalInstance>>({
  basic: {
    terminal: null,
    fitAddon: null,
    websocket: null,
    isInitialized: false
  },
  claude: {
    terminal: null,
    fitAddon: null,
    websocket: null,
    isInitialized: false
  }
})

const emit = defineEmits<{
  connected: []
  disconnected: []
  error: [message: string]
}>()

// 利用可能なタブを計算
const availableTabs = computed(() => {
  // 管理者ユーザーまたは有料プランでClaude統合を有効化
  const isAdmin = props.currentUser?.is_admin === true
  const hasClaudeAccess = isAdmin || 
                         (props.userSubscription?.plan_type !== 'free' && 
                          props.userSubscription?.limits?.claude_sessions > 0)

  return [
    {
      type: 'basic',
      label: '基本ターミナル',
      icon: 'fas fa-terminal',
      disabled: false,
      badge: null,
      badgeClass: ''
    },
    {
      type: 'claude',
      label: 'Claude統合',
      icon: 'fas fa-robot',
      disabled: !hasClaudeAccess,
      badge: hasClaudeAccess ? (isAdmin ? 'Admin' : null) : 'Pro',
      badgeClass: hasClaudeAccess && isAdmin 
        ? 'ml-1 px-2 py-1 text-xs bg-red-600 text-white rounded'
        : 'ml-1 px-2 py-1 text-xs bg-blue-600 text-white rounded'
    }
  ]
})

const connectWebSocket = (type: 'basic' | 'claude', retryCount: number = 0) => {
  const instance = terminalInstances.value[type]
  const maxRetries = 3
  
  // 既存の接続があれば切断
  if (instance.websocket) {
    instance.websocket.close()
  }
  
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  let wsUrl: string
  
  // 環境変数による WebSocket URL のオーバーライド
  const customWsUrl = import.meta.env.VITE_WEBSOCKET_URL
  
  if (customWsUrl) {
    // カスタム WebSocket URL が設定されている場合
    wsUrl = `${customWsUrl}/api/terminal/ws/${props.sessionId}?terminal_type=${type}`
  } else if (process.env.NODE_ENV === 'development') {
    // 開発環境: 直接バックエンドに接続
    const host = window.location.hostname
    const port = '8000'
    wsUrl = `${protocol}//${host}:${port}/api/terminal/ws/${props.sessionId}?terminal_type=${type}`
  } else {
    // 本番環境: 現在のホストを使用（リバースプロキシ経由）
    const host = window.location.host
    wsUrl = `${protocol}//${host}/api/terminal/ws/${props.sessionId}?terminal_type=${type}`
  }
  
  console.log(`Attempting WebSocket connection to: ${wsUrl} (attempt ${retryCount + 1})`)
  instance.websocket = new WebSocket(wsUrl)
  
  // 接続タイムアウト設定
  const connectionTimeout = setTimeout(() => {
    if (instance.websocket && instance.websocket.readyState === WebSocket.CONNECTING) {
      console.warn(`WebSocket connection timeout for ${type}`)
      instance.websocket.close()
    }
  }, 10000) // 10秒タイムアウト
  
  instance.websocket.onopen = () => {
    clearTimeout(connectionTimeout)
    console.log(`Terminal WebSocket connected (${type})`)
    emit('connected')
  }
  
  instance.websocket.onmessage = (event) => {
    if (instance.terminal) {
      instance.terminal.write(event.data)
    }
  }
  
  instance.websocket.onclose = (event) => {
    clearTimeout(connectionTimeout)
    console.log(`Terminal WebSocket disconnected (${type}):`, event.code, event.reason)
    emit('disconnected')
    
    // 自動再接続（非正常終了の場合）
    if (event.code !== 1000 && retryCount < maxRetries) {
      console.log(`Retrying WebSocket connection in ${(retryCount + 1) * 2} seconds...`)
      setTimeout(() => {
        connectWebSocket(type, retryCount + 1)
      }, (retryCount + 1) * 2000) // 2秒、4秒、6秒で再試行
    }
  }
  
  instance.websocket.onerror = (error) => {
    clearTimeout(connectionTimeout)
    console.error(`Terminal WebSocket error (${type}):`, error)
    console.error(`Failed WebSocket URL: ${wsUrl}`)
    
    const errorMsg = retryCount >= maxRetries 
      ? `WebSocket接続エラー（最大再試行回数に達しました）: ${wsUrl}`
      : `WebSocket接続エラー: ${wsUrl}`
    emit('error', errorMsg)
  }
}

// ターミナルタイプ切り替え
const switchTerminalType = async (type: 'basic' | 'claude') => {
  if (type === currentTerminalType.value) return
  
  // Claudeターミナルへの切り替え時に権限をチェック
  if (type === 'claude') {
    const isAdmin = props.currentUser?.is_admin === true
    const hasAccess = isAdmin || 
                     (props.userSubscription?.plan_type !== 'free' && 
                      props.userSubscription?.limits?.claude_sessions > 0)
    if (!hasAccess) {
      emit('error', 'Claudeターミナルの利用にはProプラン以上のサブスクリプションが必要です')
      return
    }
  }
  
  // ターミナルタイプを変更
  currentTerminalType.value = type
  
  // 指定されたタイプのターミナルを初期化（未初期化の場合）
  if (!terminalInstances.value[type].isInitialized) {
    await initializeTerminal(type)
  }
  
  // WebSocket接続を確立
  connectWebSocket(type)
  
  // ターミナルサイズを調整（切り替え後に必要）
  await nextTick()
  setTimeout(() => {
    const instance = terminalInstances.value[type]
    if (instance.fitAddon && instance.terminal) {
      instance.fitAddon.fit()
    }
  }, 300)
}

const initializeTerminal = async (type: 'basic' | 'claude') => {
  const elementRef = type === 'basic' ? basicTerminalElement : claudeTerminalElement
  if (!elementRef.value) return
  
  const instance = terminalInstances.value[type]
  
  try {
    // xterm.js ターミナルの初期化
    instance.terminal = new Terminal({
      cursorBlink: true,
      cursorStyle: 'block',
      fontSize: 14,
      fontFamily: 'Monaco, Menlo, "DejaVu Sans Mono", monospace',
      theme: {
        background: type === 'basic' ? '#000000' : '#1a1a1a',
        foreground: '#ffffff',
        cursor: type === 'basic' ? '#ffffff' : '#00ff00'
      },
      allowProposedApi: true
    })
    
    instance.fitAddon = new FitAddon()
    instance.terminal.loadAddon(instance.fitAddon)
    
    instance.terminal.open(elementRef.value)
    instance.fitAddon.fit()
    
    // ターミナル入力を WebSocket に送信
    instance.terminal.onData((data) => {
      if (instance.websocket && instance.websocket.readyState === WebSocket.OPEN) {
        instance.websocket.send(data)
      }
    })
    
    // リサイズ処理
    const handleResize = () => {
      if (instance.fitAddon && instance.terminal) {
        // 少し遅延を入れてリサイズ処理を実行
        setTimeout(() => {
          instance.fitAddon?.fit()
        }, 100)
      }
    }
    
    window.addEventListener('resize', handleResize)
    
    // ターミナル切り替え時に適切にfitするように初期リサイズ
    setTimeout(() => {
      instance.fitAddon?.fit()
    }, 200)
    
    // 初期化完了フラグ
    instance.isInitialized = true
    
    console.log(`${type} terminal initialized for session: ${props.sessionId}`)
    
  } catch (error) {
    console.error(`${type} terminal initialization error:`, error)
    emit('error', `${type}ターミナルの初期化に失敗しました`)
  }
}

const cleanup = () => {
  // 全てのターミナルインスタンスをクリーンアップ
  Object.values(terminalInstances.value).forEach(instance => {
    if (instance.websocket) {
      instance.websocket.close()
      instance.websocket = null
    }
    
    if (instance.terminal) {
      instance.terminal.dispose()
      instance.terminal = null
    }
    
    instance.isInitialized = false
  })
}

onMounted(async () => {
  await nextTick()
  // 初期は基本ターミナルを初期化
  await initializeTerminal('basic')
  connectWebSocket('basic')
  
  // バーチャルキーボードイベントリスナー
  window.addEventListener('virtual-key', handleVirtualKey)
})

onUnmounted(() => {
  cleanup()
  // イベントリスナーのクリーンアップ
  window.removeEventListener('virtual-key', handleVirtualKey)
})

// バーチャルキーボード対応
const handleVirtualKey = (event: CustomEvent) => {
  const key = event.detail
  const currentInstance = terminalInstances.value[currentTerminalType.value]
  
  if (currentInstance.websocket && currentInstance.websocket.readyState === WebSocket.OPEN) {
    currentInstance.websocket.send(key)
  }
}

// 外部からアクセス可能なメソッド
defineExpose({
  focus: () => {
    const currentInstance = terminalInstances.value[currentTerminalType.value]
    if (currentInstance.terminal) {
      currentInstance.terminal.focus()
    }
  },
  
  clear: () => {
    const currentInstance = terminalInstances.value[currentTerminalType.value]
    if (currentInstance.terminal) {
      currentInstance.terminal.clear()
    }
  },
  
  reconnect: () => {
    const type = currentTerminalType.value
    const instance = terminalInstances.value[type]
    
    // 現在のインスタンスをクリーンアップ
    if (instance.websocket) {
      instance.websocket.close()
      instance.websocket = null
    }
    
    // 再接続
    setTimeout(() => {
      connectWebSocket(type)
    }, 1000)
  }
})
</script>

<style scoped>
.terminal-container {
  background: #000;
  position: relative;
  display: flex;
  flex-direction: column;
}

.terminal-content {
  flex: 1;
  min-height: 0; /* flexbox の高さ制限を解除 */
}

.terminal-tabs {
  flex-shrink: 0;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* xterm.js のスタイル */
:deep(.xterm) {
  height: 100% !important;
  flex: 1;
}

:deep(.xterm-viewport) {
  background-color: transparent !important;
}

:deep(.xterm-screen) {
  background-color: transparent !important;
}

/* モバイル対応 */
@media (max-width: 768px) {
  .terminal-tabs {
    padding: 0;
  }
  
  .terminal-tabs .flex {
    scrollbar-width: none;
    -ms-overflow-style: none;
  }
  
  .terminal-tabs .flex::-webkit-scrollbar {
    display: none;
  }
  
  :deep(.xterm) {
    font-size: 12px !important;
  }
  
  :deep(.xterm-viewport) {
    padding: 4px !important;
  }
}

/* タブの無効状態 */
button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

button:disabled:hover {
  color: inherit !important;
  border-color: transparent !important;
}
</style>