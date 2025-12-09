from typing import Any, Optional
import os

_supabase_client = None

def get_supabase_client() -> Optional[Any]:
    """获取 Supabase 客户端实例 (延迟加载以避免依赖问题)"""
    global _supabase_client
    
    if _supabase_client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            return None
        
        try:
            # 延迟导入，防止因缺少依赖导致整个应用崩溃
            from supabase import create_client, Client
            
            # 初始化客户端
            # 注意：Supabase Python 客户端默认没有显式的全局超时设置
            # 连接超时通常由底层的 httpx/requests 控制
            _supabase_client = create_client(url, key)
            
        except ImportError:
            print("Warning: 'supabase' module not found. Running in local-only mode.")
            return None
        except Exception as e:
            print(f"Supabase Client Initialization Failed: {e}")
            return None
    
    return _supabase_client

def init_supabase_client(url: str, key: str) -> Optional[Any]:
    """使用提供的凭证强制初始化 Supabase 客户端"""
    global _supabase_client
    try:
        from supabase import create_client
        _supabase_client = create_client(url, key)
        # 更新环境变量，以便后续自动获取也能工作
        os.environ["SUPABASE_URL"] = url
        os.environ["SUPABASE_KEY"] = key
        return _supabase_client
    except Exception as e:
        print(f"Supabase Explicit Initialization Failed: {e}")
        return None
