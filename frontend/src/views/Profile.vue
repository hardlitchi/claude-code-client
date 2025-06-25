<template>
  <div class="min-h-screen bg-gray-50">
    <!-- ヘッダー -->
    <header class="bg-white shadow">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center py-6">
          <h1 class="text-2xl font-bold text-gray-900">プロフィール</h1>
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
          <div class="px-4 py-5 sm:p-6">
            <!-- プロフィール情報 -->
            <div class="space-y-8">
              <!-- アバターセクション -->
              <div>
                <h3 class="text-lg font-medium text-gray-900">プロフィール画像</h3>
                <div class="mt-2 flex items-center space-x-5">
                  <div class="relative">
                    <img
                      class="h-24 w-24 rounded-full"
                      :src="profile.avatar || 'https://via.placeholder.com/150'"
                      alt="プロフィール画像"
                    />
                    <button
                      @click="changeAvatar"
                      class="absolute bottom-0 right-0 bg-white rounded-full p-1 shadow-lg hover:bg-gray-100"
                    >
                      <svg class="h-5 w-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                    </button>
                  </div>
                  <div>
                    <button
                      @click="changeAvatar"
                      class="px-3 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                    >
                      画像を変更
                    </button>
                  </div>
                </div>
              </div>

              <!-- 基本情報フォーム -->
              <div class="grid grid-cols-1 gap-6 sm:grid-cols-2">
                <div>
                  <label for="username" class="block text-sm font-medium text-gray-700">
                    ユーザー名
                  </label>
                  <input
                    type="text"
                    id="username"
                    v-model="profile.username"
                    class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label for="email" class="block text-sm font-medium text-gray-700">
                    メールアドレス
                  </label>
                  <input
                    type="email"
                    id="email"
                    v-model="profile.email"
                    class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label for="displayName" class="block text-sm font-medium text-gray-700">
                    表示名
                  </label>
                  <input
                    type="text"
                    id="displayName"
                    v-model="profile.displayName"
                    class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label for="organization" class="block text-sm font-medium text-gray-700">
                    組織
                  </label>
                  <input
                    type="text"
                    id="organization"
                    v-model="profile.organization"
                    placeholder="会社名や組織名"
                    class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>

                <div class="sm:col-span-2">
                  <label for="bio" class="block text-sm font-medium text-gray-700">
                    自己紹介
                  </label>
                  <textarea
                    id="bio"
                    v-model="profile.bio"
                    rows="3"
                    placeholder="簡単な自己紹介を入力してください"
                    class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
              </div>

              <!-- アカウント情報 -->
              <div class="border-t border-gray-200 pt-8">
                <h3 class="text-lg font-medium text-gray-900 mb-4">アカウント情報</h3>
                <dl class="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
                  <div>
                    <dt class="text-sm font-medium text-gray-500">アカウント作成日</dt>
                    <dd class="mt-1 text-sm text-gray-900">{{ formatDate(profile.createdAt) }}</dd>
                  </div>
                  <div>
                    <dt class="text-sm font-medium text-gray-500">最終ログイン</dt>
                    <dd class="mt-1 text-sm text-gray-900">{{ formatDate(profile.lastLogin) }}</dd>
                  </div>
                  <div>
                    <dt class="text-sm font-medium text-gray-500">アカウントタイプ</dt>
                    <dd class="mt-1 text-sm text-gray-900">
                      <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        {{ profile.accountType }}
                      </span>
                    </dd>
                  </div>
                  <div>
                    <dt class="text-sm font-medium text-gray-500">使用容量</dt>
                    <dd class="mt-1 text-sm text-gray-900">
                      {{ profile.storageUsed }} / {{ profile.storageLimit }}
                    </dd>
                  </div>
                </dl>
              </div>

              <!-- 危険な操作 -->
              <div class="border-t border-gray-200 pt-8">
                <h3 class="text-lg font-medium text-gray-900 mb-4">危険な操作</h3>
                <div class="space-y-4">
                  <div class="flex items-center justify-between">
                    <div>
                      <h4 class="text-sm font-medium text-gray-900">アカウントを無効化</h4>
                      <p class="text-sm text-gray-500">一時的にアカウントを無効化します</p>
                    </div>
                    <button
                      @click="deactivateAccount"
                      class="px-4 py-2 border border-red-300 rounded-md text-sm font-medium text-red-700 hover:bg-red-50"
                    >
                      無効化
                    </button>
                  </div>
                  <div class="flex items-center justify-between">
                    <div>
                      <h4 class="text-sm font-medium text-gray-900">アカウントを削除</h4>
                      <p class="text-sm text-gray-500">アカウントとすべてのデータを完全に削除します</p>
                    </div>
                    <button
                      @click="deleteAccount"
                      class="px-4 py-2 bg-red-600 text-white rounded-md text-sm font-medium hover:bg-red-700"
                    >
                      削除
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 保存ボタン -->
          <div class="bg-gray-50 px-4 py-3 sm:px-6 flex justify-end">
            <button
              @click="saveProfile"
              class="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
            >
              プロフィールを保存
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

// プロフィールデータ
const profile = reactive({
  username: authStore.user?.username || 'user123',
  email: authStore.user?.email || 'user@example.com',
  displayName: '山田 太郎',
  organization: '',
  bio: '',
  avatar: '',
  createdAt: new Date('2024-01-01'),
  lastLogin: new Date(),
  accountType: 'Pro',
  storageUsed: '2.5 GB',
  storageLimit: '10 GB'
})

// 日付フォーマット
const formatDate = (date: Date) => {
  return new Intl.DateTimeFormat('ja-JP', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date)
}

// ログアウト処理
const handleLogout = async () => {
  await authStore.logout()
  router.push('/login')
}

// アバター変更
const changeAvatar = () => {
  // TODO: ファイルアップロード機能の実装
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = 'image/*'
  input.onchange = (e) => {
    const file = (e.target as HTMLInputElement).files?.[0]
    if (file) {
      // TODO: ファイルアップロード処理
      console.log('選択されたファイル:', file)
      // 仮の実装：DataURLとして設定
      const reader = new FileReader()
      reader.onload = (e) => {
        profile.avatar = e.target?.result as string
      }
      reader.readAsDataURL(file)
    }
  }
  input.click()
}

// プロフィール保存
const saveProfile = async () => {
  try {
    // TODO: API呼び出し
    console.log('プロフィールを保存:', profile)
    alert('プロフィールを保存しました')
  } catch (error) {
    console.error('プロフィール保存エラー:', error)
    alert('プロフィールの保存に失敗しました')
  }
}

// アカウント無効化
const deactivateAccount = async () => {
  if (!confirm('アカウントを無効化しますか？いつでも再度有効化できます。')) {
    return
  }

  try {
    // TODO: API呼び出し
    console.log('アカウントを無効化')
    alert('アカウントを無効化しました')
    await handleLogout()
  } catch (error) {
    console.error('アカウント無効化エラー:', error)
    alert('アカウントの無効化に失敗しました')
  }
}

// アカウント削除
const deleteAccount = async () => {
  if (!confirm('本当にアカウントを削除しますか？この操作は取り消せません。')) {
    return
  }

  if (!confirm('最終確認：すべてのデータが完全に削除されます。本当によろしいですか？')) {
    return
  }

  try {
    // TODO: API呼び出し
    console.log('アカウントを削除')
    alert('アカウントを削除しました')
    await handleLogout()
  } catch (error) {
    console.error('アカウント削除エラー:', error)
    alert('アカウントの削除に失敗しました')
  }
}
</script>