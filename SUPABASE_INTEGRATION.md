# Supabase 集成方案

## 概述

本文档说明如何将 RedInk 项目迁移到 Supabase，实现数据持久化存储。

## 为什么需要 Supabase？

在 Hugging Face Space 部署时：
- **容器重启问题**：容器重启后非持久化数据会丢失
- **存储限制**：HF Space 只有 `/data` 目录是持久化的
- **扩展性**：Supabase 提供更好的数据管理和查询能力

## 方案设计

### 1. 数据存储结构

#### 1.1 配置表 (configurations)
```sql
CREATE TABLE configurations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  config_type VARCHAR(50) NOT NULL, -- 'text_generation' 或 'image_generation'
  provider_name VARCHAR(100) NOT NULL,
  provider_type VARCHAR(50) NOT NULL,
  api_key TEXT,
  base_url TEXT,
  model VARCHAR(100),
  high_concurrency BOOLEAN DEFAULT false,
  is_active BOOLEAN DEFAULT false,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(config_type, provider_name)
);
```

#### 1.2 历史记录表 (history_records)
```sql
CREATE TABLE history_records (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  title TEXT NOT NULL,
  outline_raw TEXT,
  outline_pages JSONB,
  task_id VARCHAR(100),
  status VARCHAR(20) DEFAULT 'draft',
  thumbnail TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_history_created_at ON history_records(created_at DESC);
CREATE INDEX idx_history_status ON history_records(status);
```

#### 1.3 生成图片记录表 (generated_images)
```sql
CREATE TABLE generated_images (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  record_id UUID REFERENCES history_records(id) ON DELETE CASCADE,
  task_id VARCHAR(100),
  page_index INTEGER,
  image_url TEXT,
  storage_path TEXT, -- Supabase Storage 路径
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_images_record_id ON generated_images(record_id);
CREATE INDEX idx_images_task_id ON generated_images(task_id);
```

### 2. Supabase Storage 结构

```
redink-images/
├── tasks/
│   ├── {task_id}/
│   │   ├── 0.png
│   │   ├── 1.png
│   │   ├── thumb_0.png
│   │   └── thumb_1.png
└── thumbnails/
    └── {record_id}.png
```

## 实现步骤

### 步骤 1: 安装依赖

```bash
pip install supabase
```

在 `requirements.txt` 添加：
```
supabase>=2.0.0
```

### 步骤 2: 配置环境变量

在 HF Space Secrets 中添加：
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key
```

### 步骤 3: 创建 Supabase 客户端

创建 `backend/utils/supabase_client.py`:

```python
from supabase import create_client, Client
import os

_supabase_client: Client = None

def get_supabase_client() -> Client:
    """获取 Supabase 客户端实例"""
    global _supabase_client
    
    if _supabase_client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            raise ValueError("SUPABASE_URL 和 SUPABASE_KEY 环境变量必须设置")
        
        _supabase_client = create_client(url, key)
    
    return _supabase_client
```

### 步骤 4: 创建配置服务 (Supabase 版本)

创建 `backend/services/config_supabase.py`:

```python
from typing import Dict, Any, Optional, List
from backend.utils.supabase_client import get_supabase_client

class SupabaseConfigService:
    """基于 Supabase 的配置管理服务"""
    
    def __init__(self):
        self.client = get_supabase_client()
    
    def get_providers(self, config_type: str) -> Dict[str, Any]:
        """获取指定类型的所有服务商配置"""
        response = self.client.table('configurations').select('*').eq('config_type', config_type).execute()
        
        providers = {}
        active_provider = None
        
        for row in response.data:
            provider_name = row['provider_name']
            providers[provider_name] = {
                'type': row['provider_type'],
                'api_key': row['api_key'],
                'base_url': row.get('base_url'),
                'model': row.get('model'),
                'high_concurrency': row.get('high_concurrency', False)
            }
            
            if row.get('is_active'):
                active_provider = provider_name
        
        return {
            'active_provider': active_provider or '',
            'providers': providers
        }
    
    def save_provider(self, config_type: str, provider_name: str, config: Dict[str, Any]) -> bool:
        """保存或更新服务商配置"""
        try:
            data = {
                'config_type': config_type,
                'provider_name': provider_name,
                'provider_type': config.get('type'),
                'api_key': config.get('api_key'),
                'base_url': config.get('base_url'),
                'model': config.get('model'),
                'high_concurrency': config.get('high_concurrency', False)
            }
            
            # 使用 upsert 来插入或更新
            self.client.table('configurations').upsert(data).execute()
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
    
    def set_active_provider(self, config_type: str, provider_name: str) -> bool:
        """设置激活的服务商"""
        try:
            # 先将所有同类型的设为非激活
            self.client.table('configurations').update({'is_active': False}).eq('config_type', config_type).execute()
            
            # 再将指定的设为激活
            self.client.table('configurations').update({'is_active': True}).eq('config_type', config_type).eq('provider_name', provider_name).execute()
            
            return True
        except Exception as e:
            print(f"设置激活服务商失败: {e}")
            return False
    
    def delete_provider(self, config_type: str, provider_name: str) -> bool:
        """删除服务商配置"""
        try:
            self.client.table('configurations').delete().eq('config_type', config_type).eq('provider_name', provider_name).execute()
            return True
        except Exception as e:
            print(f"删除配置失败: {e}")
            return False
```

### 步骤 5: 创建历史记录服务 (Supabase 版本)

创建 `backend/services/history_supabase.py`:

```python
from typing import Dict, Any, Optional, List
from backend.utils.supabase_client import get_supabase_client
import uuid

class SupabaseHistoryService:
    """基于 Supabase 的历史记录服务"""
    
    def __init__(self):
        self.client = get_supabase_client()
    
    def create_record(self, title: str, outline: Dict[str, Any], task_id: Optional[str] = None) -> str:
        """创建历史记录"""
        record_id = str(uuid.uuid4())
        
        data = {
            'id': record_id,
            'title': title,
            'outline_raw': outline.get('raw', ''),
            'outline_pages': outline.get('pages', []),
            'task_id': task_id,
            'status': 'draft'
        }
        
        self.client.table('history_records').insert(data).execute()
        return record_id
    
    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        """获取历史记录详情"""
        response = self.client.table('history_records').select('*').eq('id', record_id).execute()
        
        if not response.data:
            return None
        
        record = response.data[0]
        
        # 获取关联的图片
        images_response = self.client.table('generated_images').select('*').eq('record_id', record_id).order('page_index').execute()
        
        return {
            'id': record['id'],
            'title': record['title'],
            'created_at': record['created_at'],
            'updated_at': record['updated_at'],
            'outline': {
                'raw': record['outline_raw'],
                'pages': record['outline_pages']
            },
            'images': {
                'task_id': record['task_id'],
                'generated': [img['image_url'] for img in images_response.data]
            },
            'status': record['status'],
            'thumbnail': record['thumbnail']
        }
    
    def list_records(self, page: int = 1, page_size: int = 20, status: Optional[str] = None) -> Dict[str, Any]:
        """获取历史记录列表"""
        offset = (page - 1) * page_size
        
        query = self.client.table('history_records').select('*', count='exact')
        
        if status:
            query = query.eq('status', status)
        
        response = query.order('created_at', desc=True).range(offset, offset + page_size - 1).execute()
        
        return {
            'records': response.data,
            'total': response.count,
            'page': page,
            'page_size': page_size,
            'total_pages': (response.count + page_size - 1) // page_size
        }
    
    def update_record(self, record_id: str, **kwargs) -> bool:
        """更新历史记录"""
        try:
            update_data = {}
            
            if 'outline' in kwargs:
                update_data['outline_raw'] = kwargs['outline'].get('raw')
                update_data['outline_pages'] = kwargs['outline'].get('pages')
            
            if 'status' in kwargs:
                update_data['status'] = kwargs['status']
            
            if 'thumbnail' in kwargs:
                update_data['thumbnail'] = kwargs['thumbnail']
            
            if update_data:
                self.client.table('history_records').update(update_data).eq('id', record_id).execute()
            
            # 更新图片记录
            if 'images' in kwargs:
                images = kwargs['images']
                task_id = images.get('task_id')
                generated = images.get('generated', [])
                
                # 删除旧的图片记录
                self.client.table('generated_images').delete().eq('record_id', record_id).execute()
                
                # 插入新的图片记录
                for idx, img_url in enumerate(generated):
                    self.client.table('generated_images').insert({
                        'record_id': record_id,
                        'task_id': task_id,
                        'page_index': idx,
                        'image_url': img_url
                    }).execute()
            
            return True
        except Exception as e:
            print(f"更新记录失败: {e}")
            return False
    
    def delete_record(self, record_id: str) -> bool:
        """删除历史记录"""
        try:
            self.client.table('history_records').delete().eq('id', record_id).execute()
            return True
        except Exception as e:
            print(f"删除记录失败: {e}")
            return False
    
    def search_records(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索历史记录"""
        response = self.client.table('history_records').select('*').ilike('title', f'%{keyword}%').execute()
        return response.data
```

### 步骤 6: 图片存储到 Supabase Storage

在 `backend/services/image.py` 中添加上传到 Supabase Storage 的功能：

```python
from backend.utils.supabase_client import get_supabase_client

def upload_to_supabase_storage(image_data: bytes, task_id: str, filename: str) -> str:
    """上传图片到 Supabase Storage"""
    client = get_supabase_client()
    
    # 构建存储路径
    storage_path = f"tasks/{task_id}/{filename}"
    
    # 上传到 Supabase Storage
    client.storage.from_('redink-images').upload(
        storage_path,
        image_data,
        file_options={"content-type": "image/png"}
    )
    
    # 获取公开 URL
    public_url = client.storage.from_('redink-images').get_public_url(storage_path)
    
    return public_url
```

## 迁移步骤

### 1. 在 Supabase 创建项目
1. 访问 https://supabase.com
2. 创建新项目
3. 记录 Project URL 和 API Keys

### 2. 创建数据库表
在 Supabase SQL Editor 中执行上述 SQL 语句

### 3. 创建 Storage Bucket
1. 在 Supabase Dashboard 进入 Storage
2. 创建名为 `redink-images` 的 bucket
3. 设置为 Public（或根据需求设置权限）

### 4. 配置环境变量
在 HF Space Settings -> Repository secrets 添加：
- `SUPABASE_URL`
- `SUPABASE_KEY`

### 5. 切换到 Supabase 服务
修改相关导入，从文件存储切换到 Supabase 存储

## 优势

1. **持久化存储**：数据不会因容器重启而丢失
2. **更好的查询能力**：支持复杂查询和全文搜索
3. **实时功能**：可以使用 Supabase Realtime 功能
4. **扩展性**：易于添加新功能（如用户系统、分享功能等）
5. **备份和恢复**：Supabase 提供自动备份

## 注意事项

1. **API Key 安全**：确保使用 Service Role Key 进行敏感操作
2. **存储限制**：注意 Supabase 免费版的存储限制（500MB）
3. **RLS 策略**：建议配置 Row Level Security 保护数据
4. **成本**：评估使用量，可能需要升级到付费计划

## 下一步

如果需要实现 Supabase 集成，我可以：
1. 创建完整的 Supabase 服务类
2. 修改现有代码以使用 Supabase
3. 提供数据迁移脚本
4. 添加环境变量配置开关（支持本地文件存储和 Supabase 两种模式）
