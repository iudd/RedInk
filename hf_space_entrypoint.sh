#!/bin/bash

# Hugging Face Space 入口脚本
set -e

echo "🚀 启动红墨AI图文生成器 (HF Space模式)..."

# 确保输出目录存在
mkdir -p /app/output /app/configs

# 设置环境变量
export PYTHONPATH=/app
export HOST=0.0.0.0
export PORT=7860
export CONFIG_DIR=/app/configs

# 复制配置文件
if [ -f "/app/text_providers.yaml.example" ] && [ ! -f "/app/configs/text_providers.yaml" ]; then
    cp /app/text_providers.yaml.example /app/configs/text_providers.yaml
fi

if [ -f "/app/image_providers.yaml.example" ] && [ ! -f "/app/configs/image_providers.yaml" ]; then
    cp /app/image_providers.yaml.example /app/configs/image_providers.yaml
fi

echo "📝 配置文件已准备完成"

# 构建前端（如果还没有构建）
if [ ! -d "/app/frontend/dist" ]; then
    echo "🎨 构建前端..."
    cd /app/frontend
    pnpm install
    pnpm build
    cd /app
fi

echo "🔧 启动服务..."

# 使用HF代理模式启动
/app/.venv/bin/python /app/hf_proxy.py