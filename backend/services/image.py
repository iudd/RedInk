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


class ImageService:
    """图片生成服务类"""

    # 并发配置
    MAX_CONCURRENT = 2  # 默认最大并发数（降低以避免限流）
    AUTO_RETRY_COUNT = 3  # 自动重试次数

    def __init__(self, provider_name: str = None):
        # ... (保持不变)

    # ... (中间代码保持不变)

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

    def retry_single_image(
        self,
        task_id: str,
        page: Dict,
        use_reference: bool = True
    ) -> Dict[str, Any]:
        """
        重试生成单张图片

        Args:
            task_id: 任务ID
            page: 页面数据
            use_reference: 是否使用封面作为参考

        Returns:
            生成结果
        """
        # 设置当前任务目录
        self.current_task_dir = os.path.join(self.history_root_dir, task_id)
        os.makedirs(self.current_task_dir, exist_ok=True)

        # 获取参考图
        reference_image = None
        if use_reference and task_id in self._task_states:
            reference_image = self._task_states[task_id].get("cover_image")

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

        Args:
            task_id: 任务ID
            pages: 需要重试的页面列表

        Yields:
            进度事件
        """
        # 获取参考图
        reference_image = None
        if task_id in self._task_states:
            reference_image = self._task_states[task_id].get("cover_image")

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
        # 从任务状态中获取完整大纲
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

        Args:
            task_id: 任务ID
            page: 页面数据
            use_reference: 是否使用封面作为参考

        Returns:
            生成结果
        """
        return self.retry_single_image(task_id, page, use_reference)

    def get_image_path(self, task_id: str, filename: str) -> str:
        """
        获取图片完整路径

        Args:
            task_id: 任务ID
            filename: 文件名

        Returns:
            完整路径
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
