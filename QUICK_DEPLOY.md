# 🚀 快速部署指南

## 问题
在 Hugging Face Space 部署时，自定义服务商配置无法保存，容器重启后配置丢失。

## 解决方案
✅ **已修复！** 配置和历史记录现在保存到 HF Space 的持久化目录 `/data`

## 修改的文件
```
backend/config.py          - 配置文件路径管理
backend/routes/api.py      - API 配置读写
backend/services/history.py - 历史记录存储
```

## 部署命令

```bash
# 1. 查看修改
git status

# 2. 提交代码
git add backend/config.py backend/routes/api.py backend/services/history.py
git commit -m "fix: 修复 HF Space 数据持久化问题"

# 3. 推送到 HF Space
git push
```

## 验证步骤

### 1️⃣ 测试配置持久化
1. 访问你的 HF Space
2. 进入"系统设置"
3. 添加一个服务商配置
4. 重启 Space（或等待自动重启）
5. 确认配置仍然存在 ✅

### 2️⃣ 测试历史记录持久化
1. 生成一个图文
2. 查看"历史记录"
3. 重启 Space
4. 确认记录仍然存在 ✅

## 存储路径

| 数据 | HF Space | 本地 |
|------|---------|------|
| 配置 | `/data/configs/*.yaml` | `{项目根}/*.yaml` |
| 历史 | `/data/history/` | `{项目根}/history/` |

## ⚠️ 重要提示

1. **首次部署后需要重新配置**
   - 旧的配置不会自动迁移
   - 需要在 UI 中重新添加服务商

2. **历史记录**
   - 旧的历史记录会丢失
   - 新生成的记录会持久化保存

## 📚 详细文档

- `FIX_SUMMARY.md` - 完整修复总结
- `CONFIG_PERSISTENCE_FIX.md` - 配置持久化详细说明
- `SUPABASE_INTEGRATION.md` - Supabase 集成方案（可选）

## 🎯 Supabase 迁移（可选）

如果需要更可靠的数据存储和更多功能：

1. 创建 Supabase 项目
2. 配置环境变量：
   ```
   SUPABASE_URL=https://xxx.supabase.co
   SUPABASE_KEY=your-key
   ```
3. 参考 `SUPABASE_INTEGRATION.md` 实施

## ✅ 完成！

现在你的 RedInk 应用可以在 HF Space 上可靠地保存配置和历史记录了！

---

**需要帮助？** 查看 `FIX_SUMMARY.md` 中的故障排查部分
