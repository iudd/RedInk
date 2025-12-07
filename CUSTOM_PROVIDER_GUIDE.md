# 自定义服务商配置指南

## 🎯 功能概述

RedInk现在支持添加自定义的OpenAI兼容AI服务商，让您可以：
- 配置任意OpenAI兼容的文本生成API
- 配置自定义的图片生成服务
- 测试连接状态
- 一键切换服务商

## 📋 支持的服务商类型

### 文本生成
- **OpenAI兼容接口**：所有兼容OpenAI API格式的服务商
- **Google Gemini**：Google官方Gemini API

### 图片生成  
- **图片API**：支持图片生成的OpenAI兼容接口
- **Google Gemini图片**：Gemini的图片生成能力

## 🚀 快速开始

### 1. 访问配置页面
在红墨应用中，点击左侧菜单的"自定义服务商"进入配置页面。

### 2. 添加自定义服务商

#### 基本信息
- **服务商名称**：自定义标识名，如"我的AI服务"
- **服务类型**：选择"文本生成"或"图片生成"
- **服务商类型**：选择API协议类型
- **模型名称**：指定要使用的模型
- **API地址**：服务商的API端点
- **API密钥**：您的API访问密钥

#### 示例配置

**示例1：自定义OpenAI兼容文本服务**
```
服务商名称：我的GPT服务
服务类型：文本生成
服务商类型：OpenAI兼容
模型名称：gpt-4
API地址：https://api.example.com/v1
API密钥：sk-xxxxxxxxxxxxx
```

**示例2：自定义图片生成服务**
```
服务商名称：我的图片AI
服务类型：图片生成
服务商类型：图片API
模型名称：dall-e-3
API地址：https://api.example.com/v1
API密钥：sk-xxxxxxxxxxxxx
```

### 3. 测试连接
填写完配置后，点击"测试连接"按钮验证：
- API地址是否可达
- API密钥是否有效
- 获取可用模型列表

### 4. 激活服务商
测试成功后，点击"添加服务商"，然后在列表中点击"激活"按钮使其生效。

## 🔧 高级配置

### 环境变量支持

除了Web界面配置，您也可以通过环境变量设置默认配置：

```bash
# 文本生成服务商
OPENAI_API_KEY=sk-xxxxxxxxxxxxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4
ACTIVE_TEXT_PROVIDER=openai

# 图片生成服务商  
GEMINI_API_KEY=AIzaxxxxxxxxxxxxxxxxx
ACTIVE_IMAGE_PROVIDER=gemini

# 配置存储目录
CONFIG_DIR=/app/configs
```

### 配置文件位置

- **自定义配置**：`/app/configs/custom_providers.json`
- **默认文本配置**：`text_providers.yaml`
- **默认图片配置**：`image_providers.yaml`

## 🛡️ 安全特性

### API密钥安全
- **存储加密**：API密钥在存储时进行加密处理
- **传输安全**：使用HTTPS传输敏感信息
- **显示脱敏**：界面中只显示密钥的前后4位

### 访问控制
- 配置文件存储在应用专属目录
- 支持环境变量覆盖配置
- 容器内部网络隔离

## 📊 使用场景

### 1. 企业内部AI服务
```yaml
# 配置企业内部AI服务
服务商名称：公司GPT服务
API地址：https://ai.company.com/api/v1
模型名称：gpt-4-turbo
```

### 2. 第三方API服务商
```yaml
# 配置第三方聚合服务
服务商名称：API聚合平台
API地址：https://api.openai-proxy.com/v1
模型名称：gpt-4o
```

### 3. 本地部署模型
```yaml
# 配置本地模型服务
服务商名称：本地LLM
API地址：http://localhost:8000/v1
模型名称：llama-3.1-8b
```

## 🔍 故障排除

### 常见问题

**1. 连接测试失败**
- 检查API地址格式是否正确
- 确认API密钥有效
- 验证网络连接状态

**2. 模型不可用**
- 确认模型名称拼写正确
- 检查服务商是否支持该模型
- 查看API使用配额

**3. 生成失败**
- 确认服务商已激活
- 检查API配额限制
- 查看服务商状态

### 调试方法

**查看容器日志**
```bash
docker logs <container_id>
```

**检查配置文件**
```bash
# 查看自定义配置
cat /app/configs/custom_providers.json
```

**手动测试API**
```bash
curl -H "Authorization: Bearer <API_KEY>" \
     https://your-api-endpoint/v1/models
```

## 🔄 配置迁移

### 导出配置
```bash
# 备份自定义配置
cp /app/configs/custom_providers.json backup/
```

### 导入配置
将配置文件放置在`/app/configs/custom_providers.json`，重启容器自动加载。

## 📞 技术支持

如遇到问题：
1. 查看本文档的故障排除部分
2. 检查Hugging Face Space的构建日志
3. 在GitHub提交Issue
4. 联系作者：histonemax@gmail.com

## 🎉 最佳实践

1. **测试先行**：添加服务商前务必测试连接
2. **命名规范**：使用有意义的服务商名称
3. **密钥管理**：定期更换API密钥
4. **性能监控**：关注服务商的响应时间和稳定性
5. **备用方案**：配置多个服务商作为备用

---

通过自定义服务商功能，RedInk可以灵活适配各种AI服务，满足不同场景的使用需求。