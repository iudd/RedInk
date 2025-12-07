# 📦 Hugging Face Spaces 部署文件清单

## 🚀 必需的核心文件

### 🐳 Docker部署文件
- `Dockerfile` - Docker镜像构建配置 ✅
- `docker-entrypoint.sh` - 容器启动入口点 ✅
- `docker/start.sh` - 服务启动脚本 ✅
- `.dockerignore` - Docker构建忽略文件 ✅

### 📋 项目配置文件
- `README.md` - 项目说明（更新为HF版本）✅
- `requirements.txt` - Python依赖列表 ✅
- `hf-space-requirements.txt` - HF空间专用依赖 ✅
- `pyproject.toml` - Python项目配置 ✅
- `text_providers.yaml.example` - 文本服务配置模板 ✅
- `image_providers.yaml.example` - 图片服务配置模板 ✅

### 📚 部署文档
- `DEPLOY_GUIDE.md` - 部署指南 ✅
- `CUSTOM_PROVIDER_GUIDE.md` - 自定义服务商指南 ✅

---

## 🏗️ 后端文件结构

### ⚙️ 核心应用文件
- `backend/__init__.py` - Python包初始化 ✅
- `backend/app.py` - Flask应用主入口 ✅
- `backend/config.py` - 配置管理模块（已更新支持环境变量）✅

### 🛣️ API路由
- `backend/routes/__init__.py` - 路由包初始化 ✅
- `backend/routes/api.py` - API路由（已添加自定义配置API）✅

### 🔄 业务服务
- `backend/services/__init__.py` - 服务包初始化 ✅
- `backend/services/config.py` - 自定义配置管理服务 ✅
- `backend/services/outline.py` - 文本生成服务 ✅
- `backend/services/image.py` - 图片生成服务 ✅
- `backend/services/history.py` - 历史记录服务 ✅

### 🤖 AI生成器
- `backend/generators/__init__.py` - 生成器包初始化 ✅
- `backend/generators/base.py` - 基础生成器类 ✅
- `backend/generators/factory.py` - 生成器工厂 ✅
- `backend/generators/openai_compatible.py` - OpenAI兼容生成器 ✅
- `backend/generators/google_genai.py` - Gemini生成器 ✅
- `backend/generators/image_api.py` - 图片API生成器 ✅

### 📝 提示词模板
- `backend/prompts/outline_prompt.txt` - 文本生成提示词 ✅
- `backend/prompts/image_prompt.txt` - 图片生成提示词 ✅

### 🔧 工具模块
- `backend/utils/__init__.py` - 工具包初始化 ✅
- `backend/utils/genai_client.py` - Gemini客户端 ✅
- `backend/utils/text_client.py` - 文本客户端 ✅
- `backend/utils/image_compressor.py` - 图片压缩工具 ✅

---

## 🎨 前端文件结构

### 🏠 基础配置
- `frontend/index.html` - HTML入口文件 ✅
- `frontend/package.json` - 前端依赖配置 ✅
- `frontend/pnpm-lock.yaml` - 依赖锁定文件 ✅
- `frontend/tsconfig.json` - TypeScript配置 ✅
- `frontend/tsconfig.node.json` - Node.js TypeScript配置 ✅
- `frontend/vite.config.ts` - Vite构建配置 ✅

### 🖼️ 静态资源
- `frontend/public/logo.png` - 应用Logo ✅
- `frontend/public/showcase1.png` - 展示图片 ✅
- `frontend/public/assets/` - 资源目录
  - `showcase_manifest.json` - 展示图片清单 ✅
  - `avatars/user_avatar.webp` - 用户头像 ✅
  - `showcase/` - 展示图片集 ✅

### 💻 源代码
- `frontend/src/main.ts` - 应用入口 ✅
- `frontend/src/App.vue` - 主应用组件（已添加自定义配置菜单）✅
- `frontend/src/router/index.ts` - 路由配置（已添加自定义配置路由）✅
- `frontend/src/api/index.ts` - API接口封装 ✅
- `frontend/src/stores/generator.ts` - 状态管理 ✅

### 📄 页面组件
- `frontend/src/views/HomeView.vue` - 首页 ✅
- `frontend/src/views/OutlineView.vue` - 大纲页面 ✅
- `frontend/src/views/GenerateView.vue` - 生成页面 ✅
- `frontend/src/views/ResultView.vue` - 结果页面 ✅
- `frontend/src/views/HistoryView.vue` - 历史记录页面 ✅
- `frontend/src/views/SettingsView.vue` - 系统设置页面 ✅
- `frontend/src/views/CustomProviderView.vue` - **新增：自定义配置页面** ✅

---

## 📁 其他必要目录

### 📂 运行时目录
- `history/` - 历史记录存储目录
- `history/.gitkeep` - 保持目录在git中

### 🖼️ 项目图片
- `images/` - 项目展示图片
  - `logo.png` - Logo文件
  - `coffee.jpg` - 赞赏码
  - `example-*.png` - 使用示例
  - `index.gif` - 动态演示

---

## 🗑️ 可以排除的文件

### Git配置（已排除）
- `.gitignore` - Git忽略配置
- `uv.lock` - UV锁定文件（部署时不需要）

### 开发文件（建议排除）
- `.git/` - Git仓库目录
- `node_modules/` - 依赖包
- `__pycache__/` - Python缓存
- `dist/` - 前端构建输出

---

## ✅ 部署前检查清单

### 📋 文件完整性
- [ ] 所有必需文件已创建 ✅
- [ ] 配置文件已更新 ✅
- [ ] 新功能已集成 ✅
- [ ] 文档已编写 ✅

### 🔧 配置验证
- [ ] Dockerfile语法正确 ✅
- [ ] 启动脚本可执行 ✅
- [ ] 环境变量配置正确 ✅
- [ ] 路由配置有效 ✅

### 🌐 功能测试
- [ ] 后端API正常响应 ✅
- [ ] 前端页面可访问 ✅
- [ ] 自定义配置功能完整 ✅
- [ ] 图片生成流程正常 ✅

---

## 🚀 快速部署命令

### 方法一：直接上传
```bash
# 1. 创建Hugging Face Space（Docker SDK）
# 2. 克隆Space仓库
git clone https://huggingface.co/spaces/你的用户名/redink-ai-generator
cd redink-ai-generator

# 3. 复制项目文件
cp -r /path/to/RedInk/* .

# 4. 提交并推送
git add .
git commit -m "部署RedInk到Hugging Face Spaces"
git push origin main
```

### 方法二：Hugging Face CLI
```bash
# 安装HF CLI
pip install huggingface_hub

# 登录
huggingface-cli login

# 创建Space
huggingface-cli space create redink-ai-generator --sdk docker

# 推送
git remote add huggingface https://huggingface.co/spaces/你的用户名/redink-ai-generator
git push huggingface main
```

---

## 🌍 环境变量配置

在Hugging Face Space的Settings > Variables中设置：

```env
OPENAI_API_KEY=sk-你的OpenAI密钥
GEMINI_API_KEY=AIza你的Gemini密钥
ACTIVE_TEXT_PROVIDER=openai
ACTIVE_IMAGE_PROVIDER=gemini
DEBUG=false
HOST=0.0.0.0
PORT=7860
CONFIG_DIR=/app/configs
```

---

## 📞 部署完成后验证

1. **访问地址**：`https://你的空间名称.hf.space`
2. **健康检查**：`/api/health`
3. **自定义配置**：点击左侧"自定义服务商"
4. **功能测试**：创建一个小红书图文

**恭喜！🎉 您的RedInk已成功部署到Hugging Face Spaces！**