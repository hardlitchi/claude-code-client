<template>
  <div class="session-sharing h-full flex flex-col">
    <!-- ヘッダー -->
    <div class="sharing-header bg-gray-100 border-b p-3">
      <div class="flex items-center justify-between">
        <h3 class="text-sm font-medium text-gray-700">セッション共有</h3>
        <button
          @click="showShareModal = true"
          class="px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          ユーザーを招待
        </button>
      </div>
    </div>

    <!-- 参加者一覧 -->
    <div class="participants-section border-b">
      <div class="p-3">
        <h4 class="text-sm font-medium text-gray-700 mb-2 flex items-center">
          <UsersIcon class="w-4 h-4 mr-2" />
          参加者 ({{ participantCount }})
        </h4>
        
        <div v-if="participants.length === 0" class="text-xs text-gray-500">
          参加者はいません
        </div>
        
        <div v-else class="space-y-2">
          <div
            v-for="participant in participants"
            :key="participant.user.id"
            class="flex items-center space-x-3 p-2 bg-white rounded border"
          >
            <!-- ユーザーアバター -->
            <div class="flex-shrink-0">
              <div class="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
                <span class="text-white text-xs font-medium">
                  {{ getUserInitials(participant.user.username) }}
                </span>
              </div>
            </div>
            
            <!-- ユーザー情報 -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center space-x-2">
                <span class="text-sm font-medium text-gray-800">
                  {{ participant.user.username }}
                </span>
                <div 
                  class="w-2 h-2 rounded-full"
                  :class="isUserActive(participant) ? 'bg-green-500' : 'bg-gray-300'"
                  :title="isUserActive(participant) ? 'オンライン' : 'オフライン'"
                ></div>
              </div>
              
              <div class="text-xs text-gray-500">
                {{ formatLastSeen(participant.last_seen) }}
              </div>
              
              <!-- カーソル位置 -->
              <div v-if="participant.cursor_position" class="text-xs text-blue-600">
                {{ formatCursorPosition(participant.cursor_position) }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 共有設定一覧 -->
    <div class="shares-list flex-1 overflow-auto">
      <div class="p-3">
        <h4 class="text-sm font-medium text-gray-700 mb-2 flex items-center">
          <ShareIcon class="w-4 h-4 mr-2" />
          共有設定
        </h4>
        
        <div v-if="loading" class="text-center text-gray-500 py-4">
          読み込み中...
        </div>
        
        <div v-else-if="shares.length === 0" class="text-xs text-gray-500">
          共有設定はありません
        </div>
        
        <div v-else class="space-y-2">
          <div
            v-for="share in shares"
            :key="share.id"
            class="bg-white border rounded p-3"
          >
            <div class="flex items-start justify-between">
              <div class="flex-1">
                <!-- ユーザー情報 -->
                <div class="flex items-center space-x-2 mb-1">
                  <span class="text-sm font-medium text-gray-800">
                    {{ share.shared_with.username }}
                  </span>
                  <span 
                    class="text-xs px-2 py-1 rounded"
                    :class="getPermissionBadgeClass(share.permission_level)"
                  >
                    {{ getPermissionLabel(share.permission_level) }}
                  </span>
                </div>
                
                <!-- 共有日時・有効期限 -->
                <div class="text-xs text-gray-500 space-y-1">
                  <div>共有日時: {{ formatDate(share.created_at) }}</div>
                  <div v-if="share.expires_at">
                    有効期限: {{ formatDate(share.expires_at) }}
                    <span 
                      v-if="isExpiringSoon(share.expires_at)"
                      class="text-orange-600 ml-1"
                    >
                      (まもなく期限切れ)
                    </span>
                  </div>
                  <div v-else class="text-green-600">無期限</div>
                </div>
              </div>
              
              <!-- 操作ボタン -->
              <div class="flex items-center space-x-1 ml-3">
                <!-- 権限変更 -->
                <select
                  :value="share.permission_level"
                  @change="updatePermission(share.id, $event.target.value)"
                  class="text-xs border border-gray-300 rounded px-2 py-1"
                >
                  <option value="viewer">閲覧者</option>
                  <option value="collaborator">共同編集者</option>
                  <option value="admin">管理者</option>
                </select>
                
                <!-- 削除 -->
                <button
                  @click="revokeShare(share.id)"
                  class="p-1 text-red-500 hover:text-red-700"
                  title="共有を取り消し"
                >
                  <XMarkIcon class="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- アクティビティログ -->
    <div class="activities-section border-t">
      <div class="p-3">
        <h4 class="text-sm font-medium text-gray-700 mb-2 flex items-center">
          <ClockIcon class="w-4 h-4 mr-2" />
          アクティビティ
        </h4>
        
        <div class="max-h-32 overflow-auto space-y-1">
          <div
            v-for="activity in recentActivities"
            :key="activity.id"
            class="text-xs text-gray-600 flex items-start space-x-2"
          >
            <span class="font-medium">{{ activity.user.username }}:</span>
            <span>{{ formatActivity(activity) }}</span>
            <span class="text-gray-400 ml-auto">
              {{ formatTime(activity.timestamp) }}
            </span>
          </div>
          
          <div v-if="activities.length === 0" class="text-xs text-gray-500">
            アクティビティはありません
          </div>
        </div>
      </div>
    </div>

    <!-- 共有モーダル -->
    <ShareSessionModal
      v-if="showShareModal"
      :session-id="sessionId"
      @close="showShareModal = false"
      @shared="onSessionShared"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useCollaborationStore } from '@/stores/collaboration'
import { useWebSocketStore } from '@/stores/websocket'
import ShareSessionModal from './ShareSessionModal.vue'
import {
  UsersIcon,
  ShareIcon,
  ClockIcon,
  XMarkIcon
} from '@heroicons/vue/24/outline'

interface Props {
  sessionId: string
}

const props = defineProps<Props>()

const collaborationStore = useCollaborationStore()
const websocketStore = useWebSocketStore()

const loading = ref(false)
const showShareModal = ref(false)

// 計算プロパティ
const shares = computed(() => collaborationStore.sessionShares)
const participants = computed(() => collaborationStore.activeParticipants)
const participantCount = computed(() => collaborationStore.participantCount)
const activities = computed(() => collaborationStore.activities)

const recentActivities = computed(() => 
  activities.value.slice(0, 10) // 最新10件
)

// WebSocket メッセージ監視
watch(
  () => websocketStore.lastMessage,
  (message) => {
    if (message) {
      collaborationStore.handleWebSocketMessage(message)
    }
  }
)

onMounted(async () => {
  await loadData()
  
  // セッションに参加
  try {
    await collaborationStore.joinSession(props.sessionId)
  } catch (error) {
    console.warn('セッション参加に失敗:', error)
  }
})

// メソッド
const loadData = async () => {
  loading.value = true
  try {
    await Promise.all([
      collaborationStore.loadSessionShares(props.sessionId),
      collaborationStore.loadParticipants(props.sessionId),
      collaborationStore.loadActivities(props.sessionId, { limit: 20 })
    ])
  } catch (error: any) {
    console.error('データ読み込みエラー:', error)
  } finally {
    loading.value = false
  }
}

const updatePermission = async (shareId: number, newLevel: string) => {
  try {
    await collaborationStore.updateSharePermission(
      props.sessionId,
      shareId,
      newLevel as 'viewer' | 'collaborator' | 'admin'
    )
  } catch (error: any) {
    alert(`権限更新エラー: ${error.message}`)
  }
}

const revokeShare = async (shareId: number) => {
  if (!confirm('この共有設定を取り消しますか？')) {
    return
  }

  try {
    await collaborationStore.revokeShare(props.sessionId, shareId)
  } catch (error: any) {
    alert(`共有取り消しエラー: ${error.message}`)
  }
}

const onSessionShared = () => {
  showShareModal.value = false
  loadData()
}

// ユーティリティ関数
const getUserInitials = (username: string): string => {
  return username.substring(0, 2).toUpperCase()
}

const getPermissionLabel = (level: string): string => {
  return collaborationStore.getPermissionLabel(level)
}

const getPermissionBadgeClass = (level: string): string => {
  const baseClass = 'px-2 py-1 rounded text-xs'
  const colorMap: Record<string, string> = {
    viewer: 'bg-gray-100 text-gray-700',
    collaborator: 'bg-blue-100 text-blue-700',
    admin: 'bg-purple-100 text-purple-700'
  }
  return `${baseClass} ${colorMap[level] || colorMap.viewer}`
}

const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleString('ja-JP')
}

const formatTime = (dateString: string): string => {
  const date = new Date(dateString)
  const now = new Date()
  const diffMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60))
  
  if (diffMinutes < 1) return 'たった今'
  if (diffMinutes < 60) return `${diffMinutes}分前`
  if (diffMinutes < 1440) return `${Math.floor(diffMinutes / 60)}時間前`
  return date.toLocaleDateString('ja-JP')
}

const formatLastSeen = (dateString: string): string => {
  const date = new Date(dateString)
  const now = new Date()
  const diffMinutes = Math.floor((now.getTime() - date.getTime()) / (1000 * 60))
  
  if (diffMinutes < 1) return 'アクティブ'
  if (diffMinutes < 5) return `${diffMinutes}分前にアクティブ`
  return `最終: ${date.toLocaleTimeString('ja-JP')}`
}

const formatCursorPosition = (cursor: any): string => {
  if (cursor.file_path) {
    return `${cursor.file_path} (${cursor.line}:${cursor.column})`
  }
  return `行 ${cursor.line}, 列 ${cursor.column}`
}

const formatActivity = (activity: any): string => {
  return collaborationStore.formatActivity(activity)
}

const isUserActive = (participant: any): boolean => {
  return collaborationStore.isUserActive(participant)
}

const isExpiringSoon = (expiryDate: string): boolean => {
  const expiry = new Date(expiryDate)
  const now = new Date()
  const diffHours = (expiry.getTime() - now.getTime()) / (1000 * 60 * 60)
  return diffHours < 24 && diffHours > 0
}
</script>

<style scoped>
.session-sharing {
  @apply bg-gray-50;
}
</style>