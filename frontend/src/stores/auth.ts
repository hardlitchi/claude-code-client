import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

interface User {
  id: number
  username: string
  email?: string
  is_active: boolean
  is_admin: boolean
}

interface LoginCredentials {
  username: string
  password: string
}

interface RegisterData {
  username: string
  password: string
  email?: string
}

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null)
  const token = ref<string | null>(localStorage.getItem('auth_token'))
  const isLoading = ref(false)

  // Getters
  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const isAdmin = computed(() => user.value?.is_admin || false)

  // API設定
  const api = axios.create({
    baseURL: '/api'
  })

  // リクエストインターセプター（認証トークンを自動付与）
  api.interceptors.request.use((config) => {
    if (token.value) {
      config.headers.Authorization = `Bearer ${token.value}`
    }
    return config
  })

  // レスポンスインターセプター（認証エラー時の処理）
  api.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        logout()
      }
      return Promise.reject(error)
    }
  )

  // Actions
  const login = async (credentials: LoginCredentials): Promise<void> => {
    isLoading.value = true
    try {
      const response = await api.post('/auth/login', credentials)
      const { access_token } = response.data

      token.value = access_token
      localStorage.setItem('auth_token', access_token)

      // ユーザー情報を取得
      await fetchUserInfo()
    } catch (error: any) {
      console.error('ログインエラー:', error)
      throw new Error(error.response?.data?.detail || 'ログインに失敗しました')
    } finally {
      isLoading.value = false
    }
  }

  const register = async (userData: RegisterData): Promise<void> => {
    isLoading.value = true
    try {
      await api.post('/auth/register', userData)
    } catch (error: any) {
      console.error('登録エラー:', error)
      throw new Error(error.response?.data?.detail || 'ユーザー登録に失敗しました')
    } finally {
      isLoading.value = false
    }
  }

  const logout = (): void => {
    user.value = null
    token.value = null
    localStorage.removeItem('auth_token')
  }

  const fetchUserInfo = async (): Promise<void> => {
    if (!token.value) return

    try {
      const response = await api.get('/users/me')
      user.value = response.data
    } catch (error) {
      console.error('ユーザー情報取得エラー:', error)
      logout()
    }
  }

  const checkAuthStatus = async (): Promise<void> => {
    if (token.value) {
      await fetchUserInfo()
    }
  }

  // 初期化時にトークンがある場合はユーザー情報を取得
  if (token.value) {
    checkAuthStatus()
  }

  return {
    // State
    user,
    token,
    isLoading,
    
    // Getters
    isAuthenticated,
    isAdmin,
    
    // Actions
    login,
    register,
    logout,
    fetchUserInfo,
    checkAuthStatus,
    
    // API instance
    api
  }
})