#!/bin/bash

# 服务监控脚本
# 功能：检查安全管理系统服务是否正常运行，异常时自动重启

# 日志文件路径
LOG_FILE="/data_nfs/121/app/security/monitor.log"
SERVICE_DIR="/data_nfs/121/app/security"
START_SCRIPT="${SERVICE_DIR}/start.sh"
PORT=8010

# 确保日志目录存在
mkdir -p "$(dirname "${LOG_FILE}")"

# 记录日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "${LOG_FILE}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 检查服务是否在运行
check_service() {
    # 检查端口是否被占用
    if netstat -tlnp 2>/dev/null | grep ":${PORT} " >/dev/null; then
        # 检查是否有python run.py进程在运行
        if ps aux | grep "python run.py" | grep -v grep >/dev/null; then
            return 0  # 服务正常运行
        fi
    fi
    return 1  # 服务异常
}

# 检查服务状态
log "开始检查安全管理系统服务状态..."
if check_service; then
    log "服务正常运行在端口 ${PORT}"
else
    log "警告：服务未正常运行，准备重启..."
    
    # 切换到服务目录并重启服务
    cd "${SERVICE_DIR}" || {
        log "错误：无法切换到服务目录 ${SERVICE_DIR}"
        exit 1
    }
    
    # 执行重启脚本
    if [ -x "${START_SCRIPT}" ]; then
        log "执行重启脚本 ${START_SCRIPT}"
        bash "${START_SCRIPT}" >> "${LOG_FILE}" 2>&1
        log "服务重启完成"
    else
        log "错误：启动脚本不存在或不可执行 ${START_SCRIPT}"
        exit 1
    fi
fi

log "检查完成"