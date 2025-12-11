#!/usr/bin/env python3
"""
Hugging Face Space 统一服务器
整合后端API和前端静态文件服务
"""

from flask import Flask, request, Response, send_from_directory, send_file
import os
import sys

# 添加后端路径到Python路径
sys.path.append('/app')

# 导入后端应用
from backend.app import create_app
backend_app = create_app()  # 这会创建并配置好所有路由

# 前端构建文件目录
FRONTEND_DIST = "/app/frontend/dist"
#FRONTEND_DIST = "e:/code/RedInk/frontend/dist"

# 不需要创建新的app，直接使用backend_app
app = backend_app  # 直接使用已经配置好的后端应用

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """服务前端静态文件"""
    # 如果是API请求，但找不到对应的路由，返回404
    if path.startswith('api/'):
        return {"error": "API endpoint not found"}, 404
    
    # 检查是否是静态文件
    if path and os.path.exists(os.path.join(FRONTEND_DIST, path)):
        return send_from_directory(FRONTEND_DIST, path)
    else:
        # 对于SPA路由，返回index.html
        return send_from_directory(FRONTEND_DIST, 'index.html')

@app.route('/api')
def api_info():
    """API信息根路径"""
    return {
        "endpoints": {
            "generate": "POST /api/generate",
            "health": "/api/health",
            "images": "GET /api/images/<filename>",
            "outline": "POST /api/outline"
        },
        "message": "红墨 AI 图文生成器 API",
        "version": "0.1.0"
    }

if __name__ == '__main__':
    # 启动统一服务器（HF Space主端口）
    print("🌐 启动统一服务器...")
    print("📱 前端页面: http://localhost:7860/")
    print("🔌 API接口: http://localhost:7860/api/*")
    app.run(host='0.0.0.0', port=7860)
