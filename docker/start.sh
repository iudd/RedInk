#!/bin/bash

# 启动脚本 - 用于Hugging Face Spaces部署

set -e

echo "🚀 启动红墨AI图文生成器..."

# 确保输出目录和配置目录存在
mkdir -p /app/output
mkdir -p /app/configs

# 设置环境变量
export PYTHONPATH=/app
export HOST=${HOST:-0.0.0.0}
export PORT=${PORT:-7860}
export CONFIG_DIR=/app/configs
export TIMESTAMP=$(date +%s)

# 创建默认配置文件（如果不存在）
if [ ! -f /app/text_providers.yaml ]; then
    cat > /app/text_providers.yaml << EOF
# 当前激活的服务商
active_provider: ${ACTIVE_TEXT_PROVIDER:-openai}

providers:
  # OpenAI 兼容接口
  openai:
    type: openai_compatible
    api_key: ${OPENAI_API_KEY:-}
    base_url: ${OPENAI_BASE_URL:-https://api.openai.com/v1}
    model: ${OPENAI_MODEL:-gpt-4}

  # Google Gemini
  gemini:
    type: google_gemini
    api_key: ${GEMINI_API_KEY:-}
    model: ${GEMINI_MODEL:-gemini-2.0-flash}
EOF
fi

if [ ! -f /app/image_providers.yaml ]; then
    cat > /app/image_providers.yaml << EOF
# 当前激活的服务商
active_provider: ${ACTIVE_IMAGE_PROVIDER:-gemini}

providers:
  # Google Gemini 图片生成
  gemini:
    type: google_genai
    api_key: ${GEMINI_API_KEY:-}
    model: ${GEMINI_IMAGE_MODEL:-gemini-3-pro-image-preview}
    high_concurrency: false

  # OpenAI 兼容图片生成
  openai_image:
    type: image_api
    api_key: ${OPENAI_API_KEY:-}
    base_url: ${OPENAI_BASE_URL:-https://api.openai.com/v1}
    model: ${OPENAI_IMAGE_MODEL:-dall-e-3}
    high_concurrency: false
EOF
fi

echo "📝 配置文件已准备完成"

# 在HF Space模式下，后端服务由代理服务器处理
# 不在这里启动独立的Flask后端服务，避免端口冲突
echo "🔧 后端服务将由代理服务器统一处理..."

# 在HF Space模式下，前端构建后由代理服务器统一服务
echo "🎨 构建前端应用..."
cd /app/frontend

# 构建前端应用到静态文件
pnpm build

echo "✅ 前端应用构建完成"
echo "🔧 代理服务器将统一处理前端和API请求"