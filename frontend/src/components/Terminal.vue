<template>
  <div class="terminal-container h-full">
    <div ref="terminalElement" class="h-full"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
// import { Terminal } from '@xterm/xterm'
// import { FitAddon } from '@xterm/addon-fit'

interface Props {
  sessionId: string
}

const props = defineProps<Props>()

const terminalElement = ref<HTMLElement>()
let terminal: any = null
let fitAddon: any = null
let websocket: WebSocket | null = null

const emit = defineEmits<{
  connected: []
  disconnected: []
  error: [message: string]
}>()

const connectWebSocket = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/api/terminal/ws/${props.sessionId}`
  
  websocket = new WebSocket(wsUrl)
  
  websocket.onopen = () => {
    console.log('Terminal WebSocket connected')
    emit('connected')
  }
  
  websocket.onmessage = (event) => {
    if (terminal) {
      terminal.write(event.data)
    }
  }
  
  websocket.onclose = () => {
    console.log('Terminal WebSocket disconnected')
    emit('disconnected')
  }
  
  websocket.onerror = (error) => {
    console.error('Terminal WebSocket error:', error)
    emit('error', 'WebSocket接続エラーが発生しました')
  }
}

const initializeTerminal = async () => {
  if (!terminalElement.value) return
  
  try {
    // TODO: xterm.js の実装
    // 現在は仮実装でHTMLベースのターミナルを表示
    terminalElement.value.innerHTML = `
      <div style="
        background: #000; 
        color: #00ff00; 
        font-family: 'Courier New', monospace; 
        padding: 10px; 
        height: 100%; 
        overflow-y: auto;
        white-space: pre-wrap;
      " id="terminal-output">
        <div>Terminal connected to session: ${props.sessionId}</div>
        <div>$ cd /home/user/project</div>
        <div>$ ls -la</div>
        <div>total 24</div>
        <div>drwxr-xr-x  3 user  staff   96 Nov 24 10:30 .</div>
        <div>drwxr-xr-x  4 user  staff  128 Nov 24 10:30 ..</div>
        <div>-rw-r--r--  1 user  staff  120 Nov 24 10:30 README.md</div>
        <div>$ <span style="animation: blink 1s infinite;">■</span></div>
      </div>
    `
    
    // 仮のキーボード入力処理
    const handleKeyPress = (event: KeyboardEvent) => {
      if (event.target === terminalElement.value || terminalElement.value?.contains(event.target as Node)) {
        if (websocket && websocket.readyState === WebSocket.OPEN) {
          if (event.key === 'Enter') {
            websocket.send('\r')
          } else if (event.key.length === 1) {
            websocket.send(event.key)
          }
        }
      }
    }
    
    document.addEventListener('keydown', handleKeyPress)
    
    // フォーカス可能にする
    terminalElement.value.setAttribute('tabindex', '0')
    terminalElement.value.focus()
    
    /* 
    // 実際のxterm.js実装（依存関係インストール後に有効化）
    const { Terminal } = await import('@xterm/xterm')
    const { FitAddon } = await import('@xterm/addon-fit')
    
    terminal = new Terminal({
      cursorBlink: true,
      cursorStyle: 'block',
      fontSize: 14,
      fontFamily: 'Monaco, Menlo, "DejaVu Sans Mono", monospace',
      theme: {
        background: '#000000',
        foreground: '#ffffff',
        cursor: '#ffffff'
      }
    })
    
    fitAddon = new FitAddon()
    terminal.loadAddon(fitAddon)
    
    terminal.open(terminalElement.value)
    fitAddon.fit()
    
    // ターミナル入力を WebSocket に送信
    terminal.onData((data) => {
      if (websocket && websocket.readyState === WebSocket.OPEN) {
        websocket.send(data)
      }
    })
    
    // リサイズ処理
    const handleResize = () => {
      if (fitAddon && terminal) {
        fitAddon.fit()
      }
    }
    
    window.addEventListener('resize', handleResize)
    */
    
  } catch (error) {
    console.error('Terminal initialization error:', error)
    emit('error', 'ターミナルの初期化に失敗しました')
  }
}

const cleanup = () => {
  if (websocket) {
    websocket.close()
    websocket = null
  }
  
  if (terminal) {
    terminal.dispose()
    terminal = null
  }
}

onMounted(async () => {
  await nextTick()
  await initializeTerminal()
  connectWebSocket()
})

onUnmounted(() => {
  cleanup()
})

// 外部からアクセス可能なメソッド
defineExpose({
  focus: () => {
    if (terminal) {
      terminal.focus()
    } else if (terminalElement.value) {
      terminalElement.value.focus()
    }
  },
  
  clear: () => {
    if (terminal) {
      terminal.clear()
    }
  },
  
  reconnect: () => {
    cleanup()
    setTimeout(() => {
      initializeTerminal()
      connectWebSocket()
    }, 1000)
  }
})
</script>

<style scoped>
.terminal-container {
  background: #000;
  position: relative;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* xterm.js のスタイル（将来有効化） */
/*
:deep(.xterm) {
  height: 100% !important;
}

:deep(.xterm-viewport) {
  background-color: transparent !important;
}

:deep(.xterm-screen) {
  background-color: transparent !important;
}
*/
</style>