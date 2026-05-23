<template>
  <v-app>
    <v-main class="login-main">
      <div class="login-container">
        <!-- Logo & Title -->
        <div class="text-center mb-6">
          <v-avatar size="80" color="primary" class="mb-3" style="box-shadow: 0 4px 20px rgba(139, 126, 116, 0.3);">
            <v-icon size="48" color="white">mdi-wallet</v-icon>
          </v-avatar>
          <h1 class="text-h4 font-weight-bold">Money App</h1>
          <p class="text-body-2 text-grey mt-1">个人记账 — 登录后使用</p>
        </div>

        <!-- Login / Register Card -->
        <v-card class="pa-6 login-card" rounded="xl" elevation="2">
          <!-- Tab: 登录 / 注册 -->
          <div class="d-flex mb-5">
            <v-btn
              variant="text"
              :color="isLogin ? 'primary' : 'grey'"
              class="flex-grow-1 tab-btn"
              :class="{ 'tab-active': isLogin }"
              @click="isLogin = true"
            >
              登录
            </v-btn>
            <v-btn
              variant="text"
              :color="!isLogin ? 'primary' : 'grey'"
              class="flex-grow-1 tab-btn"
              :class="{ 'tab-active': !isLogin }"
              @click="isLogin = false"
            >
              注册
            </v-btn>
          </div>

          <!-- Login Form -->
          <div v-if="isLogin">
            <v-text-field
              v-model="loginForm.username"
              label="用户名"
              variant="outlined"
              prepend-inner-icon="mdi-account"
              hide-details
              class="mb-3"
              @keydown.enter="handleLogin"
            />
            <v-text-field
              v-model="loginForm.password"
              label="密码"
              type="password"
              variant="outlined"
              prepend-inner-icon="mdi-lock"
              hide-details
              class="mb-4"
              @keydown.enter="handleLogin"
            />
            <v-btn
              color="primary"
              size="large"
              block
              :loading="loading"
              @click="handleLogin"
              rounded="xl"
              height="48"
            >
              登录
            </v-btn>
          </div>

          <!-- Register Form -->
          <div v-else>
            <v-text-field
              v-model="registerForm.username"
              label="用户名"
              variant="outlined"
              prepend-inner-icon="mdi-account"
              hide-details
              class="mb-3"
              @keydown.enter="handleRegister"
            />
            <v-text-field
              v-model="registerForm.password"
              label="密码（至少6位）"
              type="password"
              variant="outlined"
              prepend-inner-icon="mdi-lock"
              hide-details
              class="mb-3"
              @keydown.enter="handleRegister"
            />
            <v-text-field
              v-model="registerForm.confirmPassword"
              label="确认密码"
              type="password"
              variant="outlined"
              prepend-inner-icon="mdi-lock-check"
              hide-details
              class="mb-4"
              @keydown.enter="handleRegister"
            />
            <v-btn
              color="primary"
              size="large"
              block
              :loading="loading"
              @click="handleRegister"
              rounded="xl"
              height="48"
            >
              注册
            </v-btn>
          </div>
        </v-card>

        <!-- Error message -->
        <v-slide-y-reverse-transition>
          <v-alert
            v-if="errorMsg"
            :text="errorMsg"
            type="error"
            variant="tonal"
            class="mt-3"
            closable
            density="compact"
            @click:close="errorMsg = ''"
          />
        </v-slide-y-reverse-transition>
      </div>
    </v-main>
  </v-app>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { login as apiLogin, register as apiRegister, getMe } from '@/api/auth'

const router = useRouter()

const isLogin = ref(true)
const loading = ref(false)
const errorMsg = ref('')

const loginForm = reactive({
  username: '',
  password: '',
})

const registerForm = reactive({
  username: '',
  password: '',
  confirmPassword: '',
})

// 检查是否已登录，已登录则直接跳转
onMounted(async () => {
  const token = localStorage.getItem('token')
  if (token) {
    try {
      const user = await getMe()
      if (user) {
        router.replace('/')
      }
    } catch {
      // token 无效，清除
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      localStorage.removeItem('userId')
    }
  }
})

async function handleLogin() {
  errorMsg.value = ''
  if (!loginForm.username.trim() || !loginForm.password.trim()) {
    errorMsg.value = '请输入用户名和密码'
    return
  }
  loading.value = true
  try {
    const result = await apiLogin({
      username: loginForm.username.trim(),
      password: loginForm.password,
    })
    localStorage.setItem('token', result.access_token)
    localStorage.setItem('username', result.username)
    localStorage.setItem('userId', String(result.user_id))
    router.replace('/')
  } catch (e) {
    errorMsg.value = e.message || '登录失败'
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  errorMsg.value = ''
  if (!registerForm.username.trim()) {
    errorMsg.value = '请输入用户名'
    return
  }
  if (registerForm.password.length < 6) {
    errorMsg.value = '密码至少6位'
    return
  }
  if (registerForm.password !== registerForm.confirmPassword) {
    errorMsg.value = '两次密码输入不一致'
    return
  }
  loading.value = true
  try {
    const result = await apiRegister({
      username: registerForm.username.trim(),
      password: registerForm.password,
    })
    localStorage.setItem('token', result.access_token)
    localStorage.setItem('username', result.username)
    localStorage.setItem('userId', String(result.user_id))
    router.replace('/')
  } catch (e) {
    errorMsg.value = e.message || '注册失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-main {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgb(var(--v-theme-background));
}

.login-container {
  width: 100%;
  max-width: 400px;
  padding: 20px;
}

.login-card {
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.tab-btn {
  border-radius: 12px !important;
  transition: all 0.2s ease;
}

.tab-btn.tab-active {
  background: rgba(var(--v-theme-primary), 0.08);
}
</style>
