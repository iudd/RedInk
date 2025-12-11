"""OpenAI 兼容接口图片生成器"""
import time
import random
import base64
import socket
import subprocess
import re
from functools import wraps
from typing import Dict, Any
from urllib.parse import urlparse
from contextlib import contextmanager
import requests
from .base import ImageGeneratorBase


def retry_on_error(max_retries=5, base_delay=3):
    """错误自动重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_str = str(e)
                    # 检查是否是速率限制错误
                    if "429" in error_str or "rate" in error_str.lower():
                        if attempt < max_retries - 1:
                            wait_time = (base_delay ** attempt) + random.uniform(0, 1)
                            print(f"[重试] 遇到速率限制，{wait_time:.1f}秒后重试 (尝试 {attempt + 2}/{max_retries})")
                            time.sleep(wait_time)
                            continue
                    # 其他错误或重试耗尽
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        print(f"[重试] 请求失败: {error_str[:100]}，{wait_time}秒后重试")
                        time.sleep(wait_time)
                        continue
                    raise
            raise Exception(
                f"图片生成失败：重试 {max_retries} 次后仍失败。\n"
                "可能原因：\n"
                "1. API持续限流或配额不足\n"
                "2. 网络连接持续不稳定\n"
                "3. API服务暂时不可用\n"
                "建议：稍后再试，或检查API配额和网络状态"
            )
        return wrapper
    return decorator


def resolve_hostname_with_fallback(hostname: str) -> str:
    """
    解析主机名,如果失败则使用 nslookup 回退
    
    Args:
        hostname: 要解析的主机名
        
    Returns:
        解析到的 IP 地址,如果失败返回原始 hostname
    """
    try:
        return socket.gethostbyname(hostname)
    except:
        try:
            # Fallback to nslookup with Google DNS
            cmd = ['nslookup', hostname, '8.8.8.8']
            result = subprocess.check_output(cmd, timeout=5, stderr=subprocess.STDOUT).decode()
            ips = re.findall(r'Address:\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)', result)
            if ips:
                resolved_ip = ips[-1]
                print(f"DNS fallback: {hostname} -> {resolved_ip}")
                return resolved_ip
        except Exception as e:
            print(f"DNS resolution fallback failed for {hostname}: {e}")
    return hostname


@contextmanager
def force_ip_resolution(hostname: str, ip: str):
    """
    强制使用指定 IP 解析主机名
    
    Args:
        hostname: 主机名
        ip: 要使用的 IP 地址
    """
    if not ip or ip == hostname:
        yield
        return
    
    original_getaddrinfo = socket.getaddrinfo
    def patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        if host == hostname:
            return original_getaddrinfo(ip, port, socket.AF_INET, type, proto, flags)
        return original_getaddrinfo(host, port, family, type, proto, flags)
    
    socket.getaddrinfo = patched_getaddrinfo
    try:
        yield
    finally:
        socket.getaddrinfo = original_getaddrinfo



class OpenAICompatibleGenerator(ImageGeneratorBase):
    """OpenAI 兼容接口图片生成器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        if not self.api_key:
            raise ValueError(
                "OpenAI 兼容 API Key 未配置。\n"
                "解决方案：在系统设置页面编辑该服务商，填写 API Key"
            )

        if not self.base_url:
            raise ValueError(
                "OpenAI 兼容 API Base URL 未配置。\n"
                "解决方案：在系统设置页面编辑该服务商，填写 Base URL"
            )

        # 默认模型
        self.default_model = config.get('model', 'dall-e-3')

        # API 端点类型: 'images' 或 'chat'
        # 智能检测:某些 API (如 whisk) 使用 chat 端点生成图片
        if 'endpoint_type' in config:
            self.endpoint_type = config['endpoint_type']
        elif 'whisk' in self.base_url.lower():
            self.endpoint_type = 'chat'
            print(f"OpenAI Generator: 检测到 whisk API,自动使用 chat 端点")
        else:
            self.endpoint_type = 'images'
        
        # 预解析主机名以避免 DNS 问题
        try:
            parsed = urlparse(self.base_url)
            self.hostname = parsed.hostname
            self.resolved_ip = resolve_hostname_with_fallback(self.hostname) if self.hostname else None
            print(f"OpenAI Generator: Hostname {self.hostname} resolved to {self.resolved_ip}")
        except Exception as e:
            print(f"OpenAI Generator: Failed to parse/resolve hostname: {e}")
            self.hostname = None
            self.resolved_ip = None

    def validate_config(self) -> bool:
        """验证配置"""
        return bool(self.api_key and self.base_url)

    @retry_on_error(max_retries=5, base_delay=3)
    def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        model: str = None,
        quality: str = "standard",
        **kwargs
    ) -> bytes:
        """
        生成图片

        Args:
            prompt: 提示词
            size: 图片尺寸 (如 "1024x1024", "2048x2048", "4096x4096")
            model: 模型名称
            quality: 质量 ("standard" 或 "hd")
            **kwargs: 其他参数

        Returns:
            图片二进制数据
        """
        if model is None:
            model = self.default_model

        if self.endpoint_type == 'images':
            return self._generate_via_images_api(prompt, size, model, quality)
        elif self.endpoint_type == 'chat':
            return self._generate_via_chat_api(prompt, size, model)
        else:
            raise ValueError(
                f"不支持的端点类型: {self.endpoint_type}\n"
                "支持的类型: images, chat\n"
                "解决方案：\n"
                "在 image_providers.yaml 中设置正确的 endpoint_type\n"
                "- 'images': 使用 /v1/images/generations 端点 (标准)\n"
                "- 'chat': 使用 /v1/chat/completions 端点 (特殊)"
            )

    def _generate_via_images_api(
        self,
        prompt: str,
        size: str,
        model: str,
        quality: str
    ) -> bytes:
        """通过 /v1/images/generations 端点生成"""
        # 智能处理 base_url,避免重复 /v1
        base = self.base_url.rstrip('/')
        if base.endswith('/v1'):
            url = f"{base}/images/generations"
        else:
            url = f"{base}/v1/images/generations"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": size,
            "response_format": "b64_json"  # 使用base64格式更可靠
        }

        # 如果模型支持quality参数
        if quality and model.startswith('dall-e'):
            payload["quality"] = quality

        # 使用强制 IP 解析避免 DNS 问题
        with force_ip_resolution(self.hostname, self.resolved_ip):
            response = requests.post(url, headers=headers, json=payload, timeout=600)

        if response.status_code != 200:
            error_detail = response.text[:500]
            raise Exception(
                f"OpenAI Images API 请求失败 (状态码: {response.status_code})\n"
                f"错误详情: {error_detail}\n"
                f"请求地址: {url}\n"
                f"模型: {model}\n"
                "可能原因：\n"
                "1. API密钥无效或已过期\n"
                "2. 模型名称不正确或无权访问\n"
                "3. 请求参数不符合要求\n"
                "4. API配额已用尽\n"
                "5. Base URL配置错误\n"
                "建议：检查API密钥、base_url和模型名称配置"
            )

        try:
            result = response.json()
        except Exception as e:
            error_detail = response.text[:1000]
            raise Exception(
                f"OpenAI Images API 响应解析失败 (JSONDecodeError)\n"
                f"状态码: {response.status_code}\n"
                f"原始响应内容: {error_detail}\n"
                f"请求地址: {url}\n"
                "可能原因：API 返回了非 JSON 格式数据（可能是排队信息或 HTML 错误）"
            )

        if "data" not in result or len(result["data"]) == 0:
            raise ValueError(
                "OpenAI API 未返回图片数据。\n"
                f"响应内容: {str(result)[:500]}\n"
                "可能原因：\n"
                "1. 提示词被安全过滤拦截\n"
                "2. 模型不支持图片生成\n"
                "3. 请求格式不正确\n"
                "建议：修改提示词或检查模型配置"
            )

        image_data = result["data"][0]

        # 处理base64格式
        if "b64_json" in image_data:
            return base64.b64decode(image_data["b64_json"])

        # 处理URL格式
        elif "url" in image_data:
            with force_ip_resolution(self.hostname, self.resolved_ip):
                img_response = requests.get(image_data["url"], timeout=60)
            if img_response.status_code == 200:
                return img_response.content
            else:
                raise Exception(f"下载图片失败: {img_response.status_code}")

        else:
            raise ValueError(
                "无法从API响应中提取图片数据。\n"
                f"响应数据: {str(image_data)[:500]}\n"
                "可能原因：\n"
                "1. 响应格式不包含 b64_json 或 url 字段\n"
                "2. response_format 参数未生效\n"
                "建议：检查API文档确认图片返回格式"
            )

    def _generate_via_chat_api(
        self,
        prompt: str,
        size: str,
        model: str
    ) -> bytes:
        """通过 /v1/chat/completions 端点生成（某些服务商使用此方式）"""
        # 智能处理 base_url,避免重复 /v1
        base = self.base_url.rstrip('/')
        if base.endswith('/v1'):
            url = f"{base}/chat/completions"
        else:
            url = f"{base}/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 4096,
            "temperature": 1.0,
            # 尝试添加图片相关参数
            "response_format": {"type": "image"},
            "size": size
        }

        # 使用强制 IP 解析避免 DNS 问题
        with force_ip_resolution(self.hostname, self.resolved_ip):
            response = requests.post(url, headers=headers, json=payload, timeout=180)

        if response.status_code != 200:
            error_detail = response.text[:500]
            raise Exception(
                f"OpenAI Chat API 请求失败 (状态码: {response.status_code})\n"
                f"错误详情: {error_detail}\n"
                f"请求地址: {url}\n"
                f"模型: {model}\n"
                "可能原因：\n"
                "1. API密钥无效或已过期\n"
                "2. 该服务商不支持通过 chat 端点生成图片\n"
                "3. 请求参数格式错误\n"
                "4. API配额已用尽\n"
                "建议：尝试将 endpoint_type 改为 'images' 或检查API密钥"
            )


        result = response.json()
        
        print(f"Chat API 响应: {str(result)[:500]}")

        # 尝试多种格式提取图片数据
        # 格式1: 标准 OpenAI chat 格式
        if "choices" in result and len(result["choices"]) > 0:
            choice = result["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                content = choice["message"]["content"]
                
                # data URI 格式
                if isinstance(content, str) and content.startswith("data:image"):
                    base64_data = content.split(",")[1]
                    return base64.b64decode(base64_data)
                
                # 纯 base64
                if isinstance(content, str) and len(content) > 100:
                    try:
                        return base64.b64decode(content)
                    except:
                        pass
                
                # URL 格式
                if isinstance(content, str) and content.startswith("http"):
                    with force_ip_resolution(self.hostname, self.resolved_ip):
                        img_response = requests.get(content, timeout=60)
                    if img_response.status_code == 200:
                        return img_response.content
        
        # 格式2: 类似 images API 的格式
        if "data" in result and len(result["data"]) > 0:
            image_data = result["data"][0]
            
            if "b64_json" in image_data:
                return base64.b64decode(image_data["b64_json"])
            
            if "url" in image_data:
                with force_ip_resolution(self.hostname, self.resolved_ip):
                    img_response = requests.get(image_data["url"], timeout=60)
                if img_response.status_code == 200:
                    return img_response.content

        raise ValueError(
            "无法从 Chat API 响应中提取图片数据。\n"
            f"响应内容: {str(result)[:500]}\n"
            "可能原因：\n"
            "1. 该服务商不支持通过 chat 端点生成图片\n"
            "2. 响应格式与预期不符\n"
            "建议：\n"
            "1. 尝试将 endpoint_type 改为 'images'\n"
            "2. 或联系API服务提供商确认正确的调用方式"
        )

    def get_supported_sizes(self) -> list:
        """获取支持的图片尺寸"""
        # 默认OpenAI支持的尺寸
        return self.config.get('supported_sizes', [
            "1024x1024",
            "1792x1024",
            "1024x1792",
            "2048x2048",
            "4096x4096"
        ])
