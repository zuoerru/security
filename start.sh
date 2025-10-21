#!/bin/bash

# 启动安全管理系统服务

# 设置工作目录
cd $(dirname $0)

# 停止已运行的应用实例
if [ -f stop.sh ]; then
    echo "正在停止已运行的应用实例..."
    ./stop.sh
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖（如果首次运行）
pip install -r requirements.txt || echo "requirements.txt 不存在，跳过依赖安装"

# 确保安装CVE模块所需的依赖
pip install apscheduler requests

# 启动Flask应用
nohup python run.py > app.log 2>&1 &

# 输出启动信息
echo "安全管理系统已启动在端口 8010"
echo "日志文件: app.log"
echo "可以通过 http://服务器IP:8010 访问系统"
echo "CISA模块已配置定时任务，每6小时自动同步数据"
echo "NVD模块已配置定时任务，每6小时自动同步数据"
echo "CVE模块已配置定时任务，每3小时自动同步数据"
echo "CVE模块提供全量数据同步、按时间段同步和日志查询功能"