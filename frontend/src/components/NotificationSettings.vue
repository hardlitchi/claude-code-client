<template>
  <div class="notification-settings h-full flex flex-col">
    <!-- ヘッダー -->
    <div class="settings-header bg-gray-100 border-b p-3">
      <div class="flex items-center justify-between">
        <h3 class="text-sm font-medium text-gray-700">通知設定</h3>
        <button
          @click="showCreateModal = true"
          class="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          新規追加
        </button>
      </div>
    </div>

    <!-- 通知設定一覧 -->
    <div class="settings-list flex-1 overflow-auto">
      <div v-if="loading" class="p-4 text-center text-gray-500">
        読み込み中...
      </div>
      
      <div v-else-if="settings.length === 0" class="p-4 text-center text-gray-500">
        <BellIcon class="w-12 h-12 mx-auto mb-2 text-gray-300" />
        <p>通知設定がありません</p>
        <p class="text-xs">新規追加ボタンから設定を作成してください</p>
      </div>

      <div v-else class="p-4 space-y-3">
        <div
          v-for="setting in settings"
          :key="setting.id"
          class="bg-white border rounded-lg p-4"
        >
          <div class="flex items-start justify-between">
            <div class="flex-1">
              <!-- 設定タイプとアイコン -->
              <div class="flex items-center space-x-2 mb-2">
                <component 
                  :is="getTypeIcon(setting.type)"
                  class="w-5 h-5"
                  :class="getTypeColor(setting.type)"
                />
                <h4 class="font-medium text-gray-800">{{ getTypeName(setting.type) }}</h4>
                <span 
                  class="text-xs px-2 py-1 rounded"
                  :class="setting.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'"
                >
                  {{ setting.enabled ? '有効' : '無効' }}
                </span>
              </div>

              <!-- 設定詳細 -->
              <div class="text-sm text-gray-600 space-y-1">
                <div v-if="setting.type === 'slack'">
                  <span class="font-medium">チャンネル:</span> 
                  {{ setting.config.channel || '#general' }}
                </div>
                <div v-else-if="setting.type === 'discord'">
                  <span class="font-medium">Webhook URL:</span> 
                  {{ truncateUrl(setting.config.webhook_url) }}
                </div>
                <div v-else-if="setting.type === 'webhook'">
                  <span class="font-medium">URL:</span> 
                  {{ truncateUrl(setting.config.url) }}
                </div>
                <div v-else-if="setting.type === 'browser'">
                  <span class="font-medium">ブラウザ通知</span>
                  <span v-if="!browserPermissionGranted" class="text-orange-600 ml-2">
                    (許可が必要)
                  </span>
                </div>

                <div v-if="setting.session_id" class="text-xs text-gray-500">
                  セッション限定: {{ setting.session_id }}
                </div>
              </div>

              <!-- 作成日時 -->
              <div class="text-xs text-gray-400 mt-2">
                作成: {{ formatDate(setting.created_at) }}
              </div>
            </div>

            <!-- 操作ボタン -->
            <div class="flex items-center space-x-2 ml-4">
              <!-- 有効/無効切り替え -->
              <button
                @click="toggleSetting(setting)"
                class="p-1 rounded text-gray-500 hover:text-gray-700"
                :title="setting.enabled ? '無効にする' : '有効にする'"
              >
                <component 
                  :is="setting.enabled ? EyeIcon : EyeSlashIcon"
                  class="w-4 h-4"
                />
              </button>

              <!-- テスト送信 -->
              <button
                @click="testNotification(setting)"
                :disabled="!setting.enabled || testing"
                class="p-1 rounded text-blue-500 hover:text-blue-700 disabled:opacity-50"
                title="テスト送信"
              >
                <PlayIcon class="w-4 h-4" />
              </button>

              <!-- 編集 -->
              <button
                @click="editSetting(setting)"
                class="p-1 rounded text-gray-500 hover:text-gray-700"
                title="編集"
              >
                <PencilIcon class="w-4 h-4" />
              </button>

              <!-- 削除 -->
              <button
                @click="deleteSetting(setting)"
                class="p-1 rounded text-red-500 hover:text-red-700"
                title="削除"
              >
                <TrashIcon class="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ブラウザ通知許可バナー -->
    <div 
      v-if="hasBrowserSettings && !browserPermissionGranted"
      class="border-t bg-orange-50 border-orange-200 p-3"
    >
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-2">
          <ExclamationTriangleIcon class="w-5 h-5 text-orange-600" />
          <span class="text-sm text-orange-800">
            ブラウザ通知の許可が必要です
          </span>
        </div>
        <button
          @click="requestPermission"
          class="px-3 py-1 text-xs bg-orange-600 text-white rounded hover:bg-orange-700"
        >
          許可する
        </button>
      </div>
    </div>

    <!-- 設定作成/編集モーダル -->
    <NotificationSettingModal
      v-if="showCreateModal || editingSettings"
      :setting="editingSettings"
      @close="closeModal"
      @saved="onSettingSaved"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useNotificationStore } from '@/stores/notifications'
import NotificationSettingModal from './NotificationSettingModal.vue'
import {
  BellIcon,
  EyeIcon,
  EyeSlashIcon,
  PlayIcon,
  PencilIcon,
  TrashIcon,
  ExclamationTriangleIcon,
  ChatBubbleLeftEllipsisIcon,
  GlobeAltIcon,
  ComputerDesktopIcon
} from '@heroicons/vue/24/outline'

const notificationStore = useNotificationStore()

const loading = ref(false)
const testing = ref(false)
const showCreateModal = ref(false)
const editingSettings = ref<any>(null)

// 計算プロパティ
const settings = computed(() => notificationStore.settings)
const hasBrowserSettings = computed(() => notificationStore.hasBrowserSettings)
const browserPermissionGranted = computed(() => notificationStore.browserPermission === 'granted')

onMounted(() => {
  loadSettings()
})

// メソッド
const loadSettings = async () => {
  loading.value = true
  try {
    await notificationStore.loadSettings()
  } catch (error: any) {
    alert(`設定読み込みエラー: ${error.message}`)
  } finally {
    loading.value = false
  }
}

const toggleSetting = async (setting: any) => {
  try {
    await notificationStore.updateSetting(setting.id, {
      ...setting,
      enabled: !setting.enabled
    })
  } catch (error: any) {
    alert(`設定更新エラー: ${error.message}`)
  }
}

const testNotification = async (setting: any) => {
  testing.value = true
  try {
    await notificationStore.testNotification(
      setting.type,
      setting.config,
      `${getTypeName(setting.type)} のテスト通知です`
    )
    alert('テスト通知を送信しました')
  } catch (error: any) {
    alert(`テスト送信エラー: ${error.message}`)
  } finally {
    testing.value = false
  }
}

const editSetting = (setting: any) => {
  editingSettings.value = setting
}

const deleteSetting = async (setting: any) => {
  if (!confirm(`${getTypeName(setting.type)} の設定を削除しますか？`)) {
    return
  }

  try {
    await notificationStore.deleteSetting(setting.id)
  } catch (error: any) {
    alert(`削除エラー: ${error.message}`)
  }
}

const requestPermission = async () => {
  const granted = await notificationStore.requestBrowserPermission()
  if (!granted) {
    alert('ブラウザ通知の許可が拒否されました。ブラウザの設定から手動で許可してください。')
  }
}

const closeModal = () => {
  showCreateModal.value = false
  editingSettings.value = null
}

const onSettingSaved = () => {
  closeModal()
  loadSettings()
}

// ユーティリティ関数
const getTypeIcon = (type: string) => {
  const iconMap: Record<string, any> = {
    browser: ComputerDesktopIcon,
    slack: ChatBubbleLeftEllipsisIcon,
    discord: ChatBubbleLeftEllipsisIcon,
    webhook: GlobeAltIcon
  }
  return iconMap[type] || BellIcon
}

const getTypeColor = (type: string) => {
  const colorMap: Record<string, string> = {
    browser: 'text-blue-600',
    slack: 'text-green-600',
    discord: 'text-purple-600',
    webhook: 'text-gray-600'
  }
  return colorMap[type] || 'text-gray-600'
}

const getTypeName = (type: string) => {
  const nameMap: Record<string, string> = {
    browser: 'ブラウザ通知',
    slack: 'Slack',
    discord: 'Discord',
    webhook: 'Webhook'
  }
  return nameMap[type] || type
}

const truncateUrl = (url?: string): string => {
  if (!url) return ''
  if (url.length <= 50) return url
  return url.substring(0, 47) + '...'
}

const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleString('ja-JP')
}
</script>

<style scoped>
.notification-settings {
  @apply bg-gray-50;
}

.settings-list {
  @apply bg-gray-50;
}
</style>