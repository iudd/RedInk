# 配置持久化修复说明

## 问题描述

在 Hugging Face Space 部署时，自定义服务商配置无法保存，容器重启后配置丢失。

## 根本原因

1. **配置文件保存位置错误**：配置被保存到项目根目录 `/app/image_providers.yaml` 和 `/app/text_providers.yaml`
2. **HF Space 特性**：只有 `/data` 目录在容器重启后会保持数据
3. **结果**：容器重启后，保存在 `/app` 目录的配置文件会丢失

## 解决方案

### 已修复的文件

1. **backend/config.py**
   - 添加 `_get_config_base_path()` 方法
   - 自动检测运行环境（HF Space 或本地）
   - HF Space 环境：使用 `/data/configs` 目录
   - 本地环境：使用项目根目录

2. **backend/routes/api.py**
   - 更新 `get_config()` 函数
   - 更新 `update_config()` 函数
   - 使用新的路径获取方法

### 工作原理

```python
def _get_config_base_path():
    """获取配置文件基础路径，支持 HF Space 持久化存储"""
    from pathlib import Path
    
    # 检查是否在 HF Space 环境
    hf_data_dir = Path('/data')
    if hf_data_dir.exists() and hf_data_dir.is_dir():
        # HF Space 环境，使用持久化目录
        config_dir = hf_data_dir / 'configs'
        config_dir.mkdir(exist_ok=True)
        return config_dir
    else:
        # 本地环境，使用项目根目录
        return Path(__file__).parent.parent.parent
```

### 配置文件位置

| 环境 | 配置文件路径 | 持久化 |
|------|------------|--------|
| HF Space | `/data/configs/image_providers.yaml` | ✅ 是 |
| HF Space | `/data/configs/text_providers.yaml` | ✅ 是 |
| 本地开发 | `{项目根目录}/image_providers.yaml` | ✅ 是 |
| 本地开发 | `{项目根目录}/text_providers.yaml` | ✅ 是 |

## 部署到 HF Space

### 1. 提交代码

```bash
git add backend/config.py backend/routes/api.py
git commit -m "fix: 修复 HF Space 配置持久化问题"
git push
```

### 2. 在 HF Space 重新部署

代码推送后，HF Space 会自动重新构建和部署。

### 3. 验证修复

1. 访问你的 HF Space 应用
2. 进入"系统设置"页面
3. 添加或编辑服务商配置
4. 保存配置
5. 等待几分钟，让 HF Space 重启容器（或手动重启）
6. 再次访问"系统设置"页面
7. 确认配置仍然存在 ✅

## 本地测试

如果想在本地测试 HF Space 环境：

```bash
# 创建模拟的 /data 目录
mkdir -p /data/configs

# 运行应用
python backend/app.py
```

配置将被保存到 `/data/configs/` 目录。

## 历史记录持久化

历史记录目前保存在 `history/` 目录，在 HF Space 中也会丢失。

### 快速修复（使用 /data 目录）

修改 `backend/services/history.py`：

```python
def __init__(self):
    # 检查是否在 HF Space 环境
    hf_data_dir = Path('/data')
    if hf_data_dir.exists() and hf_data_dir.is_dir():
        self.history_dir = hf_data_dir / 'history'
    else:
        self.history_dir = Path(__file__).parent.parent.parent / 'history'
    
    self.history_dir.mkdir(exist_ok=True)
```

### 长期方案（使用 Supabase）

参考 `SUPABASE_INTEGRATION.md` 文档，将数据迁移到 Supabase。

## Supabase 集成（推荐）

如果需要更可靠的数据持久化和更好的扩展性，建议迁移到 Supabase：

### 优势
- ✅ 完全的数据持久化
- ✅ 支持复杂查询
- ✅ 自动备份
- ✅ 易于扩展（添加用户系统、分享功能等）
- ✅ 免费额度足够个人使用

### 实施步骤
详见 `SUPABASE_INTEGRATION.md` 文档。

## 常见问题

### Q: 为什么不直接使用环境变量存储配置？
A: 环境变量适合存储简单的键值对，但服务商配置较复杂（包含多个字段），使用文件或数据库更合适。

### Q: /data 目录有大小限制吗？
A: HF Space 免费版的持久化存储限制为 50GB，足够存储配置文件和历史记录。

### Q: 如果我想同时支持本地文件和 Supabase 怎么办？
A: 可以添加环境变量 `USE_SUPABASE=true/false` 来切换存储后端。

### Q: 配置文件会自动迁移吗？
A: 不会。首次部署修复后的代码时，需要重新在 UI 中配置服务商。

## 测试清单

- [ ] 本地环境：配置保存和读取正常
- [ ] HF Space：添加服务商配置
- [ ] HF Space：编辑服务商配置
- [ ] HF Space：删除服务商配置
- [ ] HF Space：切换激活的服务商
- [ ] HF Space：容器重启后配置仍然存在
- [ ] HF Space：生成图文功能正常

## 下一步

1. **立即修复**：已完成 ✅
   - 配置文件持久化已修复
   - 代码已更新

2. **可选优化**：
   - 修复历史记录持久化（使用 /data 目录）
   - 迁移到 Supabase（长期方案）

3. **部署**：
   - 提交代码到 Git
   - 推送到 HF Space
   - 验证功能

## 联系支持

如果遇到问题：
1. 检查 HF Space 日志
2. 确认 `/data` 目录存在且可写
3. 验证配置文件路径是否正确
