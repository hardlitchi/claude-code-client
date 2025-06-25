<template>
  <div class="notification-panel h-full flex flex-col">
    <!-- ヘッダー -->
    <div class="panel-header bg-gray-100 border-b p-3">
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-2">
          <h3 class="text-sm font-medium text-gray-700">通知</h3>
          <span 
            v-if="unreadCount > 0"
            class="bg-red-500 text-white text-xs rounded-full px-2 py-1 min-w-[20px] text-center"
          >
            {{ unreadCount }}
          </span>
        </div>
        
        <div class="flex items-center space-x-2">
          <!-- 全て既読 -->
          <button
            v-if="unreadCount > 0"
            @click="markAllAsRead"
            class="text-xs text-blue-600 hover:text-blue-800"
          >
            全て既読
          </button>
          
          <!-- クリア -->
          <button
            @click="clearNotifications"
            class="text-xs text-gray-500 hover:text-gray-700"
          >
            クリア
          </button>
          
          <!-- 設定 -->
          <button
            @click="showSettings = !showSettings"
            class="p-1 text-gray-500 hover:text-gray-700 rounded"
            title="通知設定"
          >
            <CogIcon class="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>

    <!-- 通知一覧 -->
    <div class="notifications-list flex-1 overflow-auto">
      <div v-if="notifications.length === 0" class="p-4 text-center text-gray-500">
        <BellIcon class="w-8 h-8 mx-auto mb-2 text-gray-300" />
        <p class="text-sm">通知はありません</p>
      </div>

      <div v-else class="divide-y divide-gray-200">
        <div
          v-for="notification in notifications"
          :key="notification.id"
          class="notification-item p-3 hover:bg-gray-50 cursor-pointer"
          :class="{ 'bg-blue-50': !notification.read }"
          @click="markAsRead(notification.id)"
        >
          <div class="flex items-start space-x-3">
            <!-- アイコン -->
            <div class="flex-shrink-0 mt-1">
              <component 
                :is="getNotificationIcon(notification.icon)"
                class="w-5 h-5"
                :class="getIconColor(notification.icon)"
              />
            </div>
            
            <!-- 内容 -->
            <div class="flex-1 min-w-0">
              <div class="flex items-start justify-between">
                <h4 class="text-sm font-medium text-gray-800 truncate">
                  {{ notification.title }}
                </h4>
                <div class="flex items-center space-x-2 ml-2">
                  <span class="text-xs text-gray-500">
                    {{ formatTime(notification.timestamp) }}
                  </span>
                  <div 
                    v-if="!notification.read"
                    class="w-2 h-2 bg-blue-500 rounded-full"
                  ></div>
                </div>
              </div>
              
              <p class="text-sm text-gray-600 mt-1 line-clamp-2">
                {{ notification.message }}
              </p>
              
              <!-- アクションボタン -->
              <div v-if="notification.actions?.length" class="mt-2 flex space-x-2">
                <button
                  v-for="action in notification.actions"
                  :key="action.id"
                  @click.stop="handleAction(action, notification)"
                  class="text-xs px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  {{ action.title }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 通知設定パネル -->
    <div v-if="showSettings" class="border-t bg-white">
      <NotificationSettings />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useNotificationStore } from '@/stores/notifications'
import { useWebSocketStore } from '@/stores/websocket'
import NotificationSettings from './NotificationSettings.vue'
import {
  BellIcon,
  CogIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  InformationCircleIcon
} from '@heroicons/vue/24/outline'

const notificationStore = useNotificationStore()
const websocketStore = useWebSocketStore()

const showSettings = ref(false)

// 計算プロパティ
const notifications = computed(() => 
  notificationStore.browserNotifications.slice().reverse() // 新しい順
)
const unreadCount = computed(() => notificationStore.unreadCount)

// WebSocket メッセージ監視
watch(
  () => websocketStore.lastMessage,
  (message) => {
    if (message) {
      notificationStore.handleWebSocketMessage(message)
    }
  }
)

onMounted(async () => {
  // 通知設定を読み込み
  try {
    await notificationStore.loadSettings()
  } catch (error) {
    console.warn('通知設定の読み込みに失敗:', error)
  }
  
  // ブラウザ通知の許可をリクエスト（設定がある場合）
  if (notificationStore.hasBrowserSettings && notificationStore.browserPermission === 'default') {
    await notificationStore.requestBrowserPermission()
  }
})

// メソッド
const markAsRead = (id: string) => {
  notificationStore.markAsRead(id)
}

const markAllAsRead = () => {
  notificationStore.markAllAsRead()
}

const clearNotifications = () => {
  if (notifications.value.length > 0) {
    if (confirm('全ての通知をクリアしますか？')) {
      notificationStore.clearNotifications()
    }
  }
}

const handleAction = (action: any, notification: any) => {
  // アクションの処理
  console.log('通知アクション:', action, notification)
  
  switch (action.action) {
    case 'view_file':
      // ファイルビューアーを開く
      break
    case 'view_logs':
      // ログビューアーを開く
      break
    case 'dismiss':
      notificationStore.removeNotification(notification.id)
      break
    default:
      console.log('未知のアクション:', action.action)
  }
}

const getNotificationIcon = (iconType: string) => {
  const iconMap: Record<string, any> = {
    success: CheckCircleIcon,
    warning: ExclamationTriangleIcon,
    error: XCircleIcon,
    info: InformationCircleIcon
  }
  return iconMap[iconType] || InformationCircleIcon
}

const getIconColor = (iconType: string) => {
  const colorMap: Record<string, string> = {
    success: 'text-green-600',
    warning: 'text-yellow-600',
    error: 'text-red-600',
    info: 'text-blue-600'
  }
  return colorMap[iconType] || 'text-blue-600'
}

const formatTime = (timestamp: Date): string => {
  const now = new Date()
  const diff = now.getTime() - timestamp.getTime()
  
  const minutes = Math.floor(diff / (1000 * 60))
  const hours = Math.floor(diff / (1000 * 60 * 60))
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  
  if (minutes < 1) return 'たった今'
  if (minutes < 60) return `${minutes}分前`
  if (hours < 24) return `${hours}時間前`
  if (days < 7) return `${days}日前`
  
  return timestamp.toLocaleDateString('ja-JP')
}
</script>

<style scoped>
.notification-panel {
  @apply bg-white;
}

.notifications-list {
  max-height: 600px;
}

.notification-item {
  transition: background-color 0.2s;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>