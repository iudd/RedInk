import yaml
import os
from pathlib import Path


class Config:
    # 基础配置
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 7860))  # Hugging Face Spaces 默认端口
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    OUTPUT_DIR = 'output'

    _image_providers_config = None
    _text_providers_config = None

    @classmethod
    def _get_config_base_path(cls):
        """获取配置文件基础路径，支持 HF Space 持久化存储"""
        # 检查是否在 HF Space 环境
        hf_data_dir = Path('/data')
        if hf_data_dir.exists() and hf_data_dir.is_dir():
            # HF Space 环境，使用持久化目录
            config_dir = hf_data_dir / 'configs'
            config_dir.mkdir(exist_ok=True)
            return config_dir
        else:
            # 本地环境，使用项目根目录
            return Path(__file__).parent.parent

    @classmethod
    def load_image_providers_config(cls):
        if cls._image_providers_config is not None:
            return cls._image_providers_config

        config_base = cls._get_config_base_path()
        config_path = config_base / 'image_providers.yaml'

        if not config_path.exists():
            # 默认配置（用户指定）
            cls._image_providers_config = {
                'active_provider': os.environ.get('ACTIVE_IMAGE_PROVIDER', 'gemini'),
                'providers': {
                    'gemini': {
                        'type': 'openai_compatible',  # 使用 OpenAI 兼容模式以支持自定义 URL
                        'api_key': os.environ.get('GEMINI_API_KEY', '1'),
                        'base_url': os.environ.get('GEMINI_BASE_URL', 'https://mind.cnzd.eu.org/v1'), # 修正为带 /v1
                        'model': os.environ.get('GEMINI_IMAGE_MODEL', 'gemini-3-image'),
                        'default_size': '1024x1024',
                        'quality': 'standard'
                    }
                }
            }
            return cls._image_providers_config

        with open(config_path, 'r', encoding='utf-8') as f:
            cls._image_providers_config = yaml.safe_load(f) or {}

        return cls._image_providers_config

    @classmethod
    def get_active_image_provider(cls):
        config = cls.load_image_providers_config()
        return config.get('active_provider', 'gemini')

    @classmethod
    def get_image_provider_config(cls, provider_name: str = None):
        config = cls.load_image_providers_config()

        if provider_name is None:
            provider_name = cls.get_active_image_provider()

        if provider_name not in config.get('providers', {}):
            # 如果找不到配置，尝试返回默认的 gemini 配置
            if provider_name == 'gemini':
                 return {
                    'type': 'openai_compatible',
                    'api_key': '1',
                    'base_url': 'https://mind.cnzd.eu.org/v1',
                    'model': 'gemini-3-image',
                    'default_size': '1024x1024',
                    'quality': 'standard'
                }
            
            available = ', '.join(config.get('providers', {}).keys())
            raise ValueError(
                f"未找到图片生成服务商配置: {provider_name}\n"
                f"可用的服务商: {available}\n"
                "解决方案：\n"
                "1. 在系统设置页面添加图片生成服务商\n"
                "2. 或检查 image_providers.yaml 文件"
            )

        provider_config = config['providers'][provider_name].copy()

        if not provider_config.get('api_key'):
            raise ValueError(
                f"服务商 {provider_name} 未配置 API Key\n"
                "解决方案：在系统设置页面编辑该服务商，填写 API Key"
            )

        return provider_config

    @classmethod
    def load_text_providers_config(cls):
        """加载文本生成配置"""
        if cls._text_providers_config is not None:
            return cls._text_providers_config

        config_base = cls._get_config_base_path()
        config_path = config_base / 'text_providers.yaml'

        if not config_path.exists():
            # 默认配置（用户指定）
            cls._text_providers_config = {
                'active_provider': os.environ.get('ACTIVE_TEXT_PROVIDER', 'openai'),
                'providers': {
                    'openai': {
                        'type': 'openai_compatible',
                        'api_key': os.environ.get('OPENAI_API_KEY', '1'),
                        'base_url': os.environ.get('OPENAI_BASE_URL', 'https://free2gpt-2api-cfwork.i13383033253-e65.workers.dev/v1'),
                        'model': os.environ.get('OPENAI_MODEL', 'gpt-4o-mini'),
                        'temperature': 0.7,
                        'max_output_tokens': 4096
                    }
                }
            }
            return cls._text_providers_config

        with open(config_path, 'r', encoding='utf-8') as f:
            cls._text_providers_config = yaml.safe_load(f) or {}

        return cls._text_providers_config

    @classmethod
    def get_active_text_provider(cls):
        config = cls.load_text_providers_config()
        return config.get('active_provider', 'openai')

    @classmethod
    def get_text_provider_config(cls, provider_name: str = None):
        """获取文本生成服务商配置"""
        config = cls.load_text_providers_config()

        if provider_name is None:
            provider_name = cls.get_active_text_provider()

        if provider_name not in config.get('providers', {}):
            available = ', '.join(config.get('providers', {}).keys())
            raise ValueError(
                f"未找到文本生成服务商配置: {provider_name}\n"
                f"可用的服务商: {available}\n"
                "解决方案：\n"
                "1. 在系统设置页面添加文本生成服务商\n"
                "2. 或检查 text_providers.yaml 文件"
            )

        provider_config = config['providers'][provider_name].copy()

        if not provider_config.get('api_key'):
            raise ValueError(
                f"服务商 {provider_name} 未配置 API Key\n"
                "解决方案：在系统设置页面编辑该服务商，填写 API Key"
            )

        return provider_config

    @classmethod
    def reload_config(cls):
        """重新加载配置（清除缓存）"""
        cls._image_providers_config = None
        cls._text_providers_config = None
