import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'
import { useAuthStore } from './auth'

interface ClaudeMessage {
  sender: 'user' | 'claude' | 'system' | 'error'
  content: string
  timestamp: string
}

interface ClaudeSessionStatus {
  session_id: string
  is_active: boolean
  message_count: number
  created_at?: string
  working_directory?: string
}

export const useClaudeStore = defineStore('claude', () => {
  // State
  const messages = ref<ClaudeMessage[]>([])
  const sessionStatus = ref<ClaudeSessionStatus | null>(null)
  const isLoading = ref(false)
  const isConnected = ref(false)

  // API クライアント
  const apiClient = axios.create({
    baseURL: '/api'
  })

  // リクエストインターセプター（認証トークンを動的に取得）
  apiClient.interceptors.request.use((config) => {
    const authStore = useAuthStore()
    if (authStore.token) {
      config.headers.Authorization = `Bearer ${authStore.token}`
    }
    return config
  })

  // レスポンスインターセプター（認証エラー処理）
  apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        const authStore = useAuthStore()
        authStore.logout()
      }
      return Promise.reject(error)
    }
  )

  // Actions
  const startSession = async (sessionId: string): Promise<void> => {
    isLoading.value = true
    try {
      await apiClient.post(`/claude/sessions/${sessionId}/start`)
      await fetchSessionStatus(sessionId)
      isConnected.value = true
    } catch (error) {
      console.error('Claude セッション開始エラー:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  const stopSession = async (sessionId: string): Promise<void> => {
    isLoading.value = true
    try {
      await apiClient.post(`/claude/sessions/${sessionId}/stop`)
      isConnected.value = false
      sessionStatus.value = null
    } catch (error) {
      console.error('Claude セッション停止エラー:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  const sendMessage = async (sessionId: string, message: string): Promise<string> => {
    isLoading.value = true
    try {
      const response = await apiClient.post(`/claude/sessions/${sessionId}/message`, {
        message
      })
      
      // メッセージ履歴を更新
      await fetchMessages(sessionId)
      
      return response.data.claude_response
    } catch (error) {
      console.error('Claude メッセージ送信エラー:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  const fetchMessages = async (sessionId: string): Promise<void> => {
    try {
      const response = await apiClient.get(`/claude/sessions/${sessionId}/messages`)
      messages.value = response.data.messages
    } catch (error) {
      console.error('Claude メッセージ履歴取得エラー:', error)
      throw error
    }
  }

  const fetchSessionStatus = async (sessionId: string): Promise<void> => {
    try {
      const response = await apiClient.get(`/claude/sessions/${sessionId}/status`)
      sessionStatus.value = response.data
      isConnected.value = response.data.is_active
    } catch (error) {
      console.error('Claude セッション状態取得エラー:', error)
      throw error
    }
  }

  const clearMessages = (): void => {
    messages.value = []
  }

  const addLocalMessage = (sender: ClaudeMessage['sender'], content: string): void => {
    messages.value.push({
      sender,
      content,
      timestamp: new Date().toISOString()
    })
  }

  return {
    // State
    messages,
    sessionStatus,
    isLoading,
    isConnected,
    
    // Actions
    startSession,
    stopSession,
    sendMessage,
    fetchMessages,
    fetchSessionStatus,
    clearMessages,
    addLocalMessage
  }
})