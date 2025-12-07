# Hugging Face Spaces 部署指南

## 🚀 快速部署

### 方法一：直接上传到Hugging Face Spaces

1. **创建新Space**
   - 访问 [Hugging Face Spaces](https://huggingface.co/spaces)
   - 点击 "Create new Space"
   - 选择 **Docker** SDK
   - 设置Space名称（如：`redink-ai-generator`）
   - 设置为Public或Private

2. **上传项目文件**
   ```bash
   git clone https://huggingface.co/spaces/你的用户名/redink-ai-generator
   cd redink-ai-generator
   git remote add origin https://github.com/HisMax/RedInk.git
   git pull origin main
   git push origin main
   ```

3. **配置环境变量**
   在Space的Settings > Variables中添加：
   ```
   OPENAI_API_KEY=你的OpenAI密钥
   GEMINI_API_KEY=你的Gemini密钥
   ACTIVE_TEXT_PROVIDER=openai  # 或 gemini
   ACTIVE_IMAGE_PROVIDER=gemini  # 或 openai_image
   ```

### 方法二：使用Hugging Face CLI

```bash
# 安装HF CLI
pip install huggingface_hub

# 登录
huggingface-cli login

# 创建Space
huggingface-cli space create redink-ai-generator --sdk docker

# 推送项目
git push huggingface main
```

## 📋 环境变量说明

| 变量名 | 说明 | 默认值 | 示例 |
|--------|------|--------|------|
| `OPENAI_API_KEY` | OpenAI API密钥 | - | `sk-xxxxxxxx` |
| `GEMINI_API_KEY` | Gemini API密钥 | - | `AIzaxxxxxxxx` |
| `ACTIVE_TEXT_PROVIDER` | 文本生成服务商 | `openai` | `openai`/`gemini` |
| `ACTIVE_IMAGE_PROVIDER` | 图片生成服务商 | `gemini` | `gemini`/`openai_image` |
| `OPENAI_BASE_URL` | OpenAI API地址 | `https://api.openai.com/v1` | 自定义API地址 |
| `OPENAI_MODEL` | OpenAI文本模型 | `gpt-4` | `gpt-4o`/`gpt-3.5-turbo` |
| `OPENAI_IMAGE_MODEL` | OpenAI图片模型 | `dall-e-3` | `dall-e-2` |
| `GEMINI_MODEL` | Gemini文本模型 | `gemini-2.0-flash` | `gemini-1.5-pro` |
| `GEMINI_IMAGE_MODEL` | Gemini图片模型 | `gemini-3-pro-image-preview` | - |

## 🔧 配置说明

### API服务商选择

**文本生成（文案）**：
- **OpenAI**: `gpt-4`, `gpt-4o`, `gpt-3.5-turbo`
- **Gemini**: `gemini-2.0-flash`, `gemini-1.5-pro`

**图片生成**：
- **Gemini**: `gemini-3-pro-image-preview`（推荐）
- **OpenAI**: `dall-e-3`, `dall-e-2`

### 高并发模式

Gemini支持高并发模式，可同时生成多张图片：
```yaml
# 在image_providers.yaml中设置
providers:
  gemini:
    high_concurrency: true  # 开启高并发
```

## 🚨 注意事项

1. **API配额限制**
   - GCP试用账号不建议开启高并发
   - 注意API调用费用控制

2. **端口配置**
   - 后端默认端口：`7860`（Hugging Face Spaces标准端口）
   - 前端开发端口：`5173`

3. **文件存储**
   - 生成的图片存储在 `/app/output` 目录
   - 历史记录保存在内存中，重启会清空

## 🔍 健康检查

部署完成后，访问以下端点检查状态：
- `https://你的空间地址.hf.space/api/health` - 后端健康检查
- `https://你的空间地址.hf.space/` - 前端界面

## 📊 监控和日志

在Hugging Face Spaces中：
- 查看构建日志：点击 "Logs" 标签
- 监控资源使用：右侧面板显示CPU/内存使用情况
- 查看运行日志：容器启动后的实时日志

## 🐛 常见问题

### 1. 构建失败
```bash
# 检查Dockerfile语法
docker build .
```

### 2. API调用失败
- 检查环境变量是否正确设置
- 验证API密钥是否有效
- 查看容器日志了解具体错误

### 3. 前端无法访问后端
- 确保CORS配置正确
- 检查代理设置
- 验证端口映射

### 4. 图片生成超时
- 检查API配额
- 考虑关闭高并发模式
- 调整超时设置

## 📞 技术支持

如遇到部署问题：
1. 查看Hugging Face Spaces文档
2. 检查GitHub Issues
3. 联系作者：histonemax@gmail.com