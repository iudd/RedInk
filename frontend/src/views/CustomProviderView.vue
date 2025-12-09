<template>
  <div class="container">
    <div class="page-header">
      <h1 class="page-title">自定义服务商配置</h1>
      <p class="page-subtitle">添加自定义的OpenAI兼容AI服务商</p>
      <div v-if="storageStatus" class="storage-status-container">
        <div class="storage-status" :class="storageStatus.mode">
          存储模式: {{ storageStatus.mode === 'supabase' ? '☁️ Supabase 云端' : '📂 本地文件' }}
        </div>
        <button 
          @click="switchStorageMode" 
          class="btn btn-small btn-secondary switch-btn"
          :disabled="switchingStorage"
        >
          {{ switchingStorage ? '切换中...' : (storageStatus.mode === 'supabase' ? '切换到本地' : '切换到 Supabase') }}
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading-container">
      <div class="spinner"></div>
      <p>加载配置中...</p>
    </div>

    <div v-else class="custom-provider-container">
      <!-- 添加自定义服务商表单 -->
      <div class="card">
        <div class="section-header">
          <div>
            <h2 class="section-title">添加自定义服务商</h2>
            <p class="section-desc">配置OpenAI兼容的AI服务商</p>
          </div>
        </div>

        <form @submit.prevent="handleAddProvider" class="provider-form">
          <div class="form-row">
            <div class="form-group">
              <label>服务商名称 *</label>
              <input
                v-model="newProvider.provider_name"
                type="text"
                placeholder="例如：我的AI服务商"
                required
              />
            </div>
            <div class="form-group">
              <label>服务类型 *</label>
              <select v-model="newProvider.service_type" required>
                <option value="text">文本生成</option>
                <option value="image">图片生成</option>
              </select>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label>服务商类型 *</label>
              <select v-model="newProvider.provider_type" required>
                <option value="openai_compatible">OpenAI兼容</option>
                <option value="google_genai">Google Gemini</option>
                <option value="image_api">图片API</option>
              </select>
            </div>
            <div class="form-group">
              <label>模型名称 *</label>
              <input
                v-model="newProvider.model"
                type="text"
                placeholder="例如：gpt-4 或 dall-e-3"
                required
              />
            </div>
          </div>

          <div class="form-group">
            <label>API地址 *</label>
            <input
              v-model="newProvider.base_url"
              type="url"
              placeholder="例如：https://api.openai.com/v1"
              required
            />
          </div>

          <div class="form-group">
            <label>API密钥 *</label>
            <input
              v-model="newProvider.api_key"
              type="password"
              placeholder="sk-xxxxxxxxxxxxx"
              required
            />
          </div>

          <div class="form-actions">
            <button
              type="button"
              @click="testConnection"
              :disabled="testingConnection"
              class="btn btn-secondary"
            >
              {{ testingConnection ? '测试中...' : '测试连接' }}
            </button>
            <button
              type="submit"
              :disabled="saving"
              class="btn btn-primary"
            >
              {{ saving ? '添加中...' : '添加服务商' }}
            </button>
          </div>

          <!-- 测试结果显示 -->
          <div v-if="testResult" class="test-result" :class="{ success: testResult.success }">
            <div class="test-header">
              <span class="test-status">
                {{ testResult.success ? '✅ 连接成功' : '❌ 连接失败' }}
              </span>
              <span class="test-message">{{ testResult.message }}</span>
            </div>
            <div v-if="testResult.models && testResult.models.length > 0" class="available-models">
              <p class="models-label">可用模型：</p>
              <div class="models-list">
                <span
                  v-for="model in testResult.models.slice(0, 10)"
                  :key="model"
                  class="model-tag"
                >
                  {{ model }}
                </span>
                <span v-if="testResult.models.length > 10" class="model-more">
                  +{{ testResult.models.length - 10 }} 更多
                </span>
              </div>
            </div>
          </div>
        </form>
      </div>

      <!-- 已添加的自定义服务商 -->
      <div class="card">
        <div class="section-header">
          <div>
            <h2 class="section-title">自定义服务商列表</h2>
            <p class="section-desc">管理已添加的自定义服务商</p>
          </div>
        </div>

        <div v-if="customProviders.length === 0" class="empty-state">
          <div class="empty-icon">📝</div>
          <p>暂无自定义服务商</p>
          <p class="empty-desc">添加您的第一个自定义AI服务商</p>
        </div>

        <div v-else class="provider-list">
          <div
            v-for="provider in customProviders"
            :key="provider.name"
            class="provider-item"
          >
            <div class="provider-info">
              <div class="provider-header">
                <h3 class="provider-name">{{ provider.name }}</h3>
                <div class="provider-badges">
                  <span class="badge type-badge">{{ getServiceTypeLabel(provider.service_type) }}</span>
                  <span class="badge status-badge" :class="{ active: isProviderActive(provider.name) }">
                    {{ isProviderActive(provider.name) ? '已激活' : '未激活' }}
                  </span>
                </div>
              </div>
              <div class="provider-details">
                <p class="provider-model">模型：{{ provider.model }}</p>
                <p class="provider-url">{{ provider.base_url }}</p>
              </div>
            </div>
            <div class="provider-actions">
              <button
                v-if="!isProviderActive(provider.name)"
                @click="setActiveProvider(provider.name)"
                class="btn btn-small btn-primary"
              >
                激活
              </button>
              <button
                @click="deleteProvider(provider.name)"
                class="btn btn-small btn-danger"
              >
                删除
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 当前激活的服务商 -->
      <div class="card">
        <div class="section-header">
          <div>
            <h2 class="section-title">当前激活的服务商</h2>
            <p class="section-desc">正在使用的AI服务商</p>
          </div>
        </div>

        <div class="active-providers">
          <div class="active-provider-item">
            <div class="provider-label">文本生成：</div>
            <div class="provider-value">{{ currentTextProvider || '未设置' }}</div>
          </div>
          <div class="active-provider-item">
            <div class="provider-label">图片生成：</div>
            <div class="provider-value">{{ currentImageProvider || '未设置' }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Supabase 配置对话框 -->
    <div v-if="showSupabaseDialog" class="modal-overlay">
      <div class="modal-content">
        <div class="modal-header">
          <h3>连接到 Supabase</h3>
          <button @click="showSupabaseDialog = false" class="close-btn">&times;</button>
        </div>
        <div class="modal-body">
          <p class="modal-desc">请输入您的 Supabase 项目凭证以启用云端存储。</p>
          
          <div class="form-group">
            <label>Supabase URL</label>
            <input 
              v-model="supabaseConfig.url" 
              type="text" 
              placeholder="https://your-project.supabase.co"
            />
          </div>
          
          <div class="form-group">
            <label>Supabase Key (anon/public)</label>
            <input 
              v-model="supabaseConfig.key" 
              type="password" 
              placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            />
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showSupabaseDialog = false" class="btn btn-secondary">取消</button>
          <button 
            @click="confirmSwitchToSupabase" 
            class="btn btn-primary"
            :disabled="switchingStorage"
          >
            {{ switchingStorage ? '连接中...' : '连接并切换' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// 状态变量
const loading = ref(true)
const saving = ref(false)
const testingConnection = ref(false)
const switchingStorage = ref(false)
const showSupabaseDialog = ref(false)
const testResult = ref<any>(null)
const storageStatus = ref<any>(null)

// Supabase 配置
const supabaseConfig = ref({
  url: '',
  key: ''
})

// 自定义服务商列表
const customProviders = ref<any[]>([])

// 当前激活的服务商
const currentTextProvider = ref('')
const currentImageProvider = ref('')

// 新服务商表单
const newProvider = ref({
  provider_name: '',
  provider_type: 'openai_compatible',
  api_key: '',
  base_url: '',
  model: '',
  service_type: 'text'
})

// 加载配置
async function loadConfig() {
  try {
    // 并行获取配置和存储状态
    const [configRes, statusRes] = await Promise.all([
      fetch('/api/custom-providers'),
      fetch('/api/health/storage')
    ])
    
    const result = await configRes.json()
    const statusResult = await statusRes.json()
    
    if (statusResult.success) {
      storageStatus.value = statusResult
    }

    if (result.success) {
      const data = result.data
      
      // 转换自定义服务商为数组格式
      customProviders.value = Object.entries(data.custom_providers || {}).map(([name, config]: [string, any]) => ({
        name,
        ...config
      }))
      
      currentTextProvider.value = data.active_text_provider || ''
      currentImageProvider.value = data.active_image_provider || ''
    } else {
      console.error('加载配置失败:', result.error)
    }
  } catch (error) {
    console.error('加载配置异常:', error)
  } finally {
    loading.value = false
  }
}

// 切换存储模式
async function switchStorageMode() {
  if (!storageStatus.value) return
  
  const currentMode = storageStatus.value.mode
  const targetMode = currentMode === 'supabase' ? 'local' : 'supabase'
  
  if (targetMode === 'local') {
    if (!confirm('确定要切换到本地文件存储吗？')) return
    await executeSwitch('local')
    return
  }
  
  // 目标是 Supabase，先尝试直接切换（使用环境变量）
  switchingStorage.value = true
  try {
    const response = await fetch('/api/config/storage-mode', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ mode: 'supabase' })
    })
    
    const result = await response.json()
    if (result.success) {
      alert('已成功切换到 Supabase 存储模式')
      await loadConfig()
    } else {
      // 如果失败，询问用户是否手动输入凭证
      // 只有当错误信息暗示凭证缺失或连接失败时才建议
      const errorMsg = result.error || '未知错误'
      if (confirm(`切换失败: ${errorMsg}\n\n是否手动输入 Supabase 凭证？`)) {
        showSupabaseDialog.value = true
      }
    }
  } catch (error) {
    alert('切换请求失败: ' + String(error))
  } finally {
    switchingStorage.value = false
  }
}

// 确认切换到 Supabase
async function confirmSwitchToSupabase() {
  if (!supabaseConfig.value.url || !supabaseConfig.value.key) {
    alert('请填写 Supabase URL 和 Key')
    return
  }
  
  showSupabaseDialog.value = false
  await executeSwitch('supabase', supabaseConfig.value.url, supabaseConfig.value.key)
}

// 执行切换逻辑
async function executeSwitch(mode: string, url?: string, key?: string) {
  switchingStorage.value = true
  try {
    const payload: any = { mode }
    if (url && key) {
      payload.supabase_url = url
      payload.supabase_key = key
    }

    const response = await fetch('/api/config/storage-mode', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload)
    })
    
    const result = await response.json()
    if (result.success) {
      alert(`已成功切换到 ${mode === 'supabase' ? 'Supabase' : '本地'} 存储模式`)
      await loadConfig()
    } else {
      alert('切换失败: ' + (result.error || '未知错误'))
      // 如果失败且是尝试切换到 Supabase，重新显示对话框以便重试
      if (mode === 'supabase' && url && key) {
        showSupabaseDialog.value = true
      }
    }
  } catch (error) {
    alert('切换请求失败: ' + String(error))
  } finally {
    switchingStorage.value = false
  }
}

// 测试连接
async function testConnection() {
  if (!newProvider.value.base_url || !newProvider.value.api_key) {
    alert('请填写API地址和密钥')
    return
  }

  testingConnection.value = true
  testResult.value = null

  try {
    const response = await fetch('/api/custom-providers/test', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        api_key: newProvider.value.api_key,
        base_url: newProvider.value.base_url
      })
    })

    const result = await response.json()
    testResult.value = result

  } catch (error) {
    testResult.value = {
      success: false,
      message: '测试请求失败：' + String(error)
    }
  } finally {
    testingConnection.value = false
  }
}

// 添加服务商
async function handleAddProvider() {
  saving.value = true

  try {
    const response = await fetch('/api/custom-providers', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(newProvider.value)
    })

    const result = await response.json()

    if (result.success) {
      alert('自定义服务商添加成功！')
      
      // 重置表单
      newProvider.value = {
        provider_name: '',
        provider_type: 'openai_compatible',
        api_key: '',
        base_url: '',
        model: '',
        service_type: 'text'
      }
      
      testResult.value = null
      
      // 重新加载配置
      await loadConfig()
    } else {
      alert('添加失败：' + (result.error || '未知错误'))
    }
  } catch (error) {
    alert('添加失败：' + String(error))
  } finally {
    saving.value = false
  }
}

// 删除服务商
async function deleteProvider(name: string) {
  if (!confirm(`确定要删除服务商 "${name}" 吗？`)) {
    return
  }

  try {
    const response = await fetch(`/api/custom-providers/${encodeURIComponent(name)}`, {
      method: 'DELETE'
    })

    const result = await response.json()

    if (result.success) {
      alert('删除成功')
      await loadConfig()
    } else {
      alert('删除失败：' + (result.error || '未知错误'))
    }
  } catch (error) {
    alert('删除失败：' + String(error))
  }
}

// 激活服务商
async function setActiveProvider(name: string) {
  // 确定服务类型
  const provider = customProviders.value.find(p => p.name === name)
  if (!provider) return

  try {
    const response = await fetch(`/api/custom-providers/${encodeURIComponent(name)}/set-active`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        service_type: provider.service_type
      })
    })

    const result = await response.json()

    if (result.success) {
      alert(`已激活 ${name} 为${provider.service_type === 'text' ? '文本' : '图片'}生成服务商`)
      await loadConfig()
    } else {
      alert('激活失败：' + (result.error || '未知错误'))
    }
  } catch (error) {
    alert('激活失败：' + String(error))
  }
}

// 工具函数
function getServiceTypeLabel(type: string): string {
  switch (type) {
    case 'text': return '文本生成'
    case 'image': return '图片生成'
    default: return type
  }
}

function isProviderActive(name: string): boolean {
  return name === currentTextProvider.value || name === currentImageProvider.value
}

// 页面加载时获取配置
onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.page-header {
  margin-bottom: 2rem;
}

.page-title {
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  color: #1f2937;
}

.page-subtitle {
  font-size: 1rem;
  color: #6b7280;
}

.storage-status-container {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-top: 0.5rem;
}

.storage-status {
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 500;
}

.switch-btn {
  font-size: 0.75rem;
  padding: 0.25rem 0.75rem;
}

.storage-status.supabase {
  background-color: #dbeafe;
  color: #1e40af;
}

.storage-status.local {
  background-color: #f3f4f6;
  color: #4b5563;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem;
}

.spinner {
  width: 2rem;
  height: 2rem;
  border: 3px solid #e5e7eb;
  border-top: 3px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.custom-provider-container {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.section-title {
  font-size: 1.25rem;
  font-weight: 600;
  margin-bottom: 0.25rem;
  color: #1f2937;
}

.section-desc {
  font-size: 0.875rem;
  color: #6b7280;
}

.provider-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
}

.form-group input,
.form-group select {
  padding: 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 0.875rem;
  transition: border-color 0.15s;
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}

.btn {
  padding: 0.625rem 1.25rem;
  border: none;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background-color: #3b82f6;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #2563eb;
}

.btn-secondary {
  background-color: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
}

.btn-secondary:hover:not(:disabled) {
  background-color: #e5e7eb;
}

.btn-danger {
  background-color: #ef4444;
  color: white;
}

.btn-danger:hover {
  background-color: #dc2626;
}

.btn-small {
  padding: 0.375rem 0.75rem;
  font-size: 0.75rem;
}

.test-result {
  padding: 1rem;
  border-radius: 8px;
  border: 1px solid #d1d5db;
  background-color: #fef2f2;
}

.test-result.success {
  background-color: #f0fdf4;
  border-color: #bbf7d0;
}

.test-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.test-status {
  font-weight: 600;
}

.test-message {
  color: #6b7280;
  font-size: 0.875rem;
}

.available-models {
  margin-top: 0.75rem;
}

.models-label {
  font-size: 0.875rem;
  font-weight: 500;
  margin-bottom: 0.5rem;
  color: #374151;
}

.models-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.model-tag {
  padding: 0.25rem 0.5rem;
  background-color: #f3f4f6;
  border-radius: 4px;
  font-size: 0.75rem;
  color: #374151;
}

.model-more {
  padding: 0.25rem 0.5rem;
  background-color: #e5e7eb;
  border-radius: 4px;
  font-size: 0.75rem;
  color: #6b7280;
}

.empty-state {
  text-align: center;
  padding: 3rem 1rem;
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.empty-state p {
  color: #6b7280;
  margin-bottom: 0.5rem;
}

.empty-desc {
  font-size: 0.875rem;
}

.provider-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.provider-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background-color: #fafafa;
}

.provider-info {
  flex: 1;
}

.provider-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.provider-name {
  font-size: 1rem;
  font-weight: 600;
  color: #1f2937;
}

.provider-badges {
  display: flex;
  gap: 0.5rem;
}

.badge {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
}

.type-badge {
  background-color: #dbeafe;
  color: #1e40af;
}

.status-badge {
  background-color: #f3f4f6;
  color: #6b7280;
}

.status-badge.active {
  background-color: #dcfce7;
  color: #166534;
}

.provider-details {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.provider-model,
.provider-url {
  font-size: 0.875rem;
  color: #6b7280;
}

.provider-actions {
  display: flex;
  gap: 0.5rem;
}

.active-providers {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.active-provider-item {
  display: flex;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background-color: #fafafa;
}

.provider-label {
  font-weight: 500;
  color: #374151;
}

.provider-value {
  color: #1f2937;
  font-weight: 600;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 500px;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h3 {
  font-size: 1.25rem;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #6b7280;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.modal-body {
  padding: 1.5rem;
}

.modal-desc {
  color: #6b7280;
  margin-bottom: 1.5rem;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  padding: 1.25rem;
  border-top: 1px solid #e5e7eb;
  background-color: #f9fafb;
  border-bottom-left-radius: 12px;
  border-bottom-right-radius: 12px;
}

@media (max-width: 768px) {
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>