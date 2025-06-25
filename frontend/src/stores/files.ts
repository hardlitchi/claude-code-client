import { defineStore } from 'pinia'
import { ref } from 'vue'
import apiClient from '@/services/api'

interface FileNode {
  type: 'file' | 'directory' | 'error'
  name: string
  size?: number
  modified?: string
  extension?: string
  children?: FileNode[]
  truncated?: boolean
  error?: string
}

interface FileContent {
  type: 'text' | 'binary'
  content?: string
  message?: string
  size: number
  modified?: string
  encoding?: string
}

export const useFileStore = defineStore('files', () => {
  // State
  const fileTree = ref<FileNode | null>(null)
  const openFiles = ref<Map<string, FileContent>>(new Map())
  const watchingSessions = ref<Set<string>>(new Set())

  // Actions
  const loadFileTree = async (sessionId: string, path: string = '') => {
    try {
      const response = await apiClient.get(`/api/files/tree/${sessionId}`, {
        params: { path }
      })
      fileTree.value = response.data
      return response.data
    } catch (error: any) {
      console.error('ファイルツリー読み込みエラー:', error)
      throw new Error(error.response?.data?.detail || 'ファイルツリーの読み込みに失敗しました')
    }
  }

  const getFileContent = async (sessionId: string, filePath: string): Promise<FileContent> => {
    try {
      // キャッシュから確認
      const cached = openFiles.value.get(filePath)
      if (cached) {
        return cached
      }

      const response = await apiClient.get(`/api/files/content/${sessionId}`, {
        params: { file_path: filePath }
      })
      
      const content = response.data
      openFiles.value.set(filePath, content)
      return content
    } catch (error: any) {
      console.error('ファイル読み込みエラー:', error)
      throw new Error(error.response?.data?.detail || 'ファイルの読み込みに失敗しました')
    }
  }

  const updateFileContent = async (
    sessionId: string, 
    filePath: string, 
    content: string, 
    encoding: string = 'utf-8'
  ) => {
    try {
      const response = await apiClient.put(`/api/files/content/${sessionId}`, {
        file_path: filePath,
        content,
        encoding
      })

      // キャッシュを更新
      const fileContent: FileContent = {
        type: 'text',
        content,
        size: content.length,
        modified: new Date().toISOString(),
        encoding
      }
      openFiles.value.set(filePath, fileContent)

      return response.data
    } catch (error: any) {
      console.error('ファイル保存エラー:', error)
      throw new Error(error.response?.data?.detail || 'ファイルの保存に失敗しました')
    }
  }

  const createFileOrDirectory = async (
    sessionId: string, 
    path: string, 
    type: 'file' | 'directory'
  ) => {
    try {
      const response = await apiClient.post(`/api/files/create/${sessionId}`, {
        path,
        type
      })
      return response.data
    } catch (error: any) {
      console.error('作成エラー:', error)
      throw new Error(error.response?.data?.detail || `${type}の作成に失敗しました`)
    }
  }

  const deleteFileOrDirectory = async (sessionId: string, path: string) => {
    try {
      const response = await apiClient.delete(`/api/files/delete/${sessionId}`, {
        params: { path }
      })
      
      // キャッシュからも削除
      openFiles.value.delete(path)
      
      return response.data
    } catch (error: any) {
      console.error('削除エラー:', error)
      throw new Error(error.response?.data?.detail || '削除に失敗しました')
    }
  }

  const uploadFile = async (sessionId: string, path: string, file: File) => {
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await apiClient.post(`/api/files/upload/${sessionId}`, formData, {
        params: { path },
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
            console.log(`アップロード進行状況: ${progress}%`)
          }
        }
      })
      
      return response.data
    } catch (error: any) {
      console.error('アップロードエラー:', error)
      throw new Error(error.response?.data?.detail || 'ファイルのアップロードに失敗しました')
    }
  }

  const downloadFile = async (sessionId: string, filePath: string) => {
    try {
      const response = await apiClient.get(`/api/files/download/${sessionId}`, {
        params: { file_path: filePath },
        responseType: 'blob'
      })

      // ダウンロードリンクを作成
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      
      // ファイル名を取得（パスから最後の部分を取得）
      const filename = filePath.split('/').pop() || 'download'
      link.download = filename
      
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      
    } catch (error: any) {
      console.error('ダウンロードエラー:', error)
      throw new Error(error.response?.data?.detail || 'ファイルのダウンロードに失敗しました')
    }
  }

  const startFileWatching = async (sessionId: string) => {
    try {
      if (watchingSessions.value.has(sessionId)) {
        return // 既に監視中
      }

      const response = await apiClient.post(`/api/files/watch/${sessionId}`)
      watchingSessions.value.add(sessionId)
      return response.data
    } catch (error: any) {
      console.error('ファイル監視開始エラー:', error)
      throw new Error(error.response?.data?.detail || 'ファイル監視の開始に失敗しました')
    }
  }

  const stopFileWatching = async (sessionId: string) => {
    try {
      if (!watchingSessions.value.has(sessionId)) {
        return // 監視していない
      }

      const response = await apiClient.delete(`/api/files/watch/${sessionId}`)
      watchingSessions.value.delete(sessionId)
      return response.data
    } catch (error: any) {
      console.error('ファイル監視停止エラー:', error)
      throw new Error(error.response?.data?.detail || 'ファイル監視の停止に失敗しました')
    }
  }

  const renameFileOrDirectory = async (
    sessionId: string, 
    oldPath: string, 
    newPath: string
  ) => {
    try {
      // リネームは削除→作成で実装（簡易版）
      // 実際の実装では専用APIエンドポイントを作成することを推奨
      
      // まずファイル内容を取得
      let content = ''
      let type: 'file' | 'directory' = 'file'
      
      try {
        const fileContent = await getFileContent(sessionId, oldPath)
        if (fileContent.type === 'text' && fileContent.content) {
          content = fileContent.content
        }
      } catch {
        // ディレクトリの可能性
        type = 'directory'
      }
      
      // 新しいファイル/ディレクトリを作成
      await createFileOrDirectory(sessionId, newPath, type)
      
      // ファイルの場合は内容をコピー
      if (type === 'file' && content) {
        await updateFileContent(sessionId, newPath, content)
      }
      
      // 元のファイル/ディレクトリを削除
      await deleteFileOrDirectory(sessionId, oldPath)
      
      // キャッシュを更新
      const cachedContent = openFiles.value.get(oldPath)
      if (cachedContent) {
        openFiles.value.delete(oldPath)
        openFiles.value.set(newPath, cachedContent)
      }
      
      return { success: true, message: 'リネームが完了しました' }
    } catch (error: any) {
      console.error('リネームエラー:', error)
      throw new Error(error.message || 'リネームに失敗しました')
    }
  }

  const searchFiles = async (
    sessionId: string, 
    query: string, 
    options: {
      includeContent?: boolean
      filePattern?: string
      maxResults?: number
    } = {}
  ) => {
    try {
      const response = await apiClient.get(`/api/files/search/${sessionId}`, {
        params: {
          query,
          include_content: options.includeContent || false,
          file_pattern: options.filePattern || '*',
          max_results: options.maxResults || 100
        }
      })
      return response.data
    } catch (error: any) {
      console.error('ファイル検索エラー:', error)
      throw new Error(error.response?.data?.detail || 'ファイル検索に失敗しました')
    }
  }

  const getFileHistory = async (sessionId: string, filePath: string) => {
    try {
      const response = await apiClient.get(`/api/files/history/${sessionId}`, {
        params: { file_path: filePath }
      })
      return response.data
    } catch (error: any) {
      console.error('ファイル履歴取得エラー:', error)
      throw new Error(error.response?.data?.detail || 'ファイル履歴の取得に失敗しました')
    }
  }

  // ユーティリティ関数
  const clearCache = () => {
    openFiles.value.clear()
  }

  const getCachedFile = (filePath: string) => {
    return openFiles.value.get(filePath)
  }

  const isCached = (filePath: string) => {
    return openFiles.value.has(filePath)
  }

  const getFileSize = (filePath: string) => {
    const cached = openFiles.value.get(filePath)
    return cached?.size || 0
  }

  // ファイルタイプ判定
  const getFileType = (filePath: string) => {
    const extension = filePath.split('.').pop()?.toLowerCase()
    
    const imageTypes = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp', 'ico']
    const videoTypes = ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm']
    const audioTypes = ['mp3', 'wav', 'flac', 'aac', 'ogg', 'wma']
    const codeTypes = ['js', 'ts', 'jsx', 'tsx', 'vue', 'py', 'java', 'cpp', 'c', 'go', 'rs', 'php', 'rb']
    const textTypes = ['txt', 'md', 'json', 'xml', 'yaml', 'yml', 'toml', 'ini', 'cfg', 'conf']
    
    if (!extension) return 'unknown'
    
    if (imageTypes.includes(extension)) return 'image'
    if (videoTypes.includes(extension)) return 'video'
    if (audioTypes.includes(extension)) return 'audio'
    if (codeTypes.includes(extension)) return 'code'
    if (textTypes.includes(extension)) return 'text'
    
    return 'other'
  }

  const isEditableFile = (filePath: string) => {
    const type = getFileType(filePath)
    return ['code', 'text', 'unknown'].includes(type)
  }

  return {
    // State
    fileTree,
    openFiles,
    watchingSessions,
    
    // Actions
    loadFileTree,
    getFileContent,
    updateFileContent,
    createFileOrDirectory,
    deleteFileOrDirectory,
    uploadFile,
    downloadFile,
    startFileWatching,
    stopFileWatching,
    renameFileOrDirectory,
    searchFiles,
    getFileHistory,
    
    // Utilities
    clearCache,
    getCachedFile,
    isCached,
    getFileSize,
    getFileType,
    isEditableFile
  }
})