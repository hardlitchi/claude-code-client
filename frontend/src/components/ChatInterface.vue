<template>
  <div class="chat-interface flex flex-col h-full">
    <!-- チャット履歴 -->
    <div class="chat-history flex-1 overflow-y-auto p-4 space-y-4">
      <div
        v-for="message in chatHistory"
        :key="message.id"
        :class="[
          'message',
          message.sender === 'user' ? 'user-message' : 'claude-message'
        ]"
      >
        <div class="message-content">
          <div class="message-header">
            <span class="sender">
              {{ message.sender === 'user' ? 'あなた' : 'Claude' }}
            </span>
            <span class="timestamp">
              {{ formatTimestamp(message.timestamp) }}
            </span>
            <span v-if="message.model" class="model">
              ({{ message.model }})
            </span>
          </div>
          <div class="message-text">
            {{ message.message }}
          </div>
        </div>
      </div>
      
      <!-- 接続ステータス -->
      <div v-if="!isSocketConnected" class="connection-status error">
        <span class="status-icon">⚠️</span>
        WebSocket接続が切断されています
        <span v-if="reconnectAttempts > 0">
          (再接続試行: {{ reconnectAttempts }}/{{ maxReconnectAttempts }})
        </span>
      </div>
      
      <!-- ローディング状態 -->
      <div v-if="isWaitingForResponse" class="loading-message">
        <div class="loading-dots">
          <span></span><span></span><span></span>
        </div>
        Claude が入力中...
      </div>
    </div>
    
    <!-- メッセージ入力 -->
    <div class="message-input-container p-4 border-t">
      <div class="input-wrapper flex space-x-2">
        <textarea
          v-model="newMessage"
          @keydown.enter.exact.prevent="sendMessage"
          @keydown.enter.shift.exact="newMessage += '\n'"
          placeholder="Claudeにメッセージを送信..."
          class="message-input flex-1 p-3 border rounded-lg resize-none"
          rows="3"
          :disabled="!isSocketConnected"
        ></textarea>
        <button
          @click="sendMessage"
          :disabled="!canSendMessage"
          class="send-button px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
        >
          送信
        </button>
      </div>
      <div class="input-hint text-sm text-gray-500 mt-2">
        Enter: 送信 | Shift+Enter: 改行 | 現在の接続状態: 
        <span :class="connectionStatusClass">
          {{ connectionStatusText }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useWebSocketStore } from '../stores/websocket'

const websocketStore = useWebSocketStore()

// データ
const newMessage = ref('')
const isWaitingForResponse = ref(false)
const maxReconnectAttempts = 5

// 算出プロパティ
const chatHistory = computed(() => websocketStore.chatHistory)
const isSocketConnected = computed(() => websocketStore.isSocketConnected)
const reconnectAttempts = computed(() => websocketStore.reconnectAttempts)

const canSendMessage = computed(() => {
  return isSocketConnected.value && newMessage.value.trim().length > 0 && !isWaitingForResponse.value
})

const connectionStatusClass = computed(() => {
  return isSocketConnected.value ? 'text-green-600' : 'text-red-600'
})

const connectionStatusText = computed(() => {
  return isSocketConnected.value ? '接続中' : '切断中'
})

// メソッド
const sendMessage = async () => {
  if (!canSendMessage.value) return
  
  const message = newMessage.value.trim()
  newMessage.value = ''
  isWaitingForResponse.value = true
  
  try {
    websocketStore.sendChatMessage(message)
    // レスポンス待ちのタイムアウト設定（30秒）
    setTimeout(() => {
      isWaitingForResponse.value = false
    }, 30000)
  } catch (error) {
    console.error('メッセージ送信エラー:', error)
    isWaitingForResponse.value = false
  }
}

const formatTimestamp = (timestamp: string) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('ja-JP', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// ライフサイクル
onMounted(() => {
  // 新しいメッセージを監視してレスポンス待ち状態を解除
  websocketStore.$subscribe((mutation, state) => {
    if (mutation.events?.type === 'add' && state.messages.length > 0) {
      const lastMessage = state.messages[state.messages.length - 1]
      if (lastMessage.sender === 'claude') {
        isWaitingForResponse.value = false
      }
    }
  })
})

onUnmounted(() => {
  // コンポーネントが破棄される際のクリーンアップは websocket store で管理
})
</script>

<style scoped>
.chat-interface {
  background-color: #f8fafc;
}

.chat-history {
  background-color: white;
}

.message {
  margin-bottom: 1rem;
}

.user-message {
  display: flex;
  justify-content: flex-end;
}

.user-message .message-content {
  background-color: #3b82f6;
  color: white;
  max-width: 70%;
  padding: 0.75rem 1rem;
  border-radius: 1rem 1rem 0.25rem 1rem;
}

.claude-message {
  display: flex;
  justify-content: flex-start;
}

.claude-message .message-content {
  background-color: #f1f5f9;
  color: #1e293b;
  max-width: 70%;
  padding: 0.75rem 1rem;
  border-radius: 1rem 1rem 1rem 0.25rem;
  border: 1px solid #e2e8f0;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  margin-bottom: 0.25rem;
  opacity: 0.8;
}

.sender {
  font-weight: 600;
}

.timestamp {
  color: #64748b;
}

.model {
  color: #64748b;
  font-style: italic;
}

.message-text {
  line-height: 1.5;
  white-space: pre-wrap;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
}

.connection-status.error {
  background-color: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
}

.loading-message {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background-color: #f1f5f9;
  border-radius: 1rem 1rem 1rem 0.25rem;
  border: 1px solid #e2e8f0;
  max-width: 70%;
  color: #64748b;
  font-style: italic;
}

.loading-dots {
  display: flex;
  gap: 0.25rem;
}

.loading-dots span {
  width: 0.5rem;
  height: 0.5rem;
  background-color: #94a3b8;
  border-radius: 50%;
  animation: pulse 1.4s ease-in-out infinite both;
}

.loading-dots span:nth-child(1) {
  animation-delay: -0.32s;
}

.loading-dots span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes pulse {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

.message-input-container {
  background-color: white;
  border-top: 1px solid #e2e8f0;
}

.message-input {
  border: 1px solid #d1d5db;
  transition: border-color 0.2s;
}

.message-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.message-input:disabled {
  background-color: #f9fafb;
  color: #9ca3af;
}

.send-button {
  transition: background-color 0.2s;
  min-width: 5rem;
}

.input-hint {
  margin-top: 0.5rem;
}
</style>
