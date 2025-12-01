---
title: RedInk 小红书AI图文生成器
emoji: 📝
colorFrom: red
colorTo: pink
sdk: docker
app_file: hf_proxy.py
pinned: false
license: cc-by-nc-sa-4.0
---

# RedInk - 小红书AI图文生成器

让传播不再需要门槛，让创作从未如此简单

## 部署说明

本项目已适配Hugging Face Spaces部署，支持以下特性：

- ✅ 自动化Docker构建
- ✅ 前后端一体化部署
- ✅ 反向代理整合
- ✅ 单端口访问（7860）
- ✅ 环境变量配置
- ✅ 健康检查端点

## Hugging Face Space 端口配置

### 端口映射方案：
- **主端口 7860**: 通过反向代理同时服务前端和后端API
  - 前端页面: `https://your-space.hf.space/`
  - API接口: `https://your-space.hf.space/api/*`

### 配置说明：
1. HF Space自动暴露端口7860
2. 内部运行反向代理服务器
3. 前端静态文件通过7860端口直接服务
4. API请求(`/*`)自动代理到后端服务

## 环境变量配置

在Space设置中配置以下环境变量：

- `OPENAI_API_KEY`: OpenAI API密钥
- `GEMINI_API_KEY`: Google Gemini API密钥
- `ACTIVE_TEXT_PROVIDER`: 文本生成服务商 (openai/gemini)
- `ACTIVE_IMAGE_PROVIDER`: 图片生成服务商 (openai_image/gemini)

## 使用方法

1. 访问部署的Space主页面
2. 在设置页面配置API密钥
3. 输入创作主题
4. 生成小红书图文内容

## 技术架构

- 后端: Python Flask + AI模型
- 前端: Vue 3 + TypeScript + Vite
- 代理: Flask反向代理整合前后端
- 部署: Docker + Hugging Face Spaces