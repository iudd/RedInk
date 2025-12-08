"""图片生成服务"""
import os
import uuid
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Generator, List, Optional, Tuple
from backend.config import Config
from backend.generators.factory import ImageGeneratorFactory
from backend.utils.image_compressor import compress_image
from backend.services.config import get_config_service
from backend.services.history import get_history_service

class ImageService:
    """图片生成服务类"""

    # 并发配置
    MAX_CONCURRENT = 2  # 默认最大并发数（降低以避免限流）
    AUTO_RETRY_COUNT = 3  # 自动重试次数

    def __init__(self, provider_name: str = None):
        """
        初始化图片生成服务

        Args:
            provider_name: 指定的服务商名称，如果为None则使用配置中的默认值
        """
        # 获取配置服务
        config_service = get_config_service()
        full_config = config_service.get_full_config()
        image_config = full_config.get('image_generation', {})
        
        # 确定使用的 provider
        if not provider_name:
            provider_name = image_config.get('active_provider')
        
        if not provider_name:
            raise ValueError("未配置激活的图片生成服务商")
            
        providers = image_config.get('providers', {})
        if provider_name not in providers:
            raise ValueError(f"找不到服务商配置: {provider_name}")
            
        self.provider_config = providers[provider_name]
        self.provider_type = self.provider_config.get('type', 'openai_compatible')
        
        # 初始化生成器
        self.generator = ImageGeneratorFactory.create(self.provider_type, self.provider_config)
        
        # 任务状态存储 (内存中)
        self._task_states = {}
        
        # 历史记录根目录
        hf_data_dir = os.path.join('/data', 'history')
        if os.path.exists('/data') and os.path.isdir('/data'):
             self.history_root_dir = hf_data_dir
        else:
             self.history_root_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "history"
            )
        os.makedirs(self.history_root_dir, exist_ok=True)

    def generate_images(
        self,
        pages: List[Dict],
        task_id: str = None,
        full_outline: str = "",
        user_images: List[bytes] = None,
        user_topic: str = ""
    ) -> Generator[Dict[str, Any], None, None]:
        """
        生成图片（生成器模式）

        Args:
            pages: 页面列表 [{"index": 0, "image_prompt": "..."}]
            task_id: 任务ID (可选)
            full_outline: 完整大纲内容 (用于上下文)
            user_images: 用户上传的参考图片列表 (bytes)
            user_topic: 用户输入的原始主题

        Yields:
            生成进度事件
        """
        if not task_id:
            task_id = str(uuid.uuid4())

        # 初始化任务状态
        self._task_states[task_id] = {
            "total": len(pages),
            "generated": {},
            "failed": {},
            "cover_image": None,
            "full_outline": full_outline
        }

        # 准备目录
        task_dir = os.path.join(self.history_root_dir, task_id)
        os.makedirs(task_dir, exist_ok=True)

        # 压缩用户上传的图片
        compressed_user_images = []
        if user_images:
            for img_bytes in user_images:
                compressed = compress_image(img_bytes, max_size=(1024, 1024))
                if compressed:
                    compressed_user_images.append(compressed)

        # 分离封面和其他页面
        cover_page = None
        other_pages = []
        for page in pages:
            if page.get("index") == 0:
                cover_page = page
            else:
                other_pages.append(page)

        total = len(pages)
        generated_images = []
        failed_pages = []
        cover_image_data = None

        # ==================== 第一阶段：生成封面 ====================
        if cover_page:
            yield {
                "event": "progress",
                "data": {
                    "index": 0,
                    "status": "generating_cover",
                    "message": "正在生成封面...",
                    "current": 0,
                    "total": total,
                    "phase": "cover"
                }
            }

            # 生成封面
            index, success, filename, error = self._generate_single_image(
                cover_page,
                task_id,
                None, # 封面没有参考图
                0, # retry_count
                full_outline,
                compressed_user_images,
                user_topic
            )

            if success:
                generated_images.append(filename)
                self._task_states[task_id]["generated"][0] = filename
                
                # 读取封面图片数据作为后续参考
                try:
                    with open(os.path.join(task_dir, filename), "rb") as f:
                        cover_image_data = f.read()
                    self._task_states[task_id]["cover_image"] = cover_image_data
                except Exception as e:
                    print(f"读取封面图片失败: {e}")

                yield {
                    "event": "complete",
                    "data": {
                        "index": 0,
                        "status": "done",
                        "image_url": f"/api/images/{task_id}/{filename}",
                        "phase": "cover"
                    }
                }
            else:
                failed_pages.append(cover_page)
                self._task_states[task_id]["failed"][0] = error
                yield {
                    "event": "error",
                    "data": {
                        "index": 0,
                        "status": "error",
                        "message": error,
                        "retryable": True,
                        "phase": "cover"
                    }
                }

        # ==================== 第二阶段：生成其他页面 ====================
        if other_pages:
            # 检查是否启用高并发模式
            high_concurrency = self.provider_config.get('high_concurrency', False)
            
            # 获取配置的并发数，默认为类定义的 MAX_CONCURRENT
            max_workers = self.provider_config.get('max_concurrent', self.MAX_CONCURRENT)

            if high_concurrency:
                # 高并发模式：并行生成
                yield {
                    "event": "progress",
                    "data": {
                        "status": "batch_start",
                        "message": f"开始并发生成 {len(other_pages)} 页内容 (并发数: {max_workers})...",
                        "current": len(generated_images),
                        "total": total,
                        "phase": "content"
                    }
                }

                # 使用线程池并发生成
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # 提交所有任务
                    future_to_page = {
                        executor.submit(
                            self._generate_single_image,
                            page,
                            task_id,
                            cover_image_data,  # 使用封面作为参考
                            0,  # retry_count
                            full_outline,  # 传入完整大纲
                            compressed_user_images,  # 用户上传的参考图片（已压缩）
                            user_topic  # 用户原始输入
                        ): page
                        for page in other_pages
                    }

                    # 发送每个页面的进度
                    for page in other_pages:
                        yield {
                            "event": "progress",
                            "data": {
                                "index": page["index"],
                                "status": "generating",
                                "current": len(generated_images) + 1,
                                "total": total,
                                "phase": "content"
                            }
                        }

                    # 收集结果
                    for future in as_completed(future_to_page):
                        page = future_to_page[future]
                        try:
                            index, success, filename, error = future.result()

                            if success:
                                generated_images.append(filename)
                                self._task_states[task_id]["generated"][index] = filename

                                yield {
                                    "event": "complete",
                                    "data": {
                                        "index": index,
                                        "status": "done",
                                        "image_url": f"/api/images/{task_id}/{filename}",
                                        "phase": "content"
                                    }
                                }
                            else:
                                failed_pages.append(page)
                                self._task_states[task_id]["failed"][index] = error

                                yield {
                                    "event": "error",
                                    "data": {
                                        "index": index,
                                        "status": "error",
                                        "message": error,
                                        "retryable": True,
                                        "phase": "content"
                                    }
                                }

                        except Exception as e:
                            failed_pages.append(page)
                            error_msg = str(e)
                            self._task_states[task_id]["failed"][page["index"]] = error_msg

                            yield {
                                "event": "error",
                                "data": {
                                    "index": page["index"],
                                    "status": "error",
                                    "message": error_msg,
                                    "retryable": True,
                                    "phase": "content"
                                }
                            }
            else:
                # 顺序模式：逐个生成
                yield {
                    "event": "progress",
                    "data": {
                        "status": "batch_start",
                        "message": f"开始顺序生成 {len(other_pages)} 页内容...",
                        "current": len(generated_images),
                        "total": total,
                        "phase": "content"
                    }
                }

                for page in other_pages:
                    # 发送生成进度
                    yield {
                        "event": "progress",
                        "data": {
                            "index": page["index"],
                            "status": "generating",
                            "current": len(generated_images) + 1,
                            "total": total,
                            "phase": "content"
                        }
                    }

                    # 生成单张图片
                    index, success, filename, error = self._generate_single_image(
                        page,
                        task_id,
                        cover_image_data,
                        0,
                        full_outline,
                        compressed_user_images,
                        user_topic
                    )

                    if success:
                        generated_images.append(filename)
                        self._task_states[task_id]["generated"][index] = filename

                        yield {
                            "event": "complete",
                            "data": {
                                "index": index,
                                "status": "done",
                                "image_url": f"/api/images/{task_id}/{filename}",
                                "phase": "content"
                            }
                        }
                    else:
                        failed_pages.append(page)
                        self._task_states[task_id]["failed"][index] = error

                        yield {
                            "event": "error",
                            "data": {
                                "index": index,
                                "status": "error",
                                "message": error,
                                "retryable": True,
                                "phase": "content"
                            }
                        }

        # ==================== 完成 ====================
        
        # 尝试更新历史记录中的图片信息
        try:
            history_service = get_history_service()
            history_service.scan_and_sync_task_images(task_id)
        except Exception as e:
            print(f"同步历史记录失败: {e}")

        yield {
            "event": "finish",
            "data": {
                "success": len(failed_pages) == 0,
                "task_id": task_id,
                "images": generated_images,
                "total": total,
                "completed": len(generated_images),
                "failed": len(failed_pages),
                "failed_indices": [p["index"] for p in failed_pages]
            }
        }

    def _generate_single_image(
        self,
        page: Dict,
        task_id: str,
        reference_image: bytes = None,
        retry_count: int = 0,
        full_outline: str = "",
        user_images: List[bytes] = None,
        user_topic: str = ""
    ) -> Tuple[int, bool, str, str]:
        """
        生成单张图片的内部方法
        """
        index = page["index"]
        prompt = page["image_prompt"]
        
        # 构建完整提示词
        # 如果有上下文，可以增强 prompt
        enhanced_prompt = prompt
        
        try:
            # 调用生成器
            # 注意：不同的生成器可能对 reference_image 的处理不同
            # 这里我们将 reference_image 传递给生成器，由生成器决定如何使用
            
            # 准备参考图片列表
            ref_images = []
            if reference_image:
                ref_images.append(reference_image)
            if user_images:
                ref_images.extend(user_images)
            
            image_data = self.generator.generate(
                prompt=enhanced_prompt,
                reference_image=ref_images[0] if ref_images else None, # 目前接口只支持单张参考图，优先使用封面
                negative_prompt="text, watermark, blurry, low quality, distorted, ugly"
            )
            
            if not image_data:
                raise Exception("生成器返回空数据")
            
            # 保存图片
            filename = f"{index}.png"
            filepath = os.path.join(self.history_root_dir, task_id, filename)
            
            with open(filepath, "wb") as f:
                f.write(image_data)
                
            # 生成缩略图
            try:
                thumb_data = compress_image(image_data, max_size=(256, 256), quality=70)
                if thumb_data:
                    thumb_filename = f"thumb_{index}.png"
                    thumb_filepath = os.path.join(self.history_root_dir, task_id, thumb_filename)
                    with open(thumb_filepath, "wb") as f:
                        f.write(thumb_data)
            except Exception as e:
                print(f"生成缩略图失败: {e}")
                
            return index, True, filename, ""
            
        except Exception as e:
            print(f"图片生成失败 (页 {index}): {e}")
            
            # 自动重试逻辑
            if retry_count < self.AUTO_RETRY_COUNT:
                print(f"正在重试第 {index} 页 (第 {retry_count + 1} 次)...")
                time.sleep(2) # 稍作等待
                return self._generate_single_image(
                    page, task_id, reference_image, retry_count + 1, full_outline, user_images, user_topic
                )
                
            return index, False, "", str(e)

    def retry_single_image(
        self,
        task_id: str,
        page: Dict,
        use_reference: bool = True
    ) -> Dict[str, Any]:
        """
        重试生成单张图片
        """
        # 设置当前任务目录
        self.current_task_dir = os.path.join(self.history_root_dir, task_id)
        os.makedirs(self.current_task_dir, exist_ok=True)

        # 获取参考图
        reference_image = None
        if use_reference and task_id in self._task_states:
            reference_image = self._task_states[task_id].get("cover_image")
        
        # 尝试从文件读取封面（如果内存中没有）
        if use_reference and not reference_image:
            try:
                cover_path = os.path.join(self.history_root_dir, task_id, "0.png")
                if os.path.exists(cover_path):
                    with open(cover_path, "rb") as f:
                        reference_image = f.read()
            except:
                pass

        # 生成图片
        index, success, filename, error = self._generate_single_image(
            page, task_id, reference_image
        )

        if success:
            # 更新任务状态
            if task_id in self._task_states:
                self._task_states[task_id]["generated"][index] = filename
                if index in self._task_states[task_id]["failed"]:
                    del self._task_states[task_id]["failed"][index]
            
            # 同步历史记录
            try:
                get_history_service().scan_and_sync_task_images(task_id)
            except:
                pass

            return {
                "success": True,
                "index": index,
                "image_url": f"/api/images/{task_id}/{filename}"
            }
        else:
            return {
                "success": False,
                "index": index,
                "error": error,
                "retryable": True
            }

    def retry_failed_images(
        self,
        task_id: str,
        pages: List[Dict]
    ) -> Generator[Dict[str, Any], None, None]:
        """
        批量重试失败的图片
        """
        # 获取参考图
        reference_image = None
        if task_id in self._task_states:
            reference_image = self._task_states[task_id].get("cover_image")
            
        if not reference_image:
             try:
                cover_path = os.path.join(self.history_root_dir, task_id, "0.png")
                if os.path.exists(cover_path):
                    with open(cover_path, "rb") as f:
                        reference_image = f.read()
             except:
                pass

        total = len(pages)
        success_count = 0
        failed_count = 0

        yield {
            "event": "retry_start",
            "data": {
                "total": total,
                "message": f"开始重试 {total} 张失败的图片"
            }
        }

        # 并发重试
        full_outline = ""
        if task_id in self._task_states:
            full_outline = self._task_states[task_id].get("full_outline", "")

        with ThreadPoolExecutor(max_workers=self.MAX_CONCURRENT) as executor:
            future_to_page = {
                executor.submit(
                    self._generate_single_image,
                    page,
                    task_id,
                    reference_image,
                    0,  # retry_count
                    full_outline  # 传入完整大纲
                ): page
                for page in pages
            }

            for future in as_completed(future_to_page):
                page = future_to_page[future]
                try:
                    index, success, filename, error = future.result()

                    if success:
                        success_count += 1
                        if task_id in self._task_states:
                            self._task_states[task_id]["generated"][index] = filename
                            if index in self._task_states[task_id]["failed"]:
                                del self._task_states[task_id]["failed"][index]

                        yield {
                            "event": "complete",
                            "data": {
                                "index": index,
                                "status": "done",
                                "image_url": f"/api/images/{task_id}/{filename}"
                            }
                        }
                    else:
                        failed_count += 1
                        yield {
                            "event": "error",
                            "data": {
                                "index": index,
                                "status": "error",
                                "message": error,
                                "retryable": True
                            }
                        }

                except Exception as e:
                    failed_count += 1
                    yield {
                        "event": "error",
                        "data": {
                            "index": page["index"],
                            "status": "error",
                            "message": str(e),
                            "retryable": True
                        }
                    }
        
        # 同步历史记录
        try:
            get_history_service().scan_and_sync_task_images(task_id)
        except:
            pass

        yield {
            "event": "retry_finish",
            "data": {
                "success": failed_count == 0,
                "total": total,
                "completed": success_count,
                "failed": failed_count
            }
        }

    def regenerate_image(
        self,
        task_id: str,
        page: Dict,
        use_reference: bool = True
    ) -> Dict[str, Any]:
        """
        重新生成图片（用户手动触发，即使成功的也可以重新生成）
        """
        return self.retry_single_image(task_id, page, use_reference)

    def get_image_path(self, task_id: str, filename: str) -> str:
        """
        获取图片完整路径
        """
        task_dir = os.path.join(self.history_root_dir, task_id)
        return os.path.join(task_dir, filename)

    def get_task_state(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        return self._task_states.get(task_id)

    def cleanup_task(self, task_id: str):
        """清理任务状态（释放内存）"""
        if task_id in self._task_states:
            del self._task_states[task_id]


# 全局服务实例
_service_instance = None

def get_image_service() -> ImageService:
    """获取全局图片生成服务实例"""
    global _service_instance
    if _service_instance is None:
        _service_instance = ImageService()
    return _service_instance

def reset_image_service():
    """重置全局服务实例（配置更新后调用）"""
    global _service_instance
    _service_instance = None
