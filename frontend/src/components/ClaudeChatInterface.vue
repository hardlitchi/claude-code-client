<template>
  <div class="claude-chat-interface flex flex-col h-full">
    <!-- Claude セッション状態 -->
    <div class="session-status p-3 bg-gray-50 border-b">
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-3">
          <div :class="[
            'status-indicator w-3 h-3 rounded-full',
            claudeStore.isConnected ? 'bg-green-500' : 'bg-red-500'
          ]"></div>
          <span class="font-medium">
            Claude Code セッション
          </span>
          <span v-if="claudeStore.sessionStatus" class="text-sm text-gray-600">
            ({{ claudeStore.sessionStatus.message_count }} メッセージ)
          </span>
        </div>
        <div class="flex space-x-2">
          <button
            v-if="!claudeStore.isConnected"
            @click="startSession"
            :disabled="claudeStore.isLoading"
            class="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-300"
          >
            開始
          </button>
          <button
            v-else
            @click="stopSession"
            :disabled="claudeStore.isLoading"
            class="px-3 py-1 text-sm bg-red-500 text-white rounded hover:bg-red-600 disabled:bg-gray-300"
          >
            停止
          </button>
          <button
            @click="toggleStreamMode"
            class="px-3 py-1 text-sm border rounded hover:bg-gray-50"
            :class="streamMode ? 'border-blue-500 text-blue-600' : 'border-gray-300'"
          >
            {{ streamMode ? 'Stream' : 'Normal' }}
          </button>
        </div>
      </div>
    </div>

    <!-- チャット履歴 -->
    <div class="chat-history flex-1 overflow-y-auto p-4 space-y-4" ref="chatHistoryEl">
      <div
        v-for="(message, index) in claudeStore.messages"
        :key="index"
        :class="[
          'message',
          message.sender === 'user' ? 'user-message' : 'other-message'
        ]"
      >
        <div class="message-content">
          <div class="message-header">
            <span class="sender">
              {{ getSenderLabel(message.sender) }}
            </span>
            <span class="timestamp">
              {{ formatTimestamp(message.timestamp) }}
            </span>
          </div>
          <div class="message-text" v-html="formatMessageContent(message.content)"></div>
        </div>
      </div>

      <!-- ローディング状態 -->
      <div v-if="claudeStore.isLoading && streamMode" class="loading-message">
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
          placeholder="Claude Code にメッセージを送信..."
          class="message-input flex-1 p-3 border rounded-lg resize-none"
          rows="3"
          :disabled="!claudeStore.isConnected || claudeStore.isLoading"
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
        Enter: 送信 | Shift+Enter: 改行 | モード: {{ streamMode ? 'ストリーミング' : '通常' }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useClaudeStore } from '../stores/claude'
import { useRoute } from 'vue-router'

const claudeStore = useClaudeStore()
const route = useRoute()

// データ
const newMessage = ref('')
const streamMode = ref(true)
const chatHistoryEl = ref<HTMLElement>()

// 算出プロパティ
const currentSessionId = computed(() => route.params.sessionId as string)

const canSendMessage = computed(() => {
  return claudeStore.isConnected && 
         newMessage.value.trim().length > 0 && 
         !claudeStore.isLoading
})

// メソッド
const startSession = async () => {
  try {
    await claudeStore.startSession(currentSessionId.value)
    await loadMessages()
  } catch (error) {
    console.error('Claude セッション開始エラー:', error)
  }
}

const stopSession = async () => {
  try {
    await claudeStore.stopSession(currentSessionId.value)
  } catch (error) {
    console.error('Claude セッション停止エラー:', error)
  }
}

const sendMessage = async () => {
  if (!canSendMessage.value) return
  
  const message = newMessage.value.trim()
  newMessage.value = ''
  
  try {
    if (streamMode.value) {
      await claudeStore.sendMessageStream(
        currentSessionId.value,
        message,
        (chunk: string) => {
          // ストリーミングチャンクの処理
          scrollToBottom()
        }
      )
    } else {
      await claudeStore.sendMessage(currentSessionId.value, message)
    }
    
    scrollToBottom()
  } catch (error) {
    console.error('メッセージ送信エラー:', error)
  }
}

const loadMessages = async () => {
  try {
    await claudeStore.fetchMessages(currentSessionId.value)
    await nextTick()
    scrollToBottom()
  } catch (error) {
    console.error('メッセージ読み込みエラー:', error)
  }
}

const toggleStreamMode = () => {
  streamMode.value = !streamMode.value
}

const getSenderLabel = (sender: string) => {
  switch (sender) {
    case 'user': return 'あなた'
    case 'claude': return 'Claude'
    case 'system': return 'システム'
    case 'error': return 'エラー'
    default: return sender
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

const formatMessageContent = (content: string) => {
  // 簡単なマークダウン風の整形
  return content
    .replace(/\n/g, '<br>')
    .replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
    .replace(/```([\s\S]*?)```/g, '<pre class="code-block"><code>$1</code></pre>')
}

const scrollToBottom = () => {
  nextTick(() => {
    if (chatHistoryEl.value) {
      chatHistoryEl.value.scrollTop = chatHistoryEl.value.scrollHeight
    }
  })
}

// ライフサイクル
onMounted(async () => {
  // セッション状態を確認
  try {
    await claudeStore.fetchSessionStatus(currentSessionId.value)
    if (claudeStore.isConnected) {
      await loadMessages()
    }
  } catch (error) {
    console.error('セッション状態確認エラー:', error)
  }
})

// メッセージ追加時の自動スクロール
watch(() => claudeStore.messages.length, () => {
  scrollToBottom()
})
</script>

<style scoped>
.claude-chat-interface {
  background-color: #f8fafc;
}

.session-status {
  background-color: #f9fafb;
}

.status-indicator {
  animation: pulse 2s infinite;
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

.other-message {
  display: flex;
  justify-content: flex-start;
}

.other-message .message-content {
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

.message-text {
  line-height: 1.5;
}

.message-text :deep(.inline-code) {
  background-color: rgba(0, 0, 0, 0.1);
  padding: 0.125rem 0.25rem;
  border-radius: 0.25rem;
  font-family: monospace;
  font-size: 0.875em;
}

.message-text :deep(.code-block) {
  background-color: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 0.375rem;
  padding: 0.75rem;
  margin: 0.5rem 0;
  overflow-x: auto;
}

.message-text :deep(.code-block code) {
  font-family: 'Courier New', monospace;
  font-size: 0.875em;
  white-space: pre;
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