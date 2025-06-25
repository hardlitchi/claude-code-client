<template>
  <div class="modal-overlay fixed inset-0 z-50 flex items-center justify-center">
    <!-- オーバーレイ -->
    <div 
      class="absolute inset-0 bg-black bg-opacity-50"
      @click="$emit('close')"
    ></div>
    
    <!-- モーダルコンテンツ -->
    <div class="modal-content relative bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-screen overflow-y-auto">
      <!-- ヘッダー -->
      <div v-if="$slots.header" class="modal-header px-6 py-4 border-b border-gray-200">
        <slot name="header"></slot>
      </div>
      
      <!-- ボディ -->
      <div class="modal-body px-6 py-4">
        <slot name="body"></slot>
      </div>
      
      <!-- フッター -->
      <div v-if="$slots.footer" class="modal-footer px-6 py-4 border-t border-gray-200">
        <slot name="footer"></slot>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// エミット
defineEmits<{
  close: []
}>()
</script>

<style scoped>
.modal-overlay {
  animation: fadeIn 0.2s ease-out;
}

.modal-content {
  animation: slideIn 0.2s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-20px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
</style>