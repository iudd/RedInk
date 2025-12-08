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
            return None
        
        try:
            _supabase_client = create_client(url, key)
        except Exception as e:
            print(f"Supabase 连接失败: {e}")
            return None
    
    return _supabase_client
