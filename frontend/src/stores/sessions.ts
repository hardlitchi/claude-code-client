import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useAuthStore } from './auth'

interface Session {
  id: number
  session_id: string
  name: string
  description?: string
  working_directory?: string
  status: 'running' | 'stopped' | 'error'
  user_id: number
  created_at: string
  updated_at?: string
  last_accessed: string
}

interface SessionCreate {
  name: string
  description?: string
  working_directory?: string
}

interface SessionUpdate {
  name?: string
  description?: string
  working_directory?: string
  status?: string
}

export const useSessionsStore = defineStore('sessions', () => {
  // State
  const sessions = ref<Session[]>([])
  const currentSession = ref<Session | null>(null)
  const isLoading = ref(false)

  // Auth store
  const authStore = useAuthStore()

  // Actions
  const fetchSessions = async (): Promise<void> => {
    isLoading.value = true
    try {
      const response = await authStore.api.get('/sessions/')
      sessions.value = response.data.sessions
    } catch (error) {
      console.error('セッション一覧取得エラー:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  const createSession = async (sessionData: SessionCreate): Promise<Session> => {
    isLoading.value = true
    try {
      const response = await authStore.api.post('/sessions/', sessionData)
      const newSession = response.data
      sessions.value.push(newSession)
      return newSession
    } catch (error) {
      console.error('セッション作成エラー:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  const getSession = async (sessionId: string): Promise<Session> => {
    isLoading.value = true
    try {
      const response = await authStore.api.get(`/sessions/${sessionId}`)
      const session = response.data
      currentSession.value = session
      
      // セッション一覧も更新
      const index = sessions.value.findIndex(s => s.session_id === sessionId)
      if (index !== -1) {
        sessions.value[index] = session
      }
      
      return session
    } catch (error) {
      console.error('セッション取得エラー:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  const updateSession = async (sessionId: string, updateData: SessionUpdate): Promise<Session> => {
    isLoading.value = true
    try {
      const response = await authStore.api.put(`/sessions/${sessionId}`, updateData)
      const updatedSession = response.data
      
      // 現在のセッションを更新
      if (currentSession.value?.session_id === sessionId) {
        currentSession.value = updatedSession
      }
      
      // セッション一覧も更新
      const index = sessions.value.findIndex(s => s.session_id === sessionId)
      if (index !== -1) {
        sessions.value[index] = updatedSession
      }
      
      return updatedSession
    } catch (error) {
      console.error('セッション更新エラー:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  const deleteSession = async (sessionId: string): Promise<void> => {
    isLoading.value = true
    try {
      await authStore.api.delete(`/sessions/${sessionId}`)
      
      // セッション一覧から削除
      sessions.value = sessions.value.filter(s => s.session_id !== sessionId)
      
      // 現在のセッションをクリア
      if (currentSession.value?.session_id === sessionId) {
        currentSession.value = null
      }
    } catch (error) {
      console.error('セッション削除エラー:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  const startSession = async (sessionId: string): Promise<void> => {
    isLoading.value = true
    try {
      await authStore.api.post(`/sessions/${sessionId}/start`)
      
      // セッション状態を更新
      await updateSessionStatus(sessionId, 'running')
    } catch (error) {
      console.error('セッション開始エラー:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  const stopSession = async (sessionId: string): Promise<void> => {
    isLoading.value = true
    try {
      await authStore.api.post(`/sessions/${sessionId}/stop`)
      
      // セッション状態を更新
      await updateSessionStatus(sessionId, 'stopped')
    } catch (error) {
      console.error('セッション停止エラー:', error)
      throw error
    } finally {
      isLoading.value = false
    }
  }

  // ヘルパー関数
  const updateSessionStatus = (sessionId: string, status: string): void => {
    // 現在のセッションを更新
    if (currentSession.value?.session_id === sessionId) {
      currentSession.value.status = status as any
    }
    
    // セッション一覧も更新
    const index = sessions.value.findIndex(s => s.session_id === sessionId)
    if (index !== -1) {
      sessions.value[index].status = status as any
    }
  }

  const getSessionById = (sessionId: string): Session | undefined => {
    return sessions.value.find(s => s.session_id === sessionId)
  }

  const clearCurrentSession = (): void => {
    currentSession.value = null
  }

  return {
    // State
    sessions,
    currentSession,
    isLoading,
    
    // Actions
    fetchSessions,
    createSession,
    getSession,
    updateSession,
    deleteSession,
    startSession,
    stopSession,
    
    // Helpers
    getSessionById,
    clearCurrentSession
  }
})