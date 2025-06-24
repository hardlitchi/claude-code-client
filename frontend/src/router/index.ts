import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/dashboard'
    },
    {
      path: '/login',
      name: 'Login',
      component: Login,
      meta: { requiresGuest: true }
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('../views/Dashboard.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/workspace/:sessionId',
      name: 'Workspace',
      component: () => import('../views/Workspace.vue'),
      meta: { requiresAuth: true }
    }
  ]
})

// 認証ガード
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  
  // トークンがある場合はユーザー情報を確認
  if (authStore.token && !authStore.user) {
    try {
      await authStore.checkAuthStatus()
    } catch (error) {
      // トークンが無効な場合はログアウト
      authStore.logout()
    }
  }

  const requiresAuth = to.meta.requiresAuth
  const requiresGuest = to.meta.requiresGuest
  const isAuthenticated = authStore.isAuthenticated

  if (requiresAuth && !isAuthenticated) {
    // 認証が必要だがログインしていない場合
    next('/login')
  } else if (requiresGuest && isAuthenticated) {
    // ゲスト専用ページだがログイン済みの場合
    next('/dashboard')
  } else {
    next()
  }
})

export default router