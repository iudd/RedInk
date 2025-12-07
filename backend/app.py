from flask import Flask
from flask_cors import CORS
from backend.config import Config
from backend.routes.api import api_bp


def create_app():
    # 配置静态文件目录为前端构建输出目录
    import os
    dist_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'dist')
    
    # 如果 dist 目录存在，则作为静态文件目录
    if os.path.exists(dist_folder):
        app = Flask(__name__, static_folder=dist_folder, static_url_path='')
    else:
        app = Flask(__name__)
        
    app.config.from_object(Config)

    CORS(app, resources={
        r"/api/*": {
            "origins": Config.CORS_ORIGINS,
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type"],
        }
    })

    app.register_blueprint(api_bp)

    @app.route('/')
    def index():
        # 如果是生产环境且 dist 存在，返回 index.html
        if os.path.exists(dist_folder):
            return app.send_static_file('index.html')
            
        # 否则返回 API 信息（开发模式）
        return {
            "message": "红墨 AI图文生成器 API",
            "version": "0.1.0",
            "endpoints": {
                "health": "/api/health",
                "outline": "POST /api/outline",
                "generate": "POST /api/generate",
                "images": "GET /api/images/<filename>"
            }
        }
        
    # 处理前端路由（SPA 支持）
    @app.route('/<path:path>')
    def serve_static(path):
        if os.path.exists(dist_folder) and os.path.exists(os.path.join(dist_folder, path)):
            return app.send_static_file(path)
        # 如果请求的文件不存在，且 dist 存在，则返回 index.html (支持 SPA 路由)
        if os.path.exists(dist_folder):
            return app.send_static_file('index.html')
        return "Not Found", 404

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )
