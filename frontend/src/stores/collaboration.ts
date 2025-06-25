import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import apiClient from '@/services/api'

interface User {
  id: number
  username: string
}

interface SessionShare {
  id: number
  shared_with: User
  permission_level: 'viewer' | 'collaborator' | 'admin'
  expires_at?: string
  created_at: string
}

interface SharedSession {
  session_id: string
  name: string
  description?: string
  owner: User
  permission_level: 'viewer' | 'collaborator' | 'admin'
  shared_at: string
  expires_at?: string
}

interface Participant {
  user: User
  joined_at: string
  last_seen: string
  cursor_position?: {
    file_path?: string
    line: number
    column: number
    selection?: any
  }
}

interface Activity {
  id: number
  user: User
  activity_type: string
  activity_data: Record<string, any>
  timestamp: string
}

interface CursorPosition {
  file_path?: string
  line: number
  column: number
  selection?: any
}

export const useCollaborationStore = defineStore('collaboration', () => {
  // State
  const sessionShares = ref<SessionShare[]>([])
  const sharedSessions = ref<SharedSession[]>([])
  const participants = ref<Participant[]>([])
  const activities = ref<Activity[]>([])
  const userCursors = ref<Map<number, CursorPosition>>(new Map())
  const loading = ref(false)

  // Computed
  const hasSharedSessions = computed(() => sharedSessions.value.length > 0)
  
  const activeParticipants = computed(() => 
    participants.value.filter(p => {
      const lastSeen = new Date(p.last_seen)
      const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000)
      return lastSeen > fiveMinutesAgo
    })
  )
  
  const participantCount = computed(() => activeParticipants.value.length)

  // Actions
  const shareSession = async (
    sessionId: string,
    username: string,
    permissionLevel: 'viewer' | 'collaborator' | 'admin',
    expiresHours?: number
  ) => {
    try {
      const response = await apiClient.post(`/api/collaboration/sessions/${sessionId}/share`, {
        username,
        permission_level: permissionLevel,
        expires_hours: expiresHours
      })
      
      // 共有一覧を再読み込み
      await loadSessionShares(sessionId)
      
      return response.data
    } catch (error: any) {
      console.error('セッション共有エラー:', error)
      throw new Error(error.response?.data?.detail || 'セッションの共有に失敗しました')
    }
  }

  const loadSessionShares = async (sessionId: string) => {
    try {
      loading.value = true
      const response = await apiClient.get(`/api/collaboration/sessions/${sessionId}/shares`)
      sessionShares.value = response.data.shares
      return response.data.shares
    } catch (error: any) {
      console.error('共有一覧読み込みエラー:', error)
      throw new Error(error.response?.data?.detail || '共有一覧の読み込みに失敗しました')
    } finally {
      loading.value = false
    }
  }

  const updateSharePermission = async (
    sessionId: string,
    shareId: number,
    permissionLevel: 'viewer' | 'collaborator' | 'admin'
  ) => {
    try {
      const response = await apiClient.put(
        `/api/collaboration/sessions/${sessionId}/shares/${shareId}`,
        { permission_level: permissionLevel }
      )
      
      // 共有一覧を再読み込み
      await loadSessionShares(sessionId)
      
      return response.data
    } catch (error: any) {
      console.error('権限更新エラー:', error)
      throw new Error(error.response?.data?.detail || '権限の更新に失敗しました')
    }
  }

  const revokeShare = async (sessionId: string, shareId: number) => {
    try {
      const response = await apiClient.delete(
        `/api/collaboration/sessions/${sessionId}/shares/${shareId}`
      )
      
      // 共有一覧を再読み込み
      await loadSessionShares(sessionId)
      
      return response.data
    } catch (error: any) {
      console.error('共有取り消しエラー:', error)
      throw new Error(error.response?.data?.detail || '共有の取り消しに失敗しました')
    }
  }

  const loadSharedSessions = async () => {
    try {
      loading.value = true
      const response = await apiClient.get('/api/collaboration/sessions/shared')
      sharedSessions.value = response.data.shared_sessions
      return response.data.shared_sessions
    } catch (error: any) {
      console.error('共有セッション読み込みエラー:', error)
      throw new Error(error.response?.data?.detail || '共有セッションの読み込みに失敗しました')
    } finally {
      loading.value = false
    }
  }

  const joinSession = async (sessionId: string) => {
    try {
      const response = await apiClient.post(`/api/collaboration/sessions/${sessionId}/join`)
      
      // 参加者一覧を更新
      await loadParticipants(sessionId)
      
      return response.data
    } catch (error: any) {
      console.error('セッション参加エラー:', error)
      throw new Error(error.response?.data?.detail || 'セッションへの参加に失敗しました')
    }
  }

  const leaveSession = async (sessionId: string) => {
    try {
      const response = await apiClient.post(`/api/collaboration/sessions/${sessionId}/leave`)
      
      // ローカル状態をクリア
      participants.value = []
      activities.value = []
      userCursors.value.clear()
      
      return response.data
    } catch (error: any) {
      console.error('セッション離脱エラー:', error)
      throw new Error(error.response?.data?.detail || 'セッションからの離脱に失敗しました')
    }
  }

  const loadParticipants = async (sessionId: string) => {
    try {
      const response = await apiClient.get(`/api/collaboration/sessions/${sessionId}/participants`)
      participants.value = response.data.participants
      
      // カーソル位置をマップに保存
      userCursors.value.clear()
      response.data.participants.forEach((p: Participant) => {
        if (p.cursor_position) {
          userCursors.value.set(p.user.id, p.cursor_position)
        }
      })
      
      return response.data.participants
    } catch (error: any) {
      console.error('参加者読み込みエラー:', error)
      throw new Error(error.response?.data?.detail || '参加者一覧の読み込みに失敗しました')
    }
  }

  const recordActivity = async (
    sessionId: string,
    activityType: string,
    activityData: Record<string, any>
  ) => {
    try {
      const response = await apiClient.post(`/api/collaboration/sessions/${sessionId}/activity`, {
        activity_type: activityType,
        activity_data: activityData
      })
      return response.data
    } catch (error: any) {
      console.error('アクティビティ記録エラー:', error)
      // アクティビティ記録は失敗してもアプリケーションを停止させない
      console.warn('アクティビティの記録に失敗しましたが、処理を続行します')
    }
  }

  const updateCursorPosition = async (sessionId: string, cursor: CursorPosition) => {
    try {
      const response = await apiClient.put(`/api/collaboration/sessions/${sessionId}/cursor`, cursor)
      return response.data
    } catch (error: any) {
      console.error('カーソル位置更新エラー:', error)
      // カーソル位置更新の失敗は無視（高頻度で発生するため）
    }
  }

  const loadActivities = async (
    sessionId: string,
    options: {
      activity_type?: string
      limit?: number
      offset?: number
    } = {}
  ) => {
    try {
      const response = await apiClient.get(`/api/collaboration/sessions/${sessionId}/activities`, {
        params: options
      })
      
      if (options.offset === 0) {
        activities.value = response.data.activities
      } else {
        activities.value.push(...response.data.activities)
      }
      
      return response.data
    } catch (error: any) {
      console.error('アクティビティ読み込みエラー:', error)
      throw new Error(error.response?.data?.detail || 'アクティビティの読み込みに失敗しました')
    }
  }

  // WebSocket メッセージハンドリング
  const handleWebSocketMessage = (message: any) => {
    switch (message.type) {
      case 'user_joined':
        {
          const existingIndex = participants.value.findIndex(p => p.user.id === message.user.id)
          const newParticipant: Participant = {
            user: message.user,
            joined_at: message.timestamp,
            last_seen: message.timestamp
          }
          
          if (existingIndex >= 0) {
            participants.value[existingIndex] = newParticipant
          } else {
            participants.value.push(newParticipant)
          }
        }
        break

      case 'user_left':
        {
          const index = participants.value.findIndex(p => p.user.id === message.user.id)
          if (index >= 0) {
            participants.value.splice(index, 1)
          }
          userCursors.value.delete(message.user.id)
        }
        break

      case 'user_activity':
        {
          const newActivity: Activity = {
            id: Date.now(), // 一時的なID
            user: message.user,
            activity_type: message.activity_type,
            activity_data: message.activity_data,
            timestamp: message.timestamp
          }
          
          activities.value.unshift(newActivity)
          
          // 最新100件のみ保持
          if (activities.value.length > 100) {
            activities.value = activities.value.slice(0, 100)
          }
        }
        break

      case 'cursor_update':
        {
          userCursors.value.set(message.user.id, message.cursor)
          
          // 参加者リストの最終アクセス時刻を更新
          const participant = participants.value.find(p => p.user.id === message.user.id)
          if (participant) {
            participant.last_seen = message.timestamp
            participant.cursor_position = message.cursor
          }
        }
        break
    }
  }

  // ユーティリティ関数
  const getPermissionLabel = (level: string): string => {
    const labels: Record<string, string> = {
      viewer: '閲覧者',
      collaborator: '共同編集者',
      admin: '管理者'
    }
    return labels[level] || level
  }

  const getPermissionColor = (level: string): string => {
    const colors: Record<string, string> = {
      viewer: 'text-gray-600',
      collaborator: 'text-blue-600',
      admin: 'text-purple-600'
    }
    return colors[level] || 'text-gray-600'
  }

  const canEdit = (level: string): boolean => {
    return ['collaborator', 'admin'].includes(level)
  }

  const canManage = (level: string): boolean => {
    return level === 'admin'
  }

  const formatActivity = (activity: Activity): string => {
    const { activity_type, activity_data } = activity
    
    switch (activity_type) {
      case 'file_edit':
        return `ファイル ${activity_data.file_path} を編集`
      case 'file_create':
        return `ファイル ${activity_data.file_path} を作成`
      case 'file_delete':
        return `ファイル ${activity_data.file_path} を削除`
      case 'cursor_move':
        return `カーソルを移動 (${activity_data.line}:${activity_data.column})`
      case 'chat':
        return `チャット: ${activity_data.message}`
      default:
        return activity_type
    }
  }

  const getUserCursor = (userId: number): CursorPosition | undefined => {
    return userCursors.value.get(userId)
  }

  const isUserActive = (participant: Participant): boolean => {
    const lastSeen = new Date(participant.last_seen)
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000)
    return lastSeen > fiveMinutesAgo
  }

  const clearSessionData = () => {
    sessionShares.value = []
    participants.value = []
    activities.value = []
    userCursors.value.clear()
  }

  return {
    // State
    sessionShares,
    sharedSessions,
    participants,
    activities,
    userCursors,
    loading,

    // Computed
    hasSharedSessions,
    activeParticipants,
    participantCount,

    // Actions
    shareSession,
    loadSessionShares,
    updateSharePermission,
    revokeShare,
    loadSharedSessions,
    joinSession,
    leaveSession,
    loadParticipants,
    recordActivity,
    updateCursorPosition,
    loadActivities,
    handleWebSocketMessage,

    // Utilities
    getPermissionLabel,
    getPermissionColor,
    canEdit,
    canManage,
    formatActivity,
    getUserCursor,
    isUserActive,
    clearSessionData
  }
})