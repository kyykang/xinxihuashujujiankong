#!/bin/bash
# 重启监控系统

echo "正在停止监控系统..."
pkill -f "python.*app.py"
sleep 2

echo "正在启动监控系统..."
python3 app.py

echo "监控系统已启动在 http://localhost:8080"
