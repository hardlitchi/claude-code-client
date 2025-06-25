<template>
  <Modal @close="$emit('close')">
    <template #header>
      <h3 class="text-lg font-medium">新しいプロジェクトを作成</h3>
    </template>
    
    <template #body>
      <div class="space-y-6">
        <!-- テンプレート選択 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-3">
            プロジェクトテンプレート
          </label>
          
          <div v-if="loadingTemplates" class="text-center text-gray-500 py-4">
            テンプレートを読み込み中...
          </div>
          
          <div v-else class="grid grid-cols-1 gap-3">
            <div
              v-for="template in templates"
              :key="template.id"
              class="border rounded-lg p-4 cursor-pointer transition-colors"
              :class="{
                'border-blue-500 bg-blue-50': selectedTemplate === template.id,
                'border-gray-200 hover:border-gray-300': selectedTemplate !== template.id
              }"
              @click="selectedTemplate = template.id"
            >
              <div class="flex items-start space-x-3">
                <div class="flex-shrink-0 mt-1">
                  <div 
                    class="w-3 h-3 rounded-full border-2"
                    :class="{
                      'border-blue-500 bg-blue-500': selectedTemplate === template.id,
                      'border-gray-300': selectedTemplate !== template.id
                    }"
                  ></div>
                </div>
                
                <div class="flex-1">
                  <h4 class="font-medium text-gray-800">{{ template.name }}</h4>
                  <p class="text-sm text-gray-600 mt-1">{{ template.description }}</p>
                  
                  <div class="mt-2 flex flex-wrap gap-2 text-xs">
                    <span class="bg-gray-100 text-gray-700 px-2 py-1 rounded">
                      ビルド: {{ template.build_command }}
                    </span>
                    <span class="bg-gray-100 text-gray-700 px-2 py-1 rounded">
                      実行: {{ template.run_command }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- プロジェクト名 -->
        <div>
          <label for="project-name" class="block text-sm font-medium text-gray-700 mb-2">
            プロジェクト名 <span class="text-red-500">*</span>
          </label>
          <input
            id="project-name"
            v-model="projectName"
            type="text"
            class="w-full p-3 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
            placeholder="my-awesome-project"
            :class="{ 'border-red-500': errors.projectName }"
            @input="validateProjectName"
          />
          <p v-if="errors.projectName" class="mt-1 text-sm text-red-600">
            {{ errors.projectName }}
          </p>
          <p class="mt-1 text-xs text-gray-500">
            英数字、ハイフン、アンダースコアのみ使用可能
          </p>
        </div>

        <!-- プロジェクト説明 -->
        <div>
          <label for="project-description" class="block text-sm font-medium text-gray-700 mb-2">
            説明（任意）
          </label>
          <textarea
            id="project-description"
            v-model="projectDescription"
            rows="3"
            class="w-full p-3 border border-gray-300 rounded-lg focus:ring-blue-500 focus:border-blue-500"
            placeholder="プロジェクトの説明を入力してください"
          ></textarea>
        </div>

        <!-- 作成後の動作設定 -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-3">
            作成後の動作
          </label>
          
          <div class="space-y-2">
            <label class="flex items-center">
              <input
                v-model="options.openProject"
                type="checkbox"
                class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span class="ml-2 text-sm text-gray-700">作成後にプロジェクトフォルダを開く</span>
            </label>
            
            <label class="flex items-center">
              <input
                v-model="options.runBuild"
                type="checkbox"
                class="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span class="ml-2 text-sm text-gray-700">初期ビルドを実行する</span>
            </label>
          </div>
        </div>
      </div>
    </template>
    
    <template #footer>
      <div class="flex justify-end space-x-3">
        <button
          @click="$emit('close')"
          class="px-4 py-2 text-gray-600 hover:text-gray-800"
          :disabled="creating"
        >
          キャンセル
        </button>
        <button
          @click="createProject"
          :disabled="!canCreate || creating"
          class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {{ creating ? '作成中...' : 'プロジェクト作成' }}
        </button>
      </div>
    </template>
  </Modal>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useProjectStore } from '@/stores/projects'
import Modal from './Modal.vue'

interface Props {
  sessionId: string
}

const props = defineProps<Props>()

const projectStore = useProjectStore()

const selectedTemplate = ref('')
const projectName = ref('')
const projectDescription = ref('')
const loadingTemplates = ref(false)
const creating = ref(false)

const options = ref({
  openProject: true,
  runBuild: false
})

const errors = ref({
  projectName: '',
  template: ''
})

// 計算プロパティ
const templates = computed(() => projectStore.availableTemplates)

const canCreate = computed(() => {
  return selectedTemplate.value && 
         projectName.value.trim() && 
         !errors.value.projectName && 
         !errors.value.template
})

onMounted(async () => {
  await loadTemplates()
})

// メソッド
const loadTemplates = async () => {
  loadingTemplates.value = true
  try {
    await projectStore.loadTemplates()
    
    // デフォルトでFastAPIテンプレートを選択
    if (templates.value.length > 0) {
      const fastapi = templates.value.find(t => t.id === 'fastapi')
      selectedTemplate.value = fastapi?.id || templates.value[0].id
    }
  } catch (error: any) {
    errors.value.template = error.message
  } finally {
    loadingTemplates.value = false
  }
}

const validateProjectName = () => {
  errors.value.projectName = ''
  
  const name = projectName.value.trim()
  
  if (!name) {
    errors.value.projectName = 'プロジェクト名は必須です'
    return
  }
  
  if (name.length < 2) {
    errors.value.projectName = 'プロジェクト名は2文字以上である必要があります'
    return
  }
  
  if (name.length > 50) {
    errors.value.projectName = 'プロジェクト名は50文字以下である必要があります'
    return
  }
  
  // 英数字、ハイフン、アンダースコアのみ許可
  const validPattern = /^[a-zA-Z0-9_-]+$/
  if (!validPattern.test(name)) {
    errors.value.projectName = '英数字、ハイフン、アンダースコアのみ使用可能です'
    return
  }
  
  // 先頭文字の検証
  if (!/^[a-zA-Z]/.test(name)) {
    errors.value.projectName = 'プロジェクト名は英字で始まる必要があります'
    return
  }
}

const createProject = async () => {
  // 最終バリデーション
  validateProjectName()
  
  if (!canCreate.value) {
    return
  }
  
  creating.value = true
  
  try {
    const result = await projectStore.createProject(
      props.sessionId,
      selectedTemplate.value,
      projectName.value.trim(),
      projectDescription.value.trim() || undefined
    )
    
    // 成功通知
    console.log('プロジェクト作成成功:', result)
    
    // 作成後の動作
    if (options.value.runBuild) {
      // ビルドを実行
      try {
        await projectStore.buildProject(props.sessionId, result.project_path)
      } catch (buildError) {
        console.warn('初期ビルドに失敗しました:', buildError)
      }
    }
    
    emit('created', {
      projectPath: result.project_path,
      projectName: projectName.value.trim(),
      template: selectedTemplate.value,
      openProject: options.value.openProject
    })
    
  } catch (error: any) {
    alert(`プロジェクト作成エラー: ${error.message}`)
  } finally {
    creating.value = false
  }
}

// エミット
const emit = defineEmits<{
  close: []
  created: [data: {
    projectPath: string
    projectName: string
    template: string
    openProject: boolean
  }]
}>()
</script>

<style scoped>
/* モーダル内のスタイル調整 */
.modal-content {
  max-width: 600px;
}
</style>