#!/bin/bash

# Docker入口点脚本
set -e

# 确保输出目录存在
mkdir -p /app/output

# 设置权限
chmod +x /app/start.sh

# 执行启动脚本
exec /app/start.sh