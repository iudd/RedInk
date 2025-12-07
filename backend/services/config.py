"""配置管理服务"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from backend.config import Config


class ConfigService:
    """配置管理服务，支持持久化存储"""
    
    def __init__(self):
        self.config_dir = Config._get_config_base_path()
        self.config_dir.mkdir(exist_ok=True)
        self.custom_config_file = self.config_dir / 'custom_providers.json'
        self._config_cache = {}
    
    def load_custom_providers(self) -> Dict[str, Any]:
        """加载自定义服务商配置"""
        try:
            if self.custom_config_file.exists():
                with open(self.custom_config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"加载自定义配置失败: {e}")
        
        # 返回默认配置
        return {
            "custom_providers": {},
            "active_text_provider": os.environ.get('ACTIVE_TEXT_PROVIDER', 'openai'),
            "active_image_provider": os.environ.get('ACTIVE_IMAGE_PROVIDER', 'gemini')
        }
    
    def save_custom_providers(self, config: Dict[str, Any]) -> bool:
        """保存自定义服务商配置"""
        try:
            with open(self.custom_config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            # 更新缓存
            self._config_cache = config
            return True
        except Exception as e:
            print(f"保存自定义配置失败: {e}")
            return False
    
    def get_custom_provider_config(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """获取特定自定义服务商配置"""
        config = self.load_custom_providers()
        return config.get("custom_providers", {}).get(provider_name)
    
    def add_custom_provider(self, 
                           provider_name: str,
                           provider_type: str,
                           api_key: str,
                           base_url: str,
                           model: str,
                           service_type: str = "text") -> bool:
        """添加自定义服务商"""
        try:
            config = self.load_custom_providers()
            
            custom_provider = {
                "type": provider_type,
                "api_key": api_key,
                "base_url": base_url,
                "model": model,
                "service_type": service_type,  # "text" 或 "image"
                "created_at": str(os.environ.get('TIMESTAMP', ''))
            }
            
            if "custom_providers" not in config:
                config["custom_providers"] = {}
            
            config["custom_providers"][provider_name] = custom_provider
            
            return self.save_custom_providers(config)
        except Exception as e:
            print(f"添加自定义服务商失败: {e}")
            return False
    
    def delete_custom_provider(self, provider_name: str) -> bool:
        """删除自定义服务商"""
        try:
            config = self.load_custom_providers()
            
            if "custom_providers" in config and provider_name in config["custom_providers"]:
                del config["custom_providers"][provider_name]
                
                # 如果删除的是当前激活的服务商，重置为默认
                if config.get("active_text_provider") == provider_name:
                    config["active_text_provider"] = "openai"
                if config.get("active_image_provider") == provider_name:
                    config["active_image_provider"] = "gemini"
                
                return self.save_custom_providers(config)
            
            return False
        except Exception as e:
            print(f"删除自定义服务商失败: {e}")
            return False
    
    def set_active_provider(self, provider_name: str, service_type: str) -> bool:
        """设置激活的服务商"""
        try:
            config = self.load_custom_providers()
            
            if service_type == "text":
                config["active_text_provider"] = provider_name
            elif service_type == "image":
                config["active_image_provider"] = provider_name
            else:
                return False
            
            return self.save_custom_providers(config)
        except Exception as e:
            print(f"设置激活服务商失败: {e}")
            return False
    
    def get_all_providers(self) -> Dict[str, Any]:
        """获取所有可用服务商（包括自定义）"""
        custom_config = self.load_custom_providers()
        result = {
            "custom_providers": custom_config.get("custom_providers", {}),
            "active_text_provider": custom_config.get("active_text_provider", "openai"),
            "active_image_provider": custom_config.get("active_image_provider", "gemini")
        }
        
        # 加载默认配置
        try:
            text_providers = Config.load_text_providers_config()
            image_providers = Config.load_image_providers_config()
            
            result["default_text_providers"] = text_providers.get("providers", {})
            result["default_image_providers"] = image_providers.get("providers", {})
        except Exception as e:
            print(f"加载默认配置失败: {e}")
            result["default_text_providers"] = {}
            result["default_image_providers"] = {}
        
        return result
    
    def test_provider_connection(self, provider_config: Dict[str, Any]) -> Dict[str, Any]:
        """测试服务商连接"""
        try:
            import requests
            
            headers = {
                "Authorization": f"Bearer {provider_config['api_key']}",
                "Content-Type": "application/json"
            }
            
            # 构建测试请求
            test_url = f"{provider_config['base_url'].rstrip('/')}/models"
            
            response = requests.get(test_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                models = response.json().get("data", [])
                return {
                    "success": True,
                    "message": "连接成功",
                    "models": [model.get("id", "") for model in models if model.get("id")]
                }
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