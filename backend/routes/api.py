"""API 路由"""
import json
import os
import zipfile
import io
from flask import Blueprint, request, jsonify, Response, send_file
from backend.services.outline import get_outline_service
from backend.services.image import get_image_service
from backend.services.history import get_history_service
from backend.services.config import get_config_service

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/outline', methods=['POST'])
def generate_outline():
    """生成大纲（支持图片上传）"""
    try:
        # 检查是否是 multipart/form-data（带图片）
        if request.content_type and 'multipart/form-data' in request.content_type:
            topic = request.form.get('topic')
            # 获取上传的图片
            images = []
            if 'images' in request.files:
                files = request.files.getlist('images')
                for file in files:
                    if file and file.filename:
                        image_data = file.read()
                        images.append(image_data)
        else:
            # JSON 请求（无图片或 base64 图片）
            data = request.get_json()
            topic = data.get('topic')
            # 支持 base64 格式的图片
            images_base64 = data.get('images', [])
            images = []
            if images_base64:
                import base64
                for img_b64 in images_base64:
                    # 移除可能的 data URL 前缀
                    if ',' in img_b64:
                        img_b64 = img_b64.split(',')[1]
                    images.append(base64.b64decode(img_b64))

        if not topic:
            return jsonify({
                "success": False,
                "error": "参数错误：topic 不能为空。\n请提供要生成图文的主题内容。"
            }), 400

        # 调用大纲生成服务
        outline_service = get_outline_service()
        result = outline_service.generate_outline(topic, images if images else None)

        if result["success"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"大纲生成异常。\n错误详情: {error_msg}\n建议：检查后端日志获取更多信息"
        }), 500


@api_bp.route('/generate', methods=['POST'])
def generate_images():
    """生成图片（SSE 流式返回，支持用户上传参考图片）"""
    try:
        # JSON 请求
        data = request.get_json()
        pages = data.get('pages')
        task_id = data.get('task_id')
        full_outline = data.get('full_outline', '')
        user_topic = data.get('user_topic', '')  # 用户原始输入
        # 支持 base64 格式的用户参考图片
        user_images_base64 = data.get('user_images', [])
        user_images = []
        if user_images_base64:
            import base64
            for img_b64 in user_images_base64:
                if ',' in img_b64:
                    img_b64 = img_b64.split(',')[1]
                user_images.append(base64.b64decode(img_b64))

        if not pages:
            return jsonify({
                "success": False,
                "error": "参数错误：pages 不能为空。\n请提供要生成的页面列表数据。"
            }), 400

        # 获取图片生成服务
        image_service = get_image_service()

        def generate():
            """SSE 生成器"""
            for event in image_service.generate_images(
                pages, task_id, full_outline,
                user_images=user_images if user_images else None,
                user_topic=user_topic
            ):
                event_type = event["event"]
                event_data = event["data"]

                # 格式化为 SSE 格式
                yield f"event: {event_type}\n"
                yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"

        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
            }
        )

    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"图片生成异常。\n错误详情: {error_msg}\n建议：检查图片生成服务配置和后端日志"
        }), 500


@api_bp.route('/images/<task_id>/<filename>', methods=['GET'])
def get_image(task_id, filename):
    """获取图片（支持缩略图）"""
    try:
        # 检查是否请求缩略图
        thumbnail = request.args.get('thumbnail', 'true').lower() == 'true'

        # 直接构建路径，不需要初始化 ImageService
        history_root = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "history"
        )

        if thumbnail:
            # 尝试返回缩略图
            thumb_filename = f"thumb_{filename}"
            thumb_filepath = os.path.join(history_root, task_id, thumb_filename)

            # 如果缩略图存在，返回缩略图
            if os.path.exists(thumb_filepath):
                return send_file(thumb_filepath, mimetype='image/png')

        # 返回原图
        filepath = os.path.join(history_root, task_id, filename)

        if not os.path.exists(filepath):
            return jsonify({
                "success": False,
                "error": f"图片不存在：{task_id}/{filename}"
            }), 404

        return send_file(filepath, mimetype='image/png')

    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"获取图片失败: {error_msg}"
        }), 500


@api_bp.route('/retry', methods=['POST'])
def retry_single_image():
    """重试生成单张图片"""
    try:
        data = request.get_json()
        task_id = data.get('task_id')
        page = data.get('page')
        use_reference = data.get('use_reference', True)

        if not task_id or not page:
            return jsonify({
                "success": False,
                "error": "参数错误：task_id 和 page 不能为空。\n请提供任务ID和页面信息。"
            }), 400

        image_service = get_image_service()
        result = image_service.retry_single_image(task_id, page, use_reference)

        return jsonify(result), 200 if result["success"] else 500

    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"重试图片生成失败。\n错误详情: {error_msg}"
        }), 500


@api_bp.route('/retry-failed', methods=['POST'])
def retry_failed_images():
    """批量重试失败的图片（SSE 流式返回）"""
    try:
        data = request.get_json()
        task_id = data.get('task_id')
        pages = data.get('pages')

        if not task_id or not pages:
            return jsonify({
                "success": False,
                "error": "参数错误：task_id 和 pages 不能为空。\n请提供任务ID和要重试的页面列表。"
            }), 400

        image_service = get_image_service()

        def generate():
            """SSE 生成器"""
            for event in image_service.retry_failed_images(task_id, pages):
                event_type = event["event"]
                event_data = event["data"]

                yield f"event: {event_type}\n"
                yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"

        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
            }
        )

    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"批量重试失败。\n错误详情: {error_msg}"
        }), 500


@api_bp.route('/regenerate', methods=['POST'])
def regenerate_image():
    """重新生成图片（即使成功的也可以重新生成）"""
    try:
        data = request.get_json()
        task_id = data.get('task_id')
        page = data.get('page')
        use_reference = data.get('use_reference', True)

        if not task_id or not page:
            return jsonify({
                "success": False,
                "error": "参数错误：task_id 和 page 不能为空。\n请提供任务ID和页面信息。"
            }), 400

        image_service = get_image_service()
        result = image_service.regenerate_image(task_id, page, use_reference)

        return jsonify(result), 200 if result["success"] else 500

    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"重新生成图片失败。\n错误详情: {error_msg}"
        }), 500


@api_bp.route('/task/<task_id>', methods=['GET'])
def get_task_state(task_id):
    """获取任务状态"""
    try:
        image_service = get_image_service()
        state = image_service.get_task_state(task_id)

        if state is None:
            return jsonify({
                "success": False,
                "error": f"任务不存在：{task_id}\n可能原因：\n1. 任务ID错误\n2. 任务已过期或被清理\n3. 服务重启导致状态丢失"
            }), 404

        # 不返回封面图片数据（太大）
        safe_state = {
            "generated": state.get("generated", {}),
            "failed": state.get("failed", {}),
            "has_cover": state.get("cover_image") is not None
        }

        return jsonify({
            "success": True,
            "state": safe_state
        }), 200

    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"获取任务状态失败。\n错误详情: {error_msg}"
        }), 500


@api_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        "success": True,
        "message": "服务正常运行"
    }), 200


@api_bp.route('/health/storage', methods=['GET'])
def storage_check():
    """检查存储状态"""
    try:
        config_service = get_config_service()
        history_service = get_history_service()
        
        return jsonify({
            "success": True,
            "config_storage": "supabase" if config_service.supabase else "local",
            "history_storage": "supabase" if history_service.supabase else "local"
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ==================== 历史记录相关 API ====================

@api_bp.route('/history', methods=['POST'])
def create_history():
    """创建历史记录"""
    try:
        data = request.get_json()
        topic = data.get('topic')
        outline = data.get('outline')
        task_id = data.get('task_id')

        if not topic or not outline:
            return jsonify({
                "success": False,
                "error": "参数错误：topic 和 outline 不能为空。\n请提供主题和大纲内容。"
            }), 400

        history_service = get_history_service()
        record_id = history_service.create_record(topic, outline, task_id)

        return jsonify({
            "success": True,
            "record_id": record_id
        }), 200

    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"创建历史记录失败。\n错误详情: {error_msg}"
        }), 500


@api_bp.route('/history', methods=['GET'])
def list_history():
    """获取历史记录列表"""
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        status = request.args.get('status')

        history_service = get_history_service()
        result = history_service.list_records(page, page_size, status)

        return jsonify({
            "success": True,
            **result
        }), 200

    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"获取历史记录列表失败。\n错误详情: {error_msg}"
        }), 500


@api_bp.route('/history/<record_id>', methods=['GET'])
def get_history(record_id):
    """获取历史记录详情"""
    try:
        history_service = get_history_service()
        record = history_service.get_record(record_id)

        if not record:
            return jsonify({
                "success": False,
                "error": f"历史记录不存在：{record_id}\n可能原因：记录已被删除或ID错误"
            }), 404

        return jsonify({
            "success": True,
            "record": record
        }), 200

    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"获取历史记录详情失败。\n错误详情: {error_msg}"
        }), 500


@api_bp.route('/history/<record_id>', methods=['PUT'])
def update_history(record_id):
    """更新历史记录"""
    try:
        data = request.get_json()
        outline = data.get('outline')
        images = data.get('images')
        status = data.get('status')
        thumbnail = data.get('thumbnail')

        history_service = get_history_service()
        success = history_service.update_record(
            record_id,
            outline=outline,
            images=images,
            status=status,
            thumbnail=thumbnail
        )

        if not success:
            return jsonify({
                "success": False,
                "error": f"更新历史记录失败：{record_id}\n可能原因：记录不存在或数据格式错误"
            }), 404

        return jsonify({
            "success": True
        }), 200

    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"更新历史记录失败。\n错误详情: {error_msg}"
        }), 500


@api_bp.route('/history/<record_id>', methods=['DELETE'])
def delete_history(record_id):
    """删除历史记录"""
    try:
        history_service = get_history_service()
        success = history_service.delete_record(record_id)

        if not success:
            return jsonify({
                "success": False,
                "error": f"删除历史记录失败：{record_id}\n可能原因：记录不存在或ID错误"
            }), 404

        return jsonify({
            "success": True
        }), 200

    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"删除历史记录失败。\n错误详情: {error_msg}"
        }), 500


@api_bp.route('/history/search', methods=['GET'])
def search_history():
    """搜索历史记录"""
    try:
        keyword = request.args.get('keyword', '')

        if not keyword:
            return jsonify({
                "success": False,
                "error": "参数错误：keyword 不能为空。\n请提供搜索关键词。"
            }), 400

        history_service = get_history_service()
        results = history_service.search_records(keyword)

        return jsonify({
            "success": True,
            "records": results
        }), 200

    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"搜索历史记录失败。\n错误详情: {error_msg}"
        }), 500


@api_bp.route('/history/stats', methods=['GET'])
def get_history_stats():
    """获取历史记录统计"""
    try:
        history_service = get_history_service()
        stats = history_service.get_statistics()

        return jsonify({
            "success": True,
            **stats
        }), 200

    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"获取历史记录统计失败。\n错误详情: {error_msg}"
        }), 500


@api_bp.route('/history/scan/<task_id>', methods=['GET'])
def scan_task(task_id):
    """扫描单个任务并同步图片列表"""
    try:
        history_service = get_history_service()
        result = history_service.scan_and_sync_task_images(task_id)

        if not result.get("success"):
            return jsonify(result), 404

        return jsonify(result), 200

    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"扫描任务失败。\n错误详情: {error_msg}"
        }), 500


@api_bp.route('/history/scan-all', methods=['POST'])
def scan_all_tasks():
    """扫描所有任务并同步图片列表"""
    try:
        history_service = get_history_service()
        result = history_service.scan_all_tasks()

        if not result.get("success"):
            return jsonify(result), 500

        return jsonify(result), 200

    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"扫描所有任务失败。\n错误详情: {error_msg}"
        }), 500


@api_bp.route('/history/<record_id>/download', methods=['GET'])
def download_history_zip(record_id):
    """下载历史记录的所有图片为 ZIP 文件"""
    try:
        history_service = get_history_service()
        record = history_service.get_record(record_id)

        if not record:
            return jsonify({
                "success": False,
                "error": f"历史记录不存在：{record_id}"
            }), 404

        task_id = record.get('images', {}).get('task_id')
        if not task_id:
            return jsonify({
                "success": False,
                "error": "该记录没有关联的任务图片"
            }), 404

        # 获取任务目录
        task_dir = os.path.join(history_service.history_dir, task_id)
        if not os.path.exists(task_dir):
            return jsonify({
                "success": False,
                "error": f"任务目录不存在：{task_id}"
            }), 404

        # 创建内存中的 ZIP 文件
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 遍历任务目录中的所有图片（排除缩略图）
            for filename in os.listdir(task_dir):
                # 跳过缩略图文件
                if filename.startswith('thumb_'):
                    continue
                if filename.endswith(('.png', '.jpg', '.jpeg')):
                    file_path = os.path.join(task_dir, filename)
                    # 添加文件到 ZIP，使用 page_N.png 命名
                    try:
                        index = int(filename.split('.')[0])
                        archive_name = f"page_{index + 1}.png"
                    except:
                        archive_name = filename

                    zf.write(file_path, archive_name)

        # 将指针移到开始位置
        memory_file.seek(0)

        # 生成下载文件名（使用记录标题）
        title = record.get('title', 'images')
        # 清理文件名中的非法字符
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_title:
            safe_title = 'images'

        filename = f"{safe_title}.zip"

        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        error_msg = str(e)
        return jsonify({
            "success": False,
            "error": f"下载失败。\n错误详情: {error_msg}"
        }), 500


# ==================== 配置管理 API ====================

def _mask_api_key(key: str) -> str:
    """遮盖 API Key，只显示前4位和后4位"""
    if not key:
        return ''
    if len(key) <= 8:
        return '*' * len(key)
    return key[:4] + '*' * (len(key) - 8) + key[-4:]


def _prepare_providers_for_response(providers: dict) -> dict:
    """准备返回给前端的 providers，返回脱敏的 api_key"""
    result = {}
    for name, config in providers.items():
        provider_copy = config.copy()
        # 返回脱敏的 api_key
        if 'api_key' in provider_copy and provider_copy['api_key']:
            provider_copy['api_key_masked'] = _mask_api_key(provider_copy['api_key'])
            provider_copy['api_key'] = ''  # 不返回实际值，前端用空字符串表示"不修改"
        else:
            provider_copy['api_key_masked'] = ''
            provider_copy['api_key'] = ''
        result[name] = provider_copy
    return result





@api_bp.route('/config', methods=['GET'])
def get_config():
    """获取当前配置"""
    try:
        config_service = get_config_service()
        full_config = config_service.get_full_config()

        # 脱敏处理
        text_config = full_config.get('text_generation', {})
        image_config = full_config.get('image_generation', {})

        return jsonify({
            "success": True,
            "config": {
                "text_generation": {
                    "active_provider": text_config.get('active_provider', ''),
                    "providers": _prepare_providers_for_response(text_config.get('providers', {}))
                },
                "image_generation": {
                    "active_provider": image_config.get('active_provider', ''),
                    "providers": _prepare_providers_for_response(image_config.get('providers', {}))
                }
            }
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"获取配置失败: {str(e)}"
        }), 500


@api_bp.route('/config', methods=['POST'])
def update_config():
    """更新配置"""
    try:
        data = request.get_json()
        config_service = get_config_service()
        
        success = config_service.update_full_config(data)
        
        if success:
            return jsonify({"success": True}), 200
        else:
            return jsonify({
                "success": False, 
                "error": "保存配置失败"
            }), 500

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"更新配置异常: {str(e)}"
        }), 500

        # 清除 ImageService 缓存，确保使用新配置
        from backend.services.image import reset_image_service
        reset_image_service()

        return jsonify({
            "success": True,
            "message": "配置已保存"
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"更新配置失败: {str(e)}"
        }), 500


# ==================== 自定义服务商管理 API ====================

@api_bp.route('/custom-providers', methods=['GET'])
def get_custom_providers():
    """获取所有自定义服务商配置"""
    try:
        config_service = get_config_service()
        providers = config_service.get_all_providers()
        
        return jsonify({
            "success": True,
            "data": providers
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"获取自定义配置失败: {str(e)}"
        }), 500


@api_bp.route('/custom-providers', methods=['POST'])
def add_custom_provider():
    """添加自定义服务商"""
    try:
        data = request.get_json()
        
        # 验证必填字段
        required_fields = ['provider_name', 'provider_type', 'api_key', 'base_url', 'model', 'service_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    "success": False,
                    "error": f"参数错误: {field} 不能为空"
                }), 400
        
        config_service = get_config_service()
        success = config_service.add_custom_provider(
            provider_name=data['provider_name'],
            provider_type=data['provider_type'],
            api_key=data['api_key'],
            base_url=data['base_url'],
            model=data['model'],
            service_type=data['service_type']
        )
        
        if success:
            return jsonify({
                "success": True,
                "message": "自定义服务商添加成功"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "添加自定义服务商失败"
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"添加自定义服务商失败: {str(e)}"
        }), 500


@api_bp.route('/custom-providers/<provider_name>', methods=['DELETE'])
def delete_custom_provider(provider_name):
    """删除自定义服务商"""
    try:
        config_service = get_config_service()
        success = config_service.delete_custom_provider(provider_name)
        
        if success:
            return jsonify({
                "success": True,
                "message": "自定义服务商删除成功"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": f"删除自定义服务商失败: {provider_name}"
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"删除自定义服务商失败: {str(e)}"
        }), 500


@api_bp.route('/custom-providers/<provider_name>/set-active', methods=['POST'])
def set_active_provider(provider_name):
    """设置激活的服务商"""
    try:
        data = request.get_json()
        service_type = data.get('service_type')  # 'text' 或 'image'
        
        if service_type not in ['text', 'image']:
            return jsonify({
                "success": False,
                "error": "参数错误: service_type 必须是 'text' 或 'image'"
            }), 400
        
        config_service = get_config_service()
        success = config_service.set_active_provider(provider_name, service_type)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"已设置 {provider_name} 为 {service_type} 服务商"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": f"设置激活服务商失败: {provider_name}"
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"设置激活服务商失败: {str(e)}"
        }), 500


@api_bp.route('/custom-providers/test', methods=['POST'])
def test_provider_connection():
    """测试服务商连接"""
    try:
        data = request.get_json()
        
        # 验证必填字段
        required_fields = ['api_key', 'base_url']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    "success": False,
                    "error": f"参数错误: {field} 不能为空"
                }), 400
        
        config_service = get_config_service()
        result = config_service.test_provider_connection(data)
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"连接测试失败: {str(e)}"
        }), 500
