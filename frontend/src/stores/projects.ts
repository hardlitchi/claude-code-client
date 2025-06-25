import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import apiClient from '@/services/api'

interface ProjectTemplate {
  id: string
  name: string
  description: string
  build_command: string
  run_command: string
  test_command: string
}

interface ProjectConfig {
  name: string
  description?: string
  template: string
  created_at: string
  created_by: string
  build_command: string
  run_command: string
  test_command: string
}

interface ProjectStatus {
  is_project: boolean
  config?: ProjectConfig
  docker_status?: {
    exists: boolean
    running: boolean
    status?: string
    container_name: string
    error?: string
  }
  project_path: string
  message?: string
}

interface BuildProcess {
  sessionId: string
  command: string
  status: 'running' | 'completed' | 'error'
  output: string[]
  startTime: Date
  endTime?: Date
  success?: boolean
  returnCode?: number
}

interface DeployProcess {
  sessionId: string
  target: string
  status: 'running' | 'completed' | 'error'
  output: string[]
  startTime: Date
  endTime?: Date
  success?: boolean
  url?: string
  containerName?: string
  error?: string
}

export const useProjectStore = defineStore('projects', () => {
  // State
  const templates = ref<Record<string, ProjectTemplate>>({})
  const currentProject = ref<ProjectStatus | null>(null)
  const buildProcesses = ref<Map<string, BuildProcess>>(new Map())
  const deployProcesses = ref<Map<string, DeployProcess>>(new Map())
  const loading = ref(false)

  // Computed
  const availableTemplates = computed(() => Object.values(templates.value))
  
  const isBuilding = computed(() => {
    return Array.from(buildProcesses.value.values()).some(p => p.status === 'running')
  })
  
  const isDeploying = computed(() => {
    return Array.from(deployProcesses.value.values()).some(p => p.status === 'running')
  })

  // Actions
  const loadTemplates = async () => {
    try {
      loading.value = true
      const response = await apiClient.get('/api/projects/templates')
      templates.value = response.data.templates
      return response.data.templates
    } catch (error: any) {
      console.error('テンプレート読み込みエラー:', error)
      throw new Error(error.response?.data?.detail || 'テンプレートの読み込みに失敗しました')
    } finally {
      loading.value = false
    }
  }

  const createProject = async (
    sessionId: string,
    templateId: string,
    projectName: string,
    description?: string
  ) => {
    try {
      loading.value = true
      const response = await apiClient.post(`/api/projects/create/${sessionId}`, {
        template: templateId,
        name: projectName,
        description
      })
      
      return response.data
    } catch (error: any) {
      console.error('プロジェクト作成エラー:', error)
      throw new Error(error.response?.data?.detail || 'プロジェクトの作成に失敗しました')
    } finally {
      loading.value = false
    }
  }

  const getProjectStatus = async (sessionId: string, projectPath?: string) => {
    try {
      const params = projectPath ? { project_path: projectPath } : {}
      const response = await apiClient.get(`/api/projects/status/${sessionId}`, { params })
      
      currentProject.value = response.data
      return response.data
    } catch (error: any) {
      console.error('プロジェクト状態取得エラー:', error)
      throw new Error(error.response?.data?.detail || 'プロジェクト状態の取得に失敗しました')
    }
  }

  const buildProject = async (
    sessionId: string,
    projectPath?: string,
    command?: string,
    environment?: Record<string, string>
  ) => {
    try {
      const params = projectPath ? { project_path: projectPath } : {}
      
      const response = await apiClient.post(`/api/projects/build/${sessionId}`, {
        command,
        environment
      }, { params })

      // ビルドプロセスを開始
      const buildProcess: BuildProcess = {
        sessionId,
        command: response.data.command,
        status: 'running',
        output: [],
        startTime: new Date()
      }
      
      buildProcesses.value.set(sessionId, buildProcess)
      
      return response.data
    } catch (error: any) {
      console.error('ビルド開始エラー:', error)
      throw new Error(error.response?.data?.detail || 'ビルドの開始に失敗しました')
    }
  }

  const deployProject = async (
    sessionId: string,
    target: 'local' | 'docker',
    projectPath?: string,
    environment?: Record<string, string>,
    config?: Record<string, any>
  ) => {
    try {
      const params = projectPath ? { project_path: projectPath } : {}
      
      const response = await apiClient.post(`/api/projects/deploy/${sessionId}`, {
        target,
        environment,
        config
      }, { params })

      // デプロイプロセスを開始
      const deployProcess: DeployProcess = {
        sessionId,
        target,
        status: 'running',
        output: [],
        startTime: new Date()
      }
      
      deployProcesses.value.set(sessionId, deployProcess)
      
      return response.data
    } catch (error: any) {
      console.error('デプロイ開始エラー:', error)
      throw new Error(error.response?.data?.detail || 'デプロイの開始に失敗しました')
    }
  }

  const stopDockerContainer = async (containerName: string) => {
    try {
      // Docker APIを直接呼び出すのではなく、プロジェクト内でDockerコマンドを実行
      // この機能は追加のAPIエンドポイントが必要になります
      console.log(`Stopping container: ${containerName}`)
      // TODO: Docker停止APIエンドポイントの実装
    } catch (error: any) {
      console.error('コンテナ停止エラー:', error)
      throw new Error('コンテナの停止に失敗しました')
    }
  }

  // WebSocket メッセージハンドリング
  const handleWebSocketMessage = (message: any) => {
    switch (message.type) {
      case 'build_started':
        {
          const process = buildProcesses.value.get(message.session_id || 'default')
          if (process) {
            process.status = 'running'
            process.output = [`ビルド開始: ${message.command}`]
          }
        }
        break

      case 'build_output':
        {
          const process = buildProcesses.value.get(message.session_id || 'default')
          if (process) {
            process.output.push(message.output)
          }
        }
        break

      case 'build_completed':
        {
          const process = buildProcesses.value.get(message.session_id || 'default')
          if (process) {
            process.status = message.success ? 'completed' : 'error'
            process.endTime = new Date()
            process.success = message.success
            process.returnCode = message.return_code
            
            if (message.success) {
              process.output.push('✅ ビルドが正常に完了しました')
            } else {
              process.output.push(`❌ ビルドが失敗しました (終了コード: ${message.return_code})`)
            }
          }
        }
        break

      case 'build_error':
        {
          const process = buildProcesses.value.get(message.session_id || 'default')
          if (process) {
            process.status = 'error'
            process.endTime = new Date()
            process.output.push(`❌ ビルドエラー: ${message.error}`)
          }
        }
        break

      case 'deploy_started':
        {
          const process = deployProcesses.value.get(message.session_id || 'default')
          if (process) {
            process.status = 'running'
            process.output = [`デプロイ開始 (${message.target})`]
            if (message.command) {
              process.output.push(`実行コマンド: ${message.command}`)
            }
          }
        }
        break

      case 'deploy_output':
        {
          const process = deployProcesses.value.get(message.session_id || 'default')
          if (process) {
            process.output.push(message.output)
          }
        }
        break

      case 'deploy_completed':
        {
          const process = deployProcesses.value.get(message.session_id || 'default')
          if (process) {
            process.status = message.success ? 'completed' : 'error'
            process.endTime = new Date()
            process.success = message.success
            process.url = message.url
            process.containerName = message.container_name
            process.error = message.error
            
            if (message.success) {
              process.output.push('✅ デプロイが正常に完了しました')
              if (message.url) {
                process.output.push(`🌐 アクセスURL: ${message.url}`)
              }
            } else {
              process.output.push(`❌ デプロイが失敗しました: ${message.error || '不明なエラー'}`)
            }
          }
        }
        break

      case 'deploy_error':
        {
          const process = deployProcesses.value.get(message.session_id || 'default')
          if (process) {
            process.status = 'error'
            process.endTime = new Date()
            process.error = message.error
            process.output.push(`❌ デプロイエラー: ${message.error}`)
          }
        }
        break

      case 'project_created':
        {
          // プロジェクト作成通知の処理
          console.log(`プロジェクト作成: ${message.project_name} (テンプレート: ${message.template})`)
        }
        break
    }
  }

  // ユーティリティ関数
  const getBuildProcess = (sessionId: string) => {
    return buildProcesses.value.get(sessionId)
  }

  const getDeployProcess = (sessionId: string) => {
    return deployProcesses.value.get(sessionId)
  }

  const clearBuildProcess = (sessionId: string) => {
    buildProcesses.value.delete(sessionId)
  }

  const clearDeployProcess = (sessionId: string) => {
    deployProcesses.value.delete(sessionId)
  }

  const isProjectDirectory = (status: ProjectStatus | null): boolean => {
    return status?.is_project === true
  }

  const getDockerStatus = (status: ProjectStatus | null) => {
    return status?.docker_status || {
      exists: false,
      running: false,
      container_name: ''
    }
  }

  const formatBuildDuration = (process: BuildProcess): string => {
    if (!process.endTime) return '実行中...'
    
    const duration = process.endTime.getTime() - process.startTime.getTime()
    const seconds = Math.floor(duration / 1000)
    const minutes = Math.floor(seconds / 60)
    
    if (minutes > 0) {
      return `${minutes}分${seconds % 60}秒`
    }
    return `${seconds}秒`
  }

  const formatDeployDuration = (process: DeployProcess): string => {
    if (!process.endTime) return '実行中...'
    
    const duration = process.endTime.getTime() - process.startTime.getTime()
    const seconds = Math.floor(duration / 1000)
    const minutes = Math.floor(seconds / 60)
    
    if (minutes > 0) {
      return `${minutes}分${seconds % 60}秒`
    }
    return `${seconds}秒`
  }

  return {
    // State
    templates,
    currentProject,
    buildProcesses,
    deployProcesses,
    loading,

    // Computed
    availableTemplates,
    isBuilding,
    isDeploying,

    // Actions
    loadTemplates,
    createProject,
    getProjectStatus,
    buildProject,
    deployProject,
    stopDockerContainer,
    handleWebSocketMessage,

    // Utilities
    getBuildProcess,
    getDeployProcess,
    clearBuildProcess,
    clearDeployProcess,
    isProjectDirectory,
    getDockerStatus,
    formatBuildDuration,
    formatDeployDuration
  }
})