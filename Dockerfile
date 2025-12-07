# 使用Python 3.11基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# 安装uv包管理器
RUN pip install uv

# 复制项目文件
COPY . .

# 安装Python依赖
RUN uv sync --frozen

# 安装Node.js和pnpm
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g pnpm

# 安装前端依赖并构建
RUN cd frontend && \
    pnpm install && \
    pnpm build

# 设置环境变量
ENV PYTHONPATH=/app
ENV HOST=0.0.0.0
ENV PORT=7860
ENV FRONTEND_PORT=5173
ENV CONFIG_DIR=/app/configs

# 创建必要的目录并设置权限
RUN mkdir -p /app/configs /app/output && \
    chmod 755 /app/configs /app/output

# 暴露端口
EXPOSE 7860 5173

# 复制启动脚本
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
COPY docker/start.sh /app/start.sh
COPY hf_space_entrypoint.sh /app/hf_space_entrypoint.sh
COPY hf_proxy.py /app/hf_proxy.py
RUN chmod +x /app/docker-entrypoint.sh /app/start.sh /app/hf_space_entrypoint.sh

# 入口点（HF Space模式）
ENTRYPOINT ["/app/hf_space_entrypoint.sh"]