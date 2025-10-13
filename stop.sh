#!/bin/bash

# 停止安全管理系统服务

# 查找并终止Flask应用进程
PID=$(ps aux | grep "python run.py" | grep -v grep | awk '{print $2}')

if [ -n "$PID" ]; then
    echo "正在停止安全管理系统服务..."
    kill -9 $PID
    echo "服务已成功停止"
else
    echo "安全管理系统服务未运行"
fi