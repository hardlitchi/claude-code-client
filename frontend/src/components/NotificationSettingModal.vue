<template>
  <Modal @close="$emit('close')">
    <template #header>
      <h3 class="text-lg font-medium">
        {{ isEditing ? '通知設定を編集' : '新しい通知設定' }}
      </h3>
    </template>
    
    <template #body>
      <div class="space-y-6">
        <!-- 通知タイプ選択 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-3">
            通知タイプ
          </label>
          
          <div class="grid grid-cols-2 gap-3">
            <div
              v-for="type in notificationTypes"
              :key="type.id"
              class="border rounded-lg p-3 cursor-pointer transition-colors"
              :class="{
                'border-blue-500 bg-blue-50': selectedType === type.id,
                'border-gray-200 hover:border-gray-300': selectedType !== type.id
              }"
              @click="selectedType = type.id"
            >
              <div class="flex items-center space-x-2">
                <component 
                  :is="type.icon"
                  class="w-5 h-5"
                  :class="type.color"
                />
                <span class="font-medium text-sm">{{ type.name }}</span>
              </div>
              <p class="text-xs text-gray-600 mt-1">{{ type.description }}</p>
            </div>
          </div>
        </div>

        <!-- ブラウザ通知設定 -->
        <div v-if="selectedType === 'browser'" class="space-y-4">
          <div class="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <div class="flex items-center space-x-2">
              <InformationCircleIcon class="w-5 h-5 text-blue-600" />
              <span class="text-sm text-blue-800">
                ブラウザ通知は自動的に表示されます。追加設定は不要です。
              </span>
            </div>
          </div>
        </div>

        <!-- Slack設定 -->
        <div v-if="selectedType === 'slack'" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Webhook URL <span class="text-red-500">*</span>
            </label>
            <input
              v-model="config.webhook_url"
              type="url"
              class="w-full p-3 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
              placeholder="https://hooks.slack.com/services/..."
              required
            />
            <p class="mt-1 text-xs text-gray-500">
              Slack App の Incoming Webhooks URL を入力してください
            </p>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              チャンネル（任意）
            </label>
            <input
              v-model="config.channel"
              type="text"
              class="w-full p-3 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
              placeholder="#general"
            />
          </div>
        </div>

        <!-- Discord設定 -->
        <div v-if="selectedType === 'discord'" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Webhook URL <span class="text-red-500">*</span>
            </label>
            <input
              v-model="config.webhook_url"
              type="url"
              class="w-full p-3 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
              placeholder="https://discord.com/api/webhooks/..."
              required
            />
            <p class="mt-1 text-xs text-gray-500">
              Discord サーバーのWebhook URL を入力してください
            </p>
          </div>
        </div>

        <!-- 汎用Webhook設定 -->
        <div v-if="selectedType === 'webhook'" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Webhook URL <span class="text-red-500">*</span>
            </label>
            <input
              v-model="config.url"
              type="url"
              class="w-full p-3 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
              placeholder="https://example.com/webhook"
              required
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              カスタムヘッダー（任意）
            </label>
            <div class="space-y-2">
              <div
                v-for="(header, index) in customHeaders"
                :key="index"
                class="flex space-x-2"
              >
                <input
                  v-model="header.key"
                  type="text"
                  class="flex-1 p-2 text-sm border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
                  placeholder="ヘッダー名"
                />
                <input
                  v-model="header.value"
                  type="text"
                  class="flex-1 p-2 text-sm border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
                  placeholder="値"
                />
                <button
                  @click="removeHeader(index)"
                  class="p-2 text-red-500 hover:text-red-700"
                  title="削除"
                >
                  <TrashIcon class="w-4 h-4" />
                </button>
              </div>
              
              <button
                @click="addHeader"
                class="w-full p-2 text-sm text-blue-600 border border-blue-300 border-dashed rounded hover:border-blue-500"
              >
                + ヘッダーを追加
              </button>
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              シークレット（任意）
            </label>
            <input
              v-model="config.secret"
              type="password"
              class="w-full p-3 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
              placeholder="認証用シークレット"
            />
            <p class="mt-1 text-xs text-gray-500">
              X-Claude-Secret ヘッダーとして送信されます
            </p>
          </div>
        </div>

        <!-- セッション限定設定 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            セッション限定（任意）
          </label>
          <input
            v-model="sessionId"
            type="text"
            class="w-full p-3 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
            placeholder="特定のセッションIDを入力"
          />
          <p class="mt-1 text-xs text-gray-500">
            空の場合は全セッションで有効になります
          </p>
        </div>

        <!-- 有効/無効設定 -->
        <div>
          <label class="flex items-center">
            <input
              v-model="enabled"
              type="checkbox"
              class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span class="ml-2 text-sm text-gray-700">この通知設定を有効にする</span>
          </label>
        </div>
      </div>
    </template>
    
    <template #footer>
      <div class="flex justify-between">
        <!-- テスト送信ボタン -->
        <button
          v-if="canTest"
          @click="testNotification"
          :disabled="testing || !isConfigValid"
          class="px-4 py-2 text-sm bg-yellow-600 text-white rounded hover:bg-yellow-700 disabled:opacity-50"
        >
          {{ testing ? 'テスト中...' : 'テスト送信' }}
        </button>
        
        <div v-else></div>
        
        <!-- 保存/キャンセルボタン -->
        <div class="flex space-x-3">
          <button
            @click="$emit('close')"
            class="px-4 py-2 text-gray-600 hover:text-gray-800"
            :disabled="saving"
          >
            キャンセル
          </button>
          <button
            @click="saveSetting"
            :disabled="!canSave || saving"
            class="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {{ saving ? '保存中...' : (isEditing ? '更新' : '作成') }}
          </button>
        </div>
      </div>
    </template>
  </Modal>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useNotificationStore } from '@/stores/notifications'
import Modal from './Modal.vue'
import {
  ComputerDesktopIcon,
  ChatBubbleLeftEllipsisIcon,
  GlobeAltIcon,
  InformationCircleIcon,
  TrashIcon
} from '@heroicons/vue/24/outline'

interface Props {
  setting?: any
}

const props = defineProps<Props>()

const notificationStore = useNotificationStore()

const selectedType = ref('browser')
const config = ref<Record<string, any>>({})
const sessionId = ref('')
const enabled = ref(true)
const customHeaders = ref<Array<{ key: string; value: string }>>([])
const saving = ref(false)
const testing = ref(false)

// 通知タイプ定義
const notificationTypes = [
  {
    id: 'browser',
    name: 'ブラウザ通知',
    description: 'デスクトップ通知を表示',
    icon: ComputerDesktopIcon,
    color: 'text-blue-600'
  },
  {
    id: 'slack',
    name: 'Slack',
    description: 'Slackチャンネルに通知',
    icon: ChatBubbleLeftEllipsisIcon,
    color: 'text-green-600'
  },
  {
    id: 'discord',
    name: 'Discord',
    description: 'Discordチャンネルに通知',
    icon: ChatBubbleLeftEllipsisIcon,
    color: 'text-purple-600'
  },
  {
    id: 'webhook',
    name: 'Webhook',
    description: '汎用Webhook通知',
    icon: GlobeAltIcon,
    color: 'text-gray-600'
  }
]

// 計算プロパティ
const isEditing = computed(() => !!props.setting)

const isConfigValid = computed(() => {
  switch (selectedType.value) {
    case 'browser':
      return true
    case 'slack':
    case 'discord':
      return !!config.value.webhook_url
    case 'webhook':
      return !!config.value.url
    default:
      return false
  }
})

const canSave = computed(() => isConfigValid.value)

const canTest = computed(() => selectedType.value !== 'browser')

// ヘッダー設定の監視
watch(
  customHeaders,
  (headers) => {
    const headersObj: Record<string, string> = {}
    headers.forEach(header => {
      if (header.key && header.value) {
        headersObj[header.key] = header.value
      }
    })
    config.value.headers = headersObj
  },
  { deep: true }
)

onMounted(() => {
  if (props.setting) {
    // 編集モードの場合、既存の設定を読み込み
    selectedType.value = props.setting.type
    config.value = { ...props.setting.config }
    sessionId.value = props.setting.session_id || ''
    enabled.value = props.setting.enabled
    
    // カスタムヘッダーの復元
    if (config.value.headers) {
      customHeaders.value = Object.entries(config.value.headers).map(([key, value]) => ({
        key,
        value: value as string
      }))
    }
  }
})

// メソッド
const addHeader = () => {
  customHeaders.value.push({ key: '', value: '' })
}

const removeHeader = (index: number) => {
  customHeaders.value.splice(index, 1)
}

const testNotification = async () => {
  testing.value = true
  try {
    await notificationStore.testNotification(
      selectedType.value,
      config.value,
      'これはテスト通知です'
    )
    alert('テスト通知を送信しました')
  } catch (error: any) {
    alert(`テスト送信エラー: ${error.message}`)
  } finally {
    testing.value = false
  }
}

const saveSetting = async () => {
  if (!canSave.value) return
  
  saving.value = true
  
  try {
    const settingData = {
      type: selectedType.value,
      config: config.value,
      enabled: enabled.value,
      session_id: sessionId.value || undefined
    }
    
    if (isEditing.value) {
      await notificationStore.updateSetting(props.setting.id, settingData)
    } else {
      await notificationStore.createSetting(settingData)
    }
    
    emit('saved')
  } catch (error: any) {
    alert(`保存エラー: ${error.message}`)
  } finally {
    saving.value = false
  }
}

// エミット
const emit = defineEmits<{
  close: []
  saved: []
}>()
</script>

<style scoped>
/* モーダル内のスタイル調整 */
.modal-content {
  max-width: 600px;
}
</style>