<template>
  <Modal @close="$emit('close')">
    <template #header>
      <h3 class="text-lg font-medium">セッションを共有</h3>
    </template>
    
    <template #body>
      <div class="space-y-6">
        <!-- ユーザー名入力 -->
        <div>
          <label for="username" class="block text-sm font-medium text-gray-700 mb-2">
            招待するユーザー名 <span class="text-red-500">*</span>
          </label>
          <input
            id="username"
            v-model="username"
            type="text"
            class="w-full p-3 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
            placeholder="ユーザー名を入力"
            :class="{ 'border-red-500': errors.username }"
            @input="validateUsername"
          />
          <p v-if="errors.username" class="mt-1 text-sm text-red-600">
            {{ errors.username }}
          </p>
        </div>

        <!-- 権限レベル選択 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-3">
            権限レベル
          </label>
          
          <div class="space-y-3">
            <div
              v-for="permission in permissionLevels"
              :key="permission.level"
              class="border rounded-lg p-3 cursor-pointer transition-colors"
              :class="{
                'border-blue-500 bg-blue-50': selectedPermission === permission.level,
                'border-gray-200 hover:border-gray-300': selectedPermission !== permission.level
              }"
              @click="selectedPermission = permission.level"
            >
              <div class="flex items-start space-x-3">
                <div class="flex-shrink-0 mt-1">
                  <div 
                    class="w-3 h-3 rounded-full border-2"
                    :class="{
                      'border-blue-500 bg-blue-500': selectedPermission === permission.level,
                      'border-gray-300': selectedPermission !== permission.level
                    }"
                  ></div>
                </div>
                
                <div class="flex-1">
                  <div class="flex items-center space-x-2">
                    <component 
                      :is="permission.icon"
                      class="w-5 h-5"
                      :class="permission.color"
                    />
                    <h4 class="font-medium text-gray-800">{{ permission.name }}</h4>
                  </div>
                  
                  <p class="text-sm text-gray-600 mt-1">{{ permission.description }}</p>
                  
                  <div class="mt-2">
                    <h5 class="text-xs font-medium text-gray-700 mb-1">できること:</h5>
                    <ul class="text-xs text-gray-600 space-y-1">
                      <li v-for="capability in permission.capabilities" :key="capability">
                        • {{ capability }}
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 有効期限設定 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-3">
            有効期限
          </label>
          
          <div class="space-y-2">
            <label class="flex items-center">
              <input
                v-model="expiryOption"
                type="radio"
                value="unlimited"
                class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span class="ml-2 text-sm text-gray-700">無期限</span>
            </label>
            
            <label class="flex items-center">
              <input
                v-model="expiryOption"
                type="radio"
                value="hours"
                class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span class="ml-2 text-sm text-gray-700">時間指定</span>
            </label>
          </div>
          
          <div v-if="expiryOption === 'hours'" class="mt-3">
            <div class="flex items-center space-x-2">
              <input
                v-model.number="expiryHours"
                type="number"
                min="1"
                max="8760"
                class="w-20 p-2 text-sm border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
              />
              <span class="text-sm text-gray-700">時間後に期限切れ</span>
            </div>
            <p class="mt-1 text-xs text-gray-500">
              期限: {{ formatExpiryDate() }}
            </p>
          </div>
        </div>

        <!-- セキュリティ注意事項 -->
        <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
          <div class="flex items-start space-x-2">
            <ExclamationTriangleIcon class="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div class="text-sm">
              <h4 class="font-medium text-yellow-800 mb-1">セキュリティに関する注意</h4>
              <ul class="text-yellow-700 space-y-1 text-xs">
                <li>• 信頼できるユーザーとのみセッションを共有してください</li>
                <li>• 共同編集者・管理者はファイルの変更や削除ができます</li>
                <li>• セッションの共有はいつでも取り消すことができます</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </template>
    
    <template #footer>
      <div class="flex justify-end space-x-3">
        <button
          @click="$emit('close')"
          class="px-4 py-2 text-gray-600 hover:text-gray-800"
          :disabled="sharing"
        >
          キャンセル
        </button>
        <button
          @click="shareSession"
          :disabled="!canShare || sharing"
          class="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {{ sharing ? '共有中...' : '共有する' }}
        </button>
      </div>
    </template>
  </Modal>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useCollaborationStore } from '@/stores/collaboration'
import Modal from './Modal.vue'
import {
  EyeIcon,
  PencilSquareIcon,
  ShieldCheckIcon,
  ExclamationTriangleIcon
} from '@heroicons/vue/24/outline'

interface Props {
  sessionId: string
}

const props = defineProps<Props>()

const collaborationStore = useCollaborationStore()

const username = ref('')
const selectedPermission = ref<'viewer' | 'collaborator' | 'admin'>('collaborator')
const expiryOption = ref<'unlimited' | 'hours'>('unlimited')
const expiryHours = ref(24)
const sharing = ref(false)

const errors = ref({
  username: ''
})

// 権限レベル定義
const permissionLevels = [
  {
    level: 'viewer' as const,
    name: '閲覧者',
    description: 'ファイルの表示とチャットのみ可能',
    icon: EyeIcon,
    color: 'text-gray-600',
    capabilities: [
      'ファイルの閲覧',
      'チャットへの参加',
      'カーソル位置の表示'
    ]
  },
  {
    level: 'collaborator' as const,
    name: '共同編集者',
    description: 'ファイルの編集とプロジェクト操作が可能',
    icon: PencilSquareIcon,
    color: 'text-blue-600',
    capabilities: [
      'ファイルの編集・作成・削除',
      'プロジェクトのビルド・デプロイ',
      'チャットへの参加',
      'すべての閲覧者権限'
    ]
  },
  {
    level: 'admin' as const,
    name: '管理者',
    description: 'セッションの完全な管理権限',
    icon: ShieldCheckIcon,
    color: 'text-purple-600',
    capabilities: [
      'セッション設定の変更',
      '他ユーザーの招待・除名',
      'セッションの削除',
      'すべての共同編集者権限'
    ]
  }
]

// 計算プロパティ
const canShare = computed(() => {
  return username.value.trim() && !errors.value.username
})

// メソッド
const validateUsername = () => {
  errors.value.username = ''
  
  const name = username.value.trim()
  
  if (!name) {
    errors.value.username = 'ユーザー名は必須です'
    return
  }
  
  if (name.length < 2) {
    errors.value.username = 'ユーザー名は2文字以上である必要があります'
    return
  }
  
  if (name.length > 50) {
    errors.value.username = 'ユーザー名は50文字以下である必要があります'
    return
  }
  
  // 英数字、アンダースコア、ハイフンのみ許可
  const validPattern = /^[a-zA-Z0-9_-]+$/
  if (!validPattern.test(name)) {
    errors.value.username = '英数字、アンダースコア、ハイフンのみ使用可能です'
    return
  }
}

const shareSession = async () => {
  // 最終バリデーション
  validateUsername()
  
  if (!canShare.value) {
    return
  }
  
  sharing.value = true
  
  try {
    const expiresHours = expiryOption.value === 'hours' ? expiryHours.value : undefined
    
    await collaborationStore.shareSession(
      props.sessionId,
      username.value.trim(),
      selectedPermission.value,
      expiresHours
    )
    
    emit('shared', {
      username: username.value.trim(),
      permission: selectedPermission.value,
      expires_hours: expiresHours
    })
    
  } catch (error: any) {
    alert(`共有エラー: ${error.message}`)
  } finally {
    sharing.value = false
  }
}

const formatExpiryDate = (): string => {
  if (expiryOption.value !== 'hours') return ''
  
  const expiryDate = new Date(Date.now() + expiryHours.value * 60 * 60 * 1000)
  return expiryDate.toLocaleString('ja-JP')
}

// エミット
const emit = defineEmits<{
  close: []
  shared: [data: {
    username: string
    permission: string
    expires_hours?: number
  }]
}>()
</script>

<style scoped>
/* モーダル内のスタイル調整 */
.modal-content {
  max-width: 600px;
}
</style>