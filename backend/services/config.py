"""配置管理服务"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from backend.config import Config
import traceback

class ConfigService:
    """配置管理服务，支持持久化存储（文件系统或 Supabase）"""
    
    def __init__(self):
        self.config_dir = Config._get_config_base_path()
        self.config_dir.mkdir(exist_ok=True)
        
        # 尝试初始化 Supabase 客户端
        try:
            from backend.utils.supabase_client import get_supabase_client
            self.supabase = get_supabase_client()
            if self.supabase:
                print("ConfigService: Supabase 客户端初始化成功")
            else:
                print("ConfigService: Supabase 客户端初始化返回 None (可能缺少环境变量)")
        except Exception as e:
            print(f"ConfigService: Supabase 初始化失败 (将使用本地文件): {e}")
            self.supabase = None
        
        if self.supabase:
            print("ConfigService: 使用 Supabase 存储")
        else:
            print("ConfigService: 使用本地文件存储")

    def get_full_config(self) -> Dict[str, Any]:
        """获取完整配置（用于 API 返回）"""
        if self.supabase:
            return self._get_full_config_supabase()
        else:
            return self._get_full_config_file()

    def update_full_config(self, data: Dict[str, Any]) -> bool:
        """更新完整配置"""
        if self.supabase:
            return self._update_full_config_supabase(data)
        else:
            return self._update_full_config_file(data)

    # ==================== Supabase 实现 ====================

    def _get_full_config_supabase(self) -> Dict[str, Any]:
        try:
            print("ConfigService: 正在从 Supabase 获取配置...")
            # 获取所有配置
            response = self.supabase.table('configurations').select('*').execute()
            rows = response.data
            print(f"ConfigService: 获取到 {len(rows)} 条配置记录")
            
            # 如果 Supabase 为空，尝试从本地文件迁移
            if not rows:
                print("ConfigService: Supabase 配置为空，尝试从本地文件迁移...")
                local_config = self._get_full_config_file()
                
                # 只有当本地配置非空时才迁移
                if local_config.get('text_generation', {}).get('providers') or \
                   local_config.get('image_generation', {}).get('providers'):
                    print("ConfigService: 正在将本地配置迁移到 Supabase...")
                    self._update_full_config_supabase(local_config)
                    return local_config
                else:
                    print("ConfigService: 本地配置也为空，跳过迁移")

            text_providers = {}
            image_providers = {}
            active_text = ""
            active_image = ""
            
            for row in rows:
                config_type = row.get('config_type')
                name = row.get('provider_name')
                
                if not config_type or not name:
                    continue

                provider_config = {
                    'type': row.get('provider_type', 'openai_compatible'),
                    'api_key': row.get('api_key', ''),
                    'base_url': row.get('base_url'),
                    'model': row.get('model'),
                    # 恢复其他可能的字段
                    'high_concurrency': row.get('high_concurrency', False)
                }
                
                if config_type == 'text_generation':
                    text_providers[name] = provider_config
                    if row.get('is_active'):
                        active_text = name
                elif config_type == 'image_generation':
                    image_providers[name] = provider_config
                    if row.get('is_active'):
                        active_image = name

            # 如果没有配置，返回默认结构
            result = {
                "text_generation": {
                    "active_provider": active_text or 'openai',
                    "providers": text_providers
                },
                "image_generation": {
                    "active_provider": active_image or 'gemini',
                    "providers": image_providers
                }
            }
            return result
        except Exception as e:
            print(f"Supabase 获取配置失败: {e}")
            traceback.print_exc()
            # 降级到文件或返回空
            return self._get_full_config_file()

    def _update_full_config_supabase(self, data: Dict[str, Any]) -> bool:
        try:
            print("ConfigService: 正在更新 Supabase 配置...")
            # 更新文本生成配置
            if 'text_generation' in data:
                self._save_provider_group_supabase('text_generation', data['text_generation'])
            
            # 更新图片生成配置
            if 'image_generation' in data:
                self._save_provider_group_supabase('image_generation', data['image_generation'])
                
            # 清除内存缓存
            Config.reload_config()
            print("ConfigService: Supabase 配置更新成功")
            return True
        except Exception as e:
            print(f"Supabase 更新配置失败: {e}")
            traceback.print_exc()
            return False

    def _save_provider_group_supabase(self, config_type: str, group_data: Dict[str, Any]):
        active_provider = group_data.get('active_provider')
        providers = group_data.get('providers', {})
        
        print(f"ConfigService: 保存 {config_type} 配置, 激活服务商: {active_provider}, 服务商数量: {len(providers)}")

        # 1. 更新 active 状态
        if active_provider:
            # 先将该类型所有设为非激活
            self.supabase.table('configurations').update({'is_active': False}).eq('config_type', config_type).execute()
        
        # 2. 遍历保存每个 provider
        for name, config in providers.items():
            # 准备数据
            row_data = {
                'config_type': config_type,
                'provider_name': name,
                'provider_type': config.get('type', 'openai_compatible'),
                'base_url': config.get('base_url'),
                'model': config.get('model'),
                'high_concurrency': config.get('high_concurrency', False)
            }
            
            # 处理 API Key
            # 如果是前端传来的空字符串或掩码，不要更新数据库中的 key
            api_key = config.get('api_key')
            if api_key and not api_key.startswith('sk-****') and api_key != '':
                row_data['api_key'] = api_key
            
            # 设置激活状态
            if active_provider and name == active_provider:
                row_data['is_active'] = True
            else:
                row_data['is_active'] = False
            
            # 执行 upsert (根据 config_type + provider_name 唯一约束)
            # 注意：Supabase upsert 需要指定 on_conflict
            self.supabase.table('configurations').upsert(
                row_data, 
                on_conflict='config_type,provider_name'
            ).execute()

    # ==================== 文件系统实现 (原有逻辑封装) ====================

    def _get_full_config_file(self) -> Dict[str, Any]:
        try:
            import yaml
            
            # 读取图片配置
            image_config_path = self.config_dir / 'image_providers.yaml'
            if image_config_path.exists():
                with open(image_config_path, 'r', encoding='utf-8') as f:
                    image_config = yaml.safe_load(f) or {}
            else:
                image_config = {'active_provider': 'gemini', 'providers': {}}

            # 读取文本配置
            text_config_path = self.config_dir / 'text_providers.yaml'
            if text_config_path.exists():
                with open(text_config_path, 'r', encoding='utf-8') as f:
                    text_config = yaml.safe_load(f) or {}
            else:
                text_config = {'active_provider': 'openai', 'providers': {}}

            return {
                "text_generation": {
                    "active_provider": text_config.get('active_provider', ''),
                    "providers": text_config.get('providers', {})
                },
                "image_generation": {
                    "active_provider": image_config.get('active_provider', ''),
                    "providers": image_config.get('providers', {})
                }
            }
        except Exception as e:
            print(f"文件加载配置失败: {e}")
            traceback.print_exc()
            return {
                "text_generation": {"active_provider": "openai", "providers": {}},
                "image_generation": {"active_provider": "gemini", "providers": {}}
            }

    def _update_full_config_file(self, data: Dict[str, Any]) -> bool:
        import yaml
        
        try:
            # 更新图片配置
            if 'image_generation' in data:
                self._save_yaml_file('image_providers.yaml', data['image_generation'])
            
            # 更新文本配置
            if 'text_generation' in data:
                self._save_yaml_file('text_providers.yaml', data['text_generation'])
            
            Config.reload_config()
            return True
        except Exception as e:
            print(f"文件保存配置失败: {e}")
            traceback.print_exc()
            return False

    def _save_yaml_file(self, filename: str, new_data: Dict[str, Any]):
        import yaml
        file_path = self.config_dir / filename
        
        # 读取现有配置以保留 API Key
        existing_config = {}
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                existing_config = yaml.safe_load(f) or {}
        
        final_config = {'providers': {}}
        
        if 'active_provider' in new_data:
            final_config['active_provider'] = new_data['active_provider']
        else:
            final_config['active_provider'] = existing_config.get('active_provider')

        if 'providers' in new_data:
            existing_providers = existing_config.get('providers', {})
            new_providers = new_data['providers']
            
            for name, new_conf in new_providers.items():
                # 处理 API Key 保留逻辑
                if new_conf.get('api_key') in [True, False, '', None]:
                    if name in existing_providers and existing_providers[name].get('api_key'):
                        new_conf['api_key'] = existing_providers[name]['api_key']
                    else:
                        new_conf.pop('api_key', None)
                
                # 清理字段
                new_conf.pop('api_key_env', None)
                new_conf.pop('api_key_masked', None)
            
            final_config['providers'] = new_providers
        
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(final_config, f, allow_unicode=True, default_flow_style=False)

    def get_all_providers(self) -> Dict[str, Any]:
        """获取所有可用服务商"""
        if self.supabase:
            return self._get_all_providers_supabase()
        else:
            return self._get_all_providers_file()

    def add_custom_provider(self, provider_name: str, provider_type: str, api_key: str, base_url: str, model: str, service_type: str = "text") -> bool:
        """添加自定义服务商"""
        if self.supabase:
            return self._add_custom_provider_supabase(provider_name, provider_type, api_key, base_url, model, service_type)
        else:
            return self._add_custom_provider_file(provider_name, provider_type, api_key, base_url, model, service_type)

    def delete_custom_provider(self, provider_name: str) -> bool:
        """删除自定义服务商"""
        if self.supabase:
            return self._delete_custom_provider_supabase(provider_name)
        else:
            return self._delete_custom_provider_file(provider_name)

    def set_active_provider(self, provider_name: str, service_type: str) -> bool:
        """设置激活的服务商"""
        if self.supabase:
            return self._set_active_provider_supabase(provider_name, service_type)
        else:
            return self._set_active_provider_file(provider_name, service_type)

    # ==================== Supabase 扩展实现 ====================

    def _get_all_providers_supabase(self) -> Dict[str, Any]:
        try:
            print("ConfigService: 正在从 Supabase 获取所有服务商...")
            response = self.supabase.table('configurations').select('*').execute()
            rows = response.data
            print(f"ConfigService: 从 Supabase 获取到 {len(rows) if rows else 0} 条配置记录")
            
            # 如果 Supabase 为空，尝试从本地文件迁移
            if not rows:
                print("ConfigService: Supabase 服务商列表为空，尝试从本地文件迁移...")
                local_config = self._get_full_config_file()
                
                if local_config.get('text_generation', {}).get('providers') or \
                   local_config.get('image_generation', {}).get('providers'):
                    print("ConfigService: 正在将本地配置迁移到 Supabase (触发自列表查询)...")
                    self._update_full_config_supabase(local_config)
                    # 重新查询
                    response = self.supabase.table('configurations').select('*').execute()
                    rows = response.data
            
            custom_providers = {}
            active_text = "openai"
            active_image = "gemini"
            
            if rows:
                for row in rows:
                    name = row['provider_name']
                    config_type = row['config_type']
                    
                    # 统一格式
                    provider_data = {
                        "type": row['provider_type'],
                        "api_key": row['api_key'],
                        "base_url": row.get('base_url'),
                        "model": row.get('model'),
                        "service_type": "text" if config_type == 'text_generation' else "image",
                        "created_at": row.get('created_at')
                    }
                    custom_providers[name] = provider_data
                    
                    if row.get('is_active'):
                        if config_type == 'text_generation':
                            active_text = name
                        elif config_type == 'image_generation':
                            active_image = name
            
            return {
                "custom_providers": custom_providers,
                "active_text_provider": active_text,
                "active_image_provider": active_image
            }
        except Exception as e:
            print(f"Supabase 获取所有服务商失败: {e}")
            import traceback
            traceback.print_exc()
            return self._get_all_providers_file()

    def _add_custom_provider_supabase(self, provider_name: str, provider_type: str, api_key: str, base_url: str, model: str, service_type: str) -> bool:
        try:
            config_type = 'text_generation' if service_type == 'text' else 'image_generation'
            
            data = {
                'config_type': config_type,
                'provider_name': provider_name,
                'provider_type': provider_type,
                'api_key': api_key,
                'base_url': base_url,
                'model': model,
                'is_active': False # 默认不激活
            }
            
            self.supabase.table('configurations').upsert(
                data, 
                on_conflict='config_type,provider_name'
            ).execute()
            
            Config.reload_config()
            return True
        except Exception as e:
            print(f"Supabase 添加服务商失败: {e}")
            return False

    def _delete_custom_provider_supabase(self, provider_name: str) -> bool:
        try:
            # 删除时可能需要知道 config_type，但这里只给了 name。
            # 尝试删除匹配 name 的记录 (假设 name 是全局唯一的，或者删除所有匹配的)
            # 为了安全，先查询
            self.supabase.table('configurations').delete().eq('provider_name', provider_name).execute()
            Config.reload_config()
            return True
        except Exception as e:
            print(f"Supabase 删除服务商失败: {e}")
            return False

    def _set_active_provider_supabase(self, provider_name: str, service_type: str) -> bool:
        try:
            config_type = 'text_generation' if service_type == 'text' else 'image_generation'
            
            # 1. 将该类型所有服务商设为非激活
            self.supabase.table('configurations').update({'is_active': False}).eq('config_type', config_type).execute()
            
            # 2. 将指定服务商设为激活
            self.supabase.table('configurations').update({'is_active': True}).eq('config_type', config_type).eq('provider_name', provider_name).execute()
            
            Config.reload_config()
            return True
        except Exception as e:
            print(f"Supabase 激活服务商失败: {e}")
            return False

    # ==================== 文件系统扩展实现 ====================

    def _get_all_providers_file(self) -> Dict[str, Any]:
        # 从 YAML 读取并合并
        full_config = self._get_full_config_file()
        text_conf = full_config.get('text_generation', {})
        image_conf = full_config.get('image_generation', {})
        
        custom_providers = {}
        
        for name, conf in text_conf.get('providers', {}).items():
            conf['service_type'] = 'text'
            custom_providers[name] = conf
            
        for name, conf in image_conf.get('providers', {}).items():
            conf['service_type'] = 'image'
            custom_providers[name] = conf
            
        return {
            "custom_providers": custom_providers,
            "active_text_provider": text_conf.get('active_provider', 'openai'),
            "active_image_provider": image_conf.get('active_provider', 'gemini')
        }

    def _add_custom_provider_file(self, provider_name: str, provider_type: str, api_key: str, base_url: str, model: str, service_type: str) -> bool:
        try:
            import yaml
            filename = 'text_providers.yaml' if service_type == 'text' else 'image_providers.yaml'
            file_path = self.config_dir / filename
            
            config = {}
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
            
            if 'providers' not in config:
                config['providers'] = {}
                
            config['providers'][provider_name] = {
                'type': provider_type,
                'api_key': api_key,
                'base_url': base_url,
                'model': model
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
                
            Config.reload_config()
            return True
        except Exception as e:
            print(f"文件添加服务商失败: {e}")
            return False

    def _delete_custom_provider_file(self, provider_name: str) -> bool:
        try:
            import yaml
            # 尝试从两个文件中删除
            for filename in ['text_providers.yaml', 'image_providers.yaml']:
                file_path = self.config_dir / filename
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        config = yaml.safe_load(f) or {}
                    
                    if 'providers' in config and provider_name in config['providers']:
                        del config['providers'][provider_name]
                        
                        with open(file_path, 'w', encoding='utf-8') as f:
                            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
            
            Config.reload_config()
            return True
        except Exception as e:
            print(f"文件删除服务商失败: {e}")
            return False

    def _set_active_provider_file(self, provider_name: str, service_type: str) -> bool:
        try:
            import yaml
            filename = 'text_providers.yaml' if service_type == 'text' else 'image_providers.yaml'
            file_path = self.config_dir / filename
            
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                
                config['active_provider'] = provider_name
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
                
                Config.reload_config()
                return True
            return False
        except Exception as e:
            print(f"文件激活服务商失败: {e}")
            return False

    def test_provider_connection(self, provider_config: Dict[str, Any]) -> Dict[str, Any]:
        """测试服务商连接"""
        try:
            import requests
            
            headers = {
                "Authorization": f"Bearer {provider_config.get('api_key', '')}",
                "Content-Type": "application/json"
            }
            
            # 构建测试请求
            base_url = provider_config.get('base_url', '')
            if not base_url:
                 return {"success": False, "message": "Base URL 为空"}

            test_url = f"{base_url.rstrip('/')}/models"
            
            # 有些 API 可能不支持 /models，尝试简单的 chat completion
            try:
                response = requests.get(test_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    models = response.json().get("data", [])
                    return {
                        "success": True,
                        "message": "连接成功",
                        "models": [model.get("id", "") for model in models if model.get("id")]
                    }
            except:
                pass
            
            # 如果 /models 失败，尝试 chat completion
            chat_url = f"{base_url.rstrip('/')}/chat/completions"
            if base_url.endswith('/v1'):
                 chat_url = f"{base_url}/chat/completions"
            
            payload = {
                "model": provider_config.get('model', 'gpt-3.5-turbo'),
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5
            }
            
            response = requests.post(chat_url, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                 return {"success": True, "message": "连接成功 (Chat测试通过)"}
            else:
                 return {
                    "success": False,
                    "message": f"连接失败: HTTP {response.status_code}",
                    "error": response.text
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"连接测试失败: {str(e)}",
                "error": str(e)
            }

# 全局实例
_config_service = None

def get_config_service() -> ConfigService:
    """获取配置服务实例"""
    global _config_service
    if _config_service is None:
        _config_service = ConfigService()
    return _config_service