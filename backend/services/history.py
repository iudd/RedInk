import os
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
import traceback
from backend.config import Config

class HistoryService:
    def __init__(self):
        # 初始化文件存储路径
        hf_data_dir = Path('/data')
        if hf_data_dir.exists() and hf_data_dir.is_dir():
            self.history_dir = str(hf_data_dir / 'history')
        else:
            self.history_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "history"
            )
        
        os.makedirs(self.history_dir, exist_ok=True)
        self.index_file = os.path.join(self.history_dir, "index.json")
        self._init_index()

        # 尝试初始化 Supabase 客户端
        try:
            from backend.utils.supabase_client import get_supabase_client
            self.supabase = get_supabase_client()
        except Exception as e:
            print(f"HistoryService: Supabase 初始化失败 (将使用本地文件): {e}")
            self.supabase = None
            
        if self.supabase:
            print("HistoryService: 使用 Supabase 存储")
            self.enable_supabase = True
        else:
            print("HistoryService: 使用本地文件存储")
            self.enable_supabase = False

    def set_storage_mode(self, mode: str, url: Optional[str] = None, key: Optional[str] = None) -> tuple[bool, str]:
        """设置存储模式: 'supabase' 或 'local'"""
        if mode == 'supabase':
            # 如果提供了新的凭证，强制重新初始化
            if url and key:
                try:
                    from backend.utils.supabase_client import init_supabase_client
                    self.supabase = init_supabase_client(url, key)
                except Exception as e:
                    return False, f"Failed to init with provided credentials: {str(e)}"

            if not self.supabase:
                # 检查环境变量
                if not os.environ.get("SUPABASE_URL") or not os.environ.get("SUPABASE_KEY"):
                     return False, "Missing SUPABASE_URL or SUPABASE_KEY environment variables."
                
                try:
                    from backend.utils.supabase_client import get_supabase_client
                    self.supabase = get_supabase_client()
                except ImportError:
                    return False, "Supabase library not installed."
                except Exception as e:
                    return False, f"Connection failed: {str(e)}"
            
            if self.supabase:
                self.enable_supabase = True
                print("HistoryService: 已切换到 Supabase 存储")
                return True, "Success"
            return False, "Failed to initialize Supabase client (Unknown reason)."
        else:
            self.enable_supabase = False
            print("HistoryService: 已切换到本地文件存储")
            return True, "Success"

    def _init_index(self):
        if not os.path.exists(self.index_file):
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump({"records": []}, f, ensure_ascii=False, indent=2)

    # ==================== 公共接口 ====================

    def create_record(self, topic: str, outline: Dict, task_id: Optional[str] = None) -> str:
        if self.supabase and self.enable_supabase:
            return self._create_record_supabase(topic, outline, task_id)
        return self._create_record_file(topic, outline, task_id)

    def get_record(self, record_id: str) -> Optional[Dict]:
        if self.supabase and self.enable_supabase:
            return self._get_record_supabase(record_id)
        return self._get_record_file(record_id)

    def update_record(self, record_id: str, outline: Optional[Dict] = None, images: Optional[Dict] = None, status: Optional[str] = None, thumbnail: Optional[str] = None) -> bool:
        if self.supabase and self.enable_supabase:
            return self._update_record_supabase(record_id, outline, images, status, thumbnail)
        return self._update_record_file(record_id, outline, images, status, thumbnail)

    def delete_record(self, record_id: str) -> bool:
        if self.supabase and self.enable_supabase:
            return self._delete_record_supabase(record_id)
        return self._delete_record_file(record_id)

    def list_records(self, page: int = 1, page_size: int = 20, status: Optional[str] = None) -> Dict:
        if self.supabase and self.enable_supabase:
            return self._list_records_supabase(page, page_size, status)
        return self._list_records_file(page, page_size, status)

    def search_records(self, keyword: str) -> List[Dict]:
        if self.supabase and self.enable_supabase:
            return self._search_records_supabase(keyword)
        return self._search_records_file(keyword)

    def get_statistics(self) -> Dict:
        if self.supabase and self.enable_supabase:
            return self._get_statistics_supabase()
        return self._get_statistics_file()

    # ==================== Supabase 实现 ====================

    def _create_record_supabase(self, topic: str, outline: Dict, task_id: Optional[str] = None) -> str:
        try:
            record_id = str(uuid.uuid4())
            data = {
                'id': record_id,
                'title': topic,
                'outline': outline, # 直接存储 JSONB
                'task_id': task_id,
                'status': 'draft',
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            self.supabase.table('history_records').insert(data).execute()
            print(f"HistoryService: Supabase 创建记录成功: {record_id}")
            return record_id
        except Exception as e:
            print(f"Supabase 创建记录失败: {e}")
            traceback.print_exc()
            # 降级到文件
            return self._create_record_file(topic, outline, task_id)

    def _get_record_supabase(self, record_id: str) -> Optional[Dict]:
        try:
            response = self.supabase.table('history_records').select('*').eq('id', record_id).execute()
            if not response.data:
                return None
            
            record = response.data[0]
            # 构造返回格式以匹配文件存储结构
            return {
                "id": record['id'],
                "title": record['title'],
                "created_at": record['created_at'],
                "updated_at": record['updated_at'],
                "outline": record.get('outline', {}),
                "images": record.get('images', {'task_id': record.get('task_id'), 'generated': []}), # 兼容旧结构
                "status": record['status'],
                "thumbnail": record['thumbnail']
            }
        except Exception as e:
            print(f"Supabase 获取记录失败: {e}")
            traceback.print_exc()
            return None

    def _update_record_supabase(self, record_id: str, outline: Optional[Dict] = None, images: Optional[Dict] = None, status: Optional[str] = None, thumbnail: Optional[str] = None) -> bool:
        try:
            data = {'updated_at': datetime.now().isoformat()}
            if outline is not None:
                data['outline'] = outline
            if status is not None:
                data['status'] = status
            if thumbnail is not None:
                data['thumbnail'] = thumbnail
            if images is not None:
                data['images'] = images # 存储 images JSONB
                if images.get('task_id'):
                    data['task_id'] = images.get('task_id')

            self.supabase.table('history_records').update(data).eq('id', record_id).execute()
            return True
        except Exception as e:
            print(f"Supabase 更新记录失败: {e}")
            traceback.print_exc()
            return False

    def _delete_record_supabase(self, record_id: str) -> bool:
        try:
            print(f"HistoryService: 正在从 Supabase 删除记录: {record_id}")
            self.supabase.table('history_records').delete().eq('id', record_id).execute()
            print(f"HistoryService: Supabase 删除记录成功: {record_id}")
            return True
        except Exception as e:
            print(f"Supabase 删除记录失败: {e}")
            traceback.print_exc()
            return False

    def _list_records_supabase(self, page: int = 1, page_size: int = 20, status: Optional[str] = None) -> Dict:
        try:
            query = self.supabase.table('history_records').select('*', count='exact')
            if status:
                query = query.eq('status', status)
            
            start = (page - 1) * page_size
            end = start + page_size - 1
            response = query.order('created_at', desc=True).range(start, end).execute()
            
            records = []
            for r in response.data:
                # 转换格式以匹配前端预期
                records.append({
                    "id": r['id'],
                    "title": r['title'],
                    "created_at": r['created_at'],
                    "updated_at": r['updated_at'],
                    "status": r['status'],
                    "thumbnail": r['thumbnail'],
                    "page_count": len(r.get('outline', {}).get('pages', [])) if r.get('outline') else 0,
                    "task_id": r.get('task_id')
                })

            return {
                "records": records,
                "total": response.count,
                "page": page,
                "page_size": page_size,
                "total_pages": (response.count + page_size - 1) // page_size
            }
        except Exception as e:
            print(f"Supabase 获取列表失败: {e}")
            traceback.print_exc()
            return {"records": [], "total": 0, "page": 1, "page_size": 20, "total_pages": 0}

    def _search_records_supabase(self, keyword: str) -> List[Dict]:
        try:
            response = self.supabase.table('history_records').select('*').ilike('title', f'%{keyword}%').order('created_at', desc=True).execute()
            records = []
            for r in response.data:
                records.append({
                    "id": r['id'],
                    "title": r['title'],
                    "created_at": r['created_at'],
                    "status": r['status'],
                    "thumbnail": r['thumbnail']
                })
            return records
        except Exception as e:
            print(f"Supabase 搜索失败: {e}")
            return []

    def _get_statistics_supabase(self) -> Dict:
        try:
            # Supabase 暂时没有直接的 group by count API 简单调用方式，
            # 这里简单实现：获取所有 status (如果数据量大需要优化，例如使用 RPC)
            # 或者分状态查询 count
            statuses = ['draft', 'generating', 'completed', 'partial', 'failed']
            status_count = {}
            total = 0
            
            for s in statuses:
                count = self.supabase.table('history_records').select('id', count='exact').eq('status', s).execute().count
                if count:
                    status_count[s] = count
                    total += count
            
            return {
                "total": total,
                "by_status": status_count
            }
        except Exception as e:
            print(f"Supabase 统计失败: {e}")
            return {"total": 0, "by_status": {}}

    # ==================== 文件系统实现 (原有逻辑) ====================

    def _load_index(self) -> Dict:
        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"records": []}

    def _save_index(self, index: Dict):
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def _get_record_path(self, record_id: str) -> str:
        return os.path.join(self.history_dir, f"{record_id}.json")

    def _create_record_file(self, topic: str, outline: Dict, task_id: Optional[str] = None) -> str:
        record_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        record = {
            "id": record_id,
            "title": topic,
            "created_at": now,
            "updated_at": now,
            "outline": outline,
            "images": {
                "task_id": task_id,
                "generated": []
            },
            "status": "draft",
            "thumbnail": None
        }

        record_path = self._get_record_path(record_id)
        with open(record_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

        index = self._load_index()
        index["records"].insert(0, {
            "id": record_id,
            "title": topic,
            "created_at": now,
            "updated_at": now,
            "status": "draft",
            "thumbnail": None,
            "page_count": len(outline.get("pages", [])),
            "task_id": task_id
        })
        self._save_index(index)
        return record_id

    def _get_record_file(self, record_id: str) -> Optional[Dict]:
        record_path = self._get_record_path(record_id)
        if not os.path.exists(record_path):
            return None
        try:
            with open(record_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _update_record_file(self, record_id: str, outline: Optional[Dict] = None, images: Optional[Dict] = None, status: Optional[str] = None, thumbnail: Optional[str] = None) -> bool:
        record = self._get_record_file(record_id)
        if not record:
            return False

        now = datetime.now().isoformat()
        record["updated_at"] = now

        if outline is not None:
            record["outline"] = outline
        if images is not None:
            record["images"] = images
        if status is not None:
            record["status"] = status
        if thumbnail is not None:
            record["thumbnail"] = thumbnail

        record_path = self._get_record_path(record_id)
        with open(record_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

        index = self._load_index()
        for idx_record in index["records"]:
            if idx_record["id"] == record_id:
                idx_record["updated_at"] = now
                if status:
                    idx_record["status"] = status
                if thumbnail:
                    idx_record["thumbnail"] = thumbnail
                if outline:
                    idx_record["page_count"] = len(outline.get("pages", []))
                if images is not None and images.get("task_id"):
                    idx_record["task_id"] = images.get("task_id")
                break
        self._save_index(index)
        return True

    def _delete_record_file(self, record_id: str) -> bool:
        record = self._get_record_file(record_id)
        if not record:
            return False

        # 删除任务图片目录
        if record.get("images") and record["images"].get("task_id"):
            task_id = record["images"]["task_id"]
            task_dir = os.path.join(self.history_dir, task_id)
            if os.path.exists(task_dir) and os.path.isdir(task_dir):
                try:
                    import shutil
                    shutil.rmtree(task_dir)
                except Exception as e:
                    print(f"删除任务目录失败: {task_dir}, {e}")

        # 删除记录JSON文件
        record_path = self._get_record_path(record_id)
        try:
            os.remove(record_path)
        except Exception:
            return False

        # 更新索引
        index = self._load_index()
        index["records"] = [r for r in index["records"] if r["id"] != record_id]
        self._save_index(index)
        return True

    def _list_records_file(self, page: int = 1, page_size: int = 20, status: Optional[str] = None) -> Dict:
        index = self._load_index()
        records = index.get("records", [])
        if status:
            records = [r for r in records if r.get("status") == status]
        
        total = len(records)
        start = (page - 1) * page_size
        end = start + page_size
        page_records = records[start:end]

        return {
            "records": page_records,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    def _search_records_file(self, keyword: str) -> List[Dict]:
        index = self._load_index()
        records = index.get("records", [])
        keyword_lower = keyword.lower()
        return [r for r in records if keyword_lower in r.get("title", "").lower()]

    def _get_statistics_file(self) -> Dict:
        index = self._load_index()
        records = index.get("records", [])
        total = len(records)
        status_count = {}
        for record in records:
            status = record.get("status", "draft")
            status_count[status] = status_count.get(status, 0) + 1
        return {"total": total, "by_status": status_count}

    # 保持原有的 scan_and_sync_task_images 和 scan_all_tasks 方法
    # 这些方法主要操作文件系统中的图片，Supabase 模式下可能需要调整
    # 但目前先保持文件系统操作，因为图片生成服务还是写文件的
    
    def scan_and_sync_task_images(self, task_id: str) -> Dict[str, Any]:
        # ... (保持原有逻辑，但 update_record 会自动分发到 Supabase)
        task_dir = os.path.join(self.history_dir, task_id)

        if not os.path.exists(task_dir) or not os.path.isdir(task_dir):
            return {"success": False, "error": f"任务目录不存在: {task_id}"}

        try:
            image_files = []
            for filename in os.listdir(task_dir):
                if filename.startswith('thumb_'): continue
                if filename.endswith(('.png', '.jpg', '.jpeg')):
                    image_files.append(filename)

            def get_index(filename):
                try: return int(filename.split('.')[0])
                except: return 999
            image_files.sort(key=get_index)

            # 查找关联记录
            # 注意：这里需要遍历所有记录，效率较低。
            # 在 Supabase 模式下，应该直接查询 task_id
            record_id = None
            
            if self.supabase:
                # Supabase 查询
                resp = self.supabase.table('history_records').select('id').eq('task_id', task_id).execute()
                if resp.data:
                    record_id = resp.data[0]['id']
            else:
                # 文件查询
                index = self._load_index()
                for rec in index.get("records", []):
                    if rec.get("task_id") == task_id:
                        record_id = rec["id"]
                        break
                    # 兼容旧数据结构：检查详情
                    if not record_id:
                        detail = self._get_record_file(rec["id"])
                        if detail and detail.get("images", {}).get("task_id") == task_id:
                            record_id = rec["id"]
                            break

            if record_id:
                record = self.get_record(record_id)
                if record:
                    expected_count = len(record.get("outline", {}).get("pages", []))
                    actual_count = len(image_files)
                    
                    if actual_count == 0: status = "draft"
                    elif actual_count >= expected_count: status = "completed"
                    else: status = "partial"

                    self.update_record(
                        record_id,
                        images={"task_id": task_id, "generated": image_files},
                        status=status,
                        thumbnail=image_files[0] if image_files else None
                    )
                    return {
                        "success": True, 
                        "record_id": record_id, 
                        "task_id": task_id, 
                        "images_count": len(image_files), 
                        "images": image_files, 
                        "status": status
                    }

            return {
                "success": True, 
                "task_id": task_id, 
                "images_count": len(image_files), 
                "images": image_files, 
                "no_record": True
            }

        except Exception as e:
            return {"success": False, "error": f"扫描任务失败: {str(e)}"}

    def scan_all_tasks(self) -> Dict[str, Any]:
        if not os.path.exists(self.history_dir):
            return {"success": False, "error": "历史记录目录不存在"}

        try:
            synced_count = 0
            failed_count = 0
            orphan_tasks = []
            results = []

            for item in os.listdir(self.history_dir):
                item_path = os.path.join(self.history_dir, item)
                if not os.path.isdir(item_path): continue
                
                task_id = item
                result = self.scan_and_sync_task_images(task_id)
                results.append(result)

                if result.get("success"):
                    if result.get("no_record"): orphan_tasks.append(task_id)
                    else: synced_count += 1
                else:
                    failed_count += 1

            return {
                "success": True,
                "total_tasks": len(results),
                "synced": synced_count,
                "failed": failed_count,
                "orphan_tasks": orphan_tasks,
                "results": results
            }
        except Exception as e:
            return {"success": False, "error": f"扫描所有任务失败: {str(e)}"}


_service_instance = None

def get_history_service() -> HistoryService:
    global _service_instance
    if _service_instance is None:
        _service_instance = HistoryService()
    return _service_instance
