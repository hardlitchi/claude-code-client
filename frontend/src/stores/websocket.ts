import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useAuthStore } from './auth'

export interface WebSocketMessage {
  type: 'chat' | 'terminal' | 'system' | 'status' | 'error'
  data: any
  user_id?: string
  session_id?: string
  timestamp: string
}

export interface ChatMessage {
  id: string
  message: string
  sender: 'user' | 'claude'
  timestamp: string
  user_id?: string
  model?: string
}

export const useWebSocketStore = defineStore('websocket', () => {
  // State
  const socket = ref<WebSocket | null>(null)
  const isConnected = ref(false)
  const connectionId = ref<string | null>(null)
  const currentSessionId = ref<string | null>(null)
  const messages = ref<ChatMessage[]>([])
  const terminalOutput = ref<string[]>([])
  const reconnectAttempts = ref(0)
  const maxReconnectAttempts = 5

  // Getters
  const isSocketConnected = computed(() => isConnected.value && socket.value?.readyState === WebSocket.OPEN)
  const chatHistory = computed(() => messages.value.filter(msg => msg.sender))
  const lastMessage = computed(() => messages.value[messages.value.length - 1])

  // Actions
  const connect = async (sessionId: string) => {
    const authStore = useAuthStore()
    if (!authStore.token) {
      throw new Error('認証トークンが必要です')
    }

    try {
      disconnect() // 既存の接続をクリーンアップ
      
      const baseWsUrl = import.meta.env.VITE_WEBSOCKET_URL || 'ws://localhost:8000'
      const wsUrl = `${baseWsUrl}/api/ws/${sessionId}?token=${authStore.token}`
      socket.value = new WebSocket(wsUrl)
      currentSessionId.value = sessionId

      socket.value.onopen = () => {
        console.log('WebSocket接続が確立されました')
        isConnected.value = true
        reconnectAttempts.value = 0
      }

      socket.value.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          handleMessage(message)
        } catch (error) {
          console.error('メッセージ解析エラー:', error)
        }
      }

      socket.value.onclose = (event) => {
        console.log('WebSocket接続が閉じられました:', event.code, event.reason)
        isConnected.value = false
        connectionId.value = null
        
        // 自動再接続
        if (event.code !== 1000 && reconnectAttempts.value < maxReconnectAttempts) {
          setTimeout(() => {
            reconnectAttempts.value++
            connect(sessionId)
          }, 2000 * reconnectAttempts.value)
        }
      }

      socket.value.onerror = (error) => {
        console.error('WebSocketエラー:', error)
      }
    } catch (error) {
      console.error('WebSocket接続エラー:', error)
      throw error
    }
  }

  const disconnect = () => {
    if (socket.value) {
      socket.value.close(1000, '正常終了')
      socket.value = null
    }
    isConnected.value = false
    connectionId.value = null
    currentSessionId.value = null
  }

  const sendMessage = (type: WebSocketMessage['type'], data: any) => {
    if (!isSocketConnected.value) {
      throw new Error('WebSocket接続が確立されていません')
    }

    const message: Partial<WebSocketMessage> = {
      type,
      data,
      session_id: currentSessionId.value || undefined,
      timestamp: new Date().toISOString()
    }

    socket.value!.send(JSON.stringify(message))
  }

  const sendChatMessage = (message: string) => {
    sendMessage('chat', { message })
    
    // ユーザーメッセージを即座にUIに追加
    const chatMessage: ChatMessage = {
      id: Date.now().toString(),
      message,
      sender: 'user',
      timestamp: new Date().toISOString()
    }
    messages.value.push(chatMessage)
  }

  const sendTerminalCommand = (command: string) => {
    sendMessage('terminal', { command })
  }

  const handleMessage = (message: WebSocketMessage) => {
    console.log('受信メッセージ:', message)

    switch (message.type) {
      case 'chat':
        const chatMessage: ChatMessage = {
          id: Date.now().toString(),
          message: message.data.message,
          sender: message.data.sender,
          timestamp: message.timestamp,
          user_id: message.data.user_id,
          model: message.data.model
        }
        // ユーザーメッセージは既に追加済みなので、Claudeメッセージのみ追加
        if (chatMessage.sender === 'claude') {
          messages.value.push(chatMessage)
        }
        break

      case 'terminal':
        const output = `$ ${message.data.command}\n${message.data.output}`
        terminalOutput.value.push(output)
        break

      case 'system':
        if (message.data.connection_id) {
          connectionId.value = message.data.connection_id
        }
        console.log('システムメッセージ:', message.data.message)
        break

      case 'error':
        console.error('サーバーエラー:', message.data.error)
        // エラーメッセージをチャットに表示
        const errorMessage: ChatMessage = {
          id: Date.now().toString(),
          message: `エラー: ${message.data.error}`,
          sender: 'claude',
          timestamp: message.timestamp
        }
        messages.value.push(errorMessage)
        break

      default:
        console.warn('未処理のメッセージタイプ:', message.type)
    }
  }

  const clearMessages = () => {
    messages.value = []
  }

  const clearTerminalOutput = () => {
    terminalOutput.value = []
  }

  return {
    // State
    socket,
    isConnected,
    connectionId,
    currentSessionId,
    messages,
    terminalOutput,
    reconnectAttempts,
    
    // Getters
    isSocketConnected,
    chatHistory,
    lastMessage,
    
    // Actions
    connect,
    disconnect,
    sendMessage,
    sendChatMessage,
    sendTerminalCommand,
    clearMessages,
    clearTerminalOutput
  }
})
