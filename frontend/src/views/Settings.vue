<template>
  <div class="min-h-screen bg-gray-50">
    <!-- ヘッダー -->
    <header class="bg-white shadow">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center py-6">
          <h1 class="text-2xl font-bold text-gray-900">設定</h1>
          <div class="flex items-center space-x-4">
            <router-link to="/dashboard" class="text-gray-500 hover:text-gray-700">
              ダッシュボードに戻る
            </router-link>
            <button
              @click="handleLogout"
              class="text-gray-500 hover:text-gray-700"
            >
              ログアウト
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- メインコンテンツ -->
    <main class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
      <div class="px-4 py-6 sm:px-0">
        <div class="bg-white overflow-hidden shadow rounded-lg">
          <!-- タブナビゲーション -->
          <div class="border-b border-gray-200">
            <nav class="-mb-px flex" aria-label="Tabs">
              <button
                v-for="tab in tabs"
                :key="tab.id"
                @click="activeTab = tab.id"
                :class="[
                  activeTab === tab.id
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
                  'whitespace-nowrap py-4 px-6 border-b-2 font-medium text-sm cursor-pointer'
                ]"
              >
                {{ tab.name }}
              </button>
            </nav>
          </div>

          <!-- タブコンテンツ -->
          <div class="p-6">
            <!-- 一般設定 -->
            <div v-if="activeTab === 'general'" class="space-y-6">
              <div>
                <h3 class="text-lg font-medium text-gray-900">一般設定</h3>
                <p class="mt-1 text-sm text-gray-600">
                  アプリケーションの基本的な設定を管理します。
                </p>
              </div>

              <div class="space-y-4">
                <div>
                  <label class="block text-sm font-medium text-gray-700">
                    言語設定
                  </label>
                  <select
                    v-model="settings.language"
                    class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                  >
                    <option value="ja">日本語</option>
                    <option value="en">English</option>
                  </select>
                </div>

                <div>
                  <label class="block text-sm font-medium text-gray-700">
                    テーマ
                  </label>
                  <select
                    v-model="settings.theme"
                    class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                  >
                    <option value="light">ライト</option>
                    <option value="dark">ダーク</option>
                    <option value="auto">自動</option>
                  </select>
                </div>

                <div>
                  <label class="block text-sm font-medium text-gray-700">
                    タイムゾーン
                  </label>
                  <select
                    v-model="settings.timezone"
                    class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                  >
                    <option value="Asia/Tokyo">東京 (GMT+9)</option>
                    <option value="UTC">UTC</option>
                    <option value="America/New_York">ニューヨーク (GMT-5)</option>
                  </select>
                </div>
              </div>
            </div>

            <!-- 通知設定 -->
            <div v-if="activeTab === 'notifications'" class="space-y-6">
              <div>
                <h3 class="text-lg font-medium text-gray-900">通知設定</h3>
                <p class="mt-1 text-sm text-gray-600">
                  通知の受信方法とタイミングを設定します。
                </p>
              </div>

              <NotificationSettings />
            </div>

            <!-- セキュリティ設定 -->
            <div v-if="activeTab === 'security'" class="space-y-6">
              <div>
                <h3 class="text-lg font-medium text-gray-900">セキュリティ</h3>
                <p class="mt-1 text-sm text-gray-600">
                  アカウントのセキュリティ設定を管理します。
                </p>
              </div>

              <div class="space-y-4">
                <div>
                  <h4 class="text-sm font-medium text-gray-900">パスワード変更</h4>
                  <div class="mt-2 space-y-2">
                    <input
                      type="password"
                      v-model="passwordForm.current"
                      placeholder="現在のパスワード"
                      class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    />
                    <input
                      type="password"
                      v-model="passwordForm.new"
                      placeholder="新しいパスワード"
                      class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    />
                    <input
                      type="password"
                      v-model="passwordForm.confirm"
                      placeholder="新しいパスワード（確認）"
                      class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    />
                    <button
                      @click="changePassword"
                      class="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
                    >
                      パスワードを変更
                    </button>
                  </div>
                </div>

                <div>
                  <h4 class="text-sm font-medium text-gray-900">二要素認証</h4>
                  <div class="mt-2 flex items-center justify-between">
                    <span class="text-sm text-gray-600">
                      二要素認証を有効にしてアカウントを保護します
                    </span>
                    <button
                      @click="toggle2FA"
                      :class="[
                        settings.twoFactorEnabled
                          ? 'bg-indigo-600'
                          : 'bg-gray-200',
                        'relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2'
                      ]"
                    >
                      <span
                        :class="[
                          settings.twoFactorEnabled
                            ? 'translate-x-5'
                            : 'translate-x-0',
                          'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out'
                        ]"
                      />
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- API設定 -->
            <div v-if="activeTab === 'api'" class="space-y-6">
              <div>
                <h3 class="text-lg font-medium text-gray-900">API設定</h3>
                <p class="mt-1 text-sm text-gray-600">
                  外部サービスとの連携設定を管理します。
                </p>
              </div>

              <div class="space-y-4">
                <div>
                  <h4 class="text-sm font-medium text-gray-900">APIキー</h4>
                  <div class="mt-2">
                    <div class="flex items-center space-x-2">
                      <input
                        type="text"
                        :value="maskedApiKey"
                        readonly
                        class="block flex-1 px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
                      />
                      <button
                        @click="regenerateApiKey"
                        class="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
                      >
                        再生成
                      </button>
                    </div>
                    <p class="mt-1 text-xs text-gray-500">
                      APIキーは一度だけ表示されます。安全に保管してください。
                    </p>
                  </div>
                </div>

                <div>
                  <h4 class="text-sm font-medium text-gray-900">Webhook URL</h4>
                  <div class="mt-2 space-y-2">
                    <input
                      type="url"
                      v-model="settings.webhookUrl"
                      placeholder="https://example.com/webhook"
                      class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                    />
                    <p class="text-xs text-gray-500">
                      イベント通知を受け取るWebhook URLを設定します
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 保存ボタン -->
          <div class="bg-gray-50 px-6 py-3 flex justify-end">
            <button
              @click="saveSettings"
              class="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
            >
              設定を保存
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import NotificationSettings from '@/components/NotificationSettings.vue'

const router = useRouter()
const authStore = useAuthStore()

// タブ定義
const tabs = [
  { id: 'general', name: '一般' },
  { id: 'notifications', name: '通知' },
  { id: 'security', name: 'セキュリティ' },
  { id: 'api', name: 'API' }
]

const activeTab = ref('general')

// 設定データ
const settings = reactive({
  language: 'ja',
  theme: 'light',
  timezone: 'Asia/Tokyo',
  twoFactorEnabled: false,
  webhookUrl: '',
  apiKey: 'sk_live_xxxxxxxxxxxxx'
})

// パスワード変更フォーム
const passwordForm = reactive({
  current: '',
  new: '',
  confirm: ''
})

// マスクされたAPIキー
const maskedApiKey = computed(() => {
  const key = settings.apiKey
  if (key.length <= 8) return key
  return `${key.substring(0, 7)}...${key.substring(key.length - 4)}`
})

// ログアウト処理
const handleLogout = async () => {
  await authStore.logout()
  router.push('/login')
}

// パスワード変更
const changePassword = async () => {
  if (passwordForm.new !== passwordForm.confirm) {
    alert('新しいパスワードが一致しません')
    return
  }

  try {
    // TODO: API呼び出し
    console.log('パスワード変更:', passwordForm)
    alert('パスワードを変更しました')
    passwordForm.current = ''
    passwordForm.new = ''
    passwordForm.confirm = ''
  } catch (error) {
    console.error('パスワード変更エラー:', error)
    alert('パスワードの変更に失敗しました')
  }
}

// 二要素認証の切り替え
const toggle2FA = () => {
  settings.twoFactorEnabled = !settings.twoFactorEnabled
}

// APIキーの再生成
const regenerateApiKey = async () => {
  if (!confirm('APIキーを再生成しますか？既存のキーは無効になります。')) {
    return
  }

  try {
    // TODO: API呼び出し
    settings.apiKey = 'sk_live_' + Math.random().toString(36).substring(2, 15)
    alert('新しいAPIキーが生成されました')
  } catch (error) {
    console.error('APIキー再生成エラー:', error)
    alert('APIキーの再生成に失敗しました')
  }
}

// 設定の保存
const saveSettings = async () => {
  try {
    // TODO: API呼び出し
    console.log('設定を保存:', settings)
    alert('設定を保存しました')
  } catch (error) {
    console.error('設定保存エラー:', error)
    alert('設定の保存に失敗しました')
  }
}
</script>