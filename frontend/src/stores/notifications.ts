import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import apiClient from '@/services/api'

interface NotificationSetting {
  id: number
  type: 'browser' | 'slack' | 'discord' | 'webhook'
  config: Record<string, any>
  enabled: boolean
  session_id?: string
  created_at: string
  updated_at: string
}

interface EventLog {
  id: number
  session_id?: string
  event_type: string
  event_data: Record<string, any>
  severity: 'info' | 'warning' | 'error' | 'success'
  created_at: string
}

interface WebhookLog {
  id: number
  session_id?: string
  webhook_url: string
  event_type: string
  payload: Record<string, any>
  response_status?: number
  response_body?: string
  success: boolean
  created_at: string
}

interface BrowserNotification {
  id: string
  title: string
  message: string
  icon: 'info' | 'warning' | 'error' | 'success'
  timestamp: Date
  read: boolean
  actions?: Array<{ id: string; title: string; action: string }>
}

export const useNotificationStore = defineStore('notifications', () => {
  // State
  const settings = ref<NotificationSetting[]>([])
  const eventLogs = ref<EventLog[]>([])
  const webhookLogs = ref<WebhookLog[]>([])
  const browserNotifications = ref<BrowserNotification[]>([])
  const loading = ref(false)
  
  // ブラウザ通知の許可状態
  const browserPermission = ref<NotificationPermission>('default')

  // Computed
  const unreadNotifications = computed(() => 
    browserNotifications.value.filter(n => !n.read)
  )
  
  const unreadCount = computed(() => unreadNotifications.value.length)
  
  const hasSlackSettings = computed(() => 
    settings.value.some(s => s.type === 'slack' && s.enabled)
  )
  
  const hasDiscordSettings = computed(() => 
    settings.value.some(s => s.type === 'discord' && s.enabled)
  )
  
  const hasBrowserSettings = computed(() => 
    settings.value.some(s => s.type === 'browser' && s.enabled)
  )

  // Actions
  const requestBrowserPermission = async () => {
    if ('Notification' in window) {
      const permission = await Notification.requestPermission()
      browserPermission.value = permission
      return permission === 'granted'
    }
    return false
  }

  const loadSettings = async () => {
    try {
      loading.value = true
      const response = await apiClient.get('/api/notifications/settings')
      settings.value = response.data.settings
      return response.data.settings
    } catch (error: any) {
      console.error('通知設定読み込みエラー:', error)
      throw new Error(error.response?.data?.detail || '通知設定の読み込みに失敗しました')
    } finally {
      loading.value = false
    }
  }

  const createSetting = async (setting: {
    type: string
    config: Record<string, any>
    enabled?: boolean
    session_id?: string
  }) => {
    try {
      const response = await apiClient.post('/api/notifications/settings', setting)
      await loadSettings() // 設定を再読み込み
      return response.data
    } catch (error: any) {
      console.error('通知設定作成エラー:', error)
      throw new Error(error.response?.data?.detail || '通知設定の作成に失敗しました')
    }
  }

  const updateSetting = async (id: number, setting: {
    type: string
    config: Record<string, any>
    enabled?: boolean
    session_id?: string
  }) => {
    try {
      const response = await apiClient.put(`/api/notifications/settings/${id}`, setting)
      await loadSettings() // 設定を再読み込み
      return response.data
    } catch (error: any) {
      console.error('通知設定更新エラー:', error)
      throw new Error(error.response?.data?.detail || '通知設定の更新に失敗しました')
    }
  }

  const deleteSetting = async (id: number) => {
    try {
      const response = await apiClient.delete(`/api/notifications/settings/${id}`)
      await loadSettings() // 設定を再読み込み
      return response.data
    } catch (error: any) {
      console.error('通知設定削除エラー:', error)
      throw new Error(error.response?.data?.detail || '通知設定の削除に失敗しました')
    }
  }

  const testNotification = async (type: string, config: Record<string, any>, message?: string) => {
    try {
      const response = await apiClient.post('/api/notifications/test', {
        type,
        config,
        message: message || 'これはテスト通知です'
      })
      return response.data
    } catch (error: any) {
      console.error('テスト通知エラー:', error)
      throw new Error(error.response?.data?.detail || 'テスト通知の送信に失敗しました')
    }
  }

  const loadEventLogs = async (options: {
    session_id?: string
    event_type?: string
    severity?: string
    limit?: number
    offset?: number
  } = {}) => {
    try {
      const response = await apiClient.get('/api/notifications/events', {
        params: options
      })
      eventLogs.value = response.data.events
      return response.data
    } catch (error: any) {
      console.error('イベントログ読み込みエラー:', error)
      throw new Error(error.response?.data?.detail || 'イベントログの読み込みに失敗しました')
    }
  }

  const loadWebhookLogs = async (options: {
    limit?: number
    offset?: number
  } = {}) => {
    try {
      const response = await apiClient.get('/api/notifications/webhook-logs', {
        params: options
      })
      webhookLogs.value = response.data.logs
      return response.data
    } catch (error: any) {
      console.error('Webhookログ読み込みエラー:', error)
      throw new Error(error.response?.data?.detail || 'Webhookログの読み込みに失敗しました')
    }
  }

  const triggerEvent = async (
    sessionId: string,
    eventType: string,
    eventData: Record<string, any>,
    severity: 'info' | 'warning' | 'error' | 'success' = 'info'
  ) => {
    try {
      const response = await apiClient.post(`/api/notifications/events/${sessionId}`, {
        event_type: eventType,
        event_data: eventData,
        severity
      })
      return response.data
    } catch (error: any) {
      console.error('イベントトリガーエラー:', error)
      throw new Error(error.response?.data?.detail || 'イベントのトリガーに失敗しました')
    }
  }

  // ブラウザ通知管理
  const showBrowserNotification = (notification: Omit<BrowserNotification, 'id' | 'timestamp' | 'read'>) => {
    const id = Date.now().toString()
    const browserNotif: BrowserNotification = {
      id,
      ...notification,
      timestamp: new Date(),
      read: false
    }
    
    browserNotifications.value.unshift(browserNotif)
    
    // ブラウザネイティブ通知を表示
    if (browserPermission.value === 'granted' && hasBrowserSettings.value) {
      const nativeNotif = new Notification(notification.title, {
        body: notification.message,
        icon: getNotificationIcon(notification.icon),
        tag: id
      })
      
      nativeNotif.onclick = () => {
        markAsRead(id)
        nativeNotif.close()
      }
      
      // 5秒後に自動で閉じる
      setTimeout(() => {
        nativeNotif.close()
      }, 5000)
    }
    
    return id
  }

  const markAsRead = (id: string) => {
    const notification = browserNotifications.value.find(n => n.id === id)
    if (notification) {
      notification.read = true
    }
  }

  const markAllAsRead = () => {
    browserNotifications.value.forEach(n => n.read = true)
  }

  const clearNotifications = () => {
    browserNotifications.value = []
  }

  const removeNotification = (id: string) => {
    const index = browserNotifications.value.findIndex(n => n.id === id)
    if (index !== -1) {
      browserNotifications.value.splice(index, 1)
    }
  }

  // WebSocketメッセージハンドリング
  const handleWebSocketMessage = (message: any) => {
    switch (message.type) {
      case 'browser_notification':
        showBrowserNotification({
          title: message.title,
          message: message.message,
          icon: message.icon || 'info',
          actions: message.actions
        })
        break
        
      case 'build_completed':
        if (hasBrowserSettings.value) {
          const success = message.success
          showBrowserNotification({
            title: 'ビルド完了',
            message: success ? 'ビルドが正常に完了しました' : 'ビルドが失敗しました',
            icon: success ? 'success' : 'error'
          })
        }
        break
        
      case 'deploy_completed':
        if (hasBrowserSettings.value) {
          const success = message.success
          showBrowserNotification({
            title: 'デプロイ完了',
            message: success 
              ? `デプロイが正常に完了しました (${message.target})`
              : `デプロイが失敗しました (${message.target})`,
            icon: success ? 'success' : 'error'
          })
        }
        break
        
      case 'file_updated':
        if (hasBrowserSettings.value) {
          showBrowserNotification({
            title: 'ファイル更新',
            message: `${message.file_path} が更新されました`,
            icon: 'info'
          })
        }
        break
        
      case 'project_created':
        if (hasBrowserSettings.value) {
          showBrowserNotification({
            title: 'プロジェクト作成',
            message: `プロジェクト "${message.project_name}" が作成されました`,
            icon: 'success'
          })
        }
        break
    }
  }

  // ユーティリティ関数
  const getNotificationIcon = (type: string): string => {
    const iconMap: Record<string, string> = {
      info: '/icons/info.png',
      success: '/icons/success.png',
      warning: '/icons/warning.png',
      error: '/icons/error.png'
    }
    return iconMap[type] || iconMap.info
  }

  const getSeverityColor = (severity: string): string => {
    const colorMap: Record<string, string> = {
      info: 'text-blue-600',
      success: 'text-green-600',
      warning: 'text-yellow-600',
      error: 'text-red-600'
    }
    return colorMap[severity] || colorMap.info
  }

  const getSeverityBgColor = (severity: string): string => {
    const colorMap: Record<string, string> = {
      info: 'bg-blue-50',
      success: 'bg-green-50',
      warning: 'bg-yellow-50',
      error: 'bg-red-50'
    }
    return colorMap[severity] || colorMap.info
  }

  const formatEventData = (eventData: Record<string, any>): string => {
    try {
      return JSON.stringify(eventData, null, 2)
    } catch {
      return String(eventData)
    }
  }

  // 初期化時にブラウザ通知の許可状態を確認
  if ('Notification' in window) {
    browserPermission.value = Notification.permission
  }

  return {
    // State
    settings,
    eventLogs,
    webhookLogs,
    browserNotifications,
    loading,
    browserPermission,

    // Computed
    unreadNotifications,
    unreadCount,
    hasSlackSettings,
    hasDiscordSettings,
    hasBrowserSettings,

    // Actions
    requestBrowserPermission,
    loadSettings,
    createSetting,
    updateSetting,
    deleteSetting,
    testNotification,
    loadEventLogs,
    loadWebhookLogs,
    triggerEvent,
    showBrowserNotification,
    markAsRead,
    markAllAsRead,
    clearNotifications,
    removeNotification,
    handleWebSocketMessage,

    // Utilities
    getNotificationIcon,
    getSeverityColor,
    getSeverityBgColor,
    formatEventData
  }
})