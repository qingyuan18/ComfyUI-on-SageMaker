#!/bin/bash

CUR_DIR="./"

# 查找使用 8080 端口的进程
PID=$(lsof -ti:8000)

# 如果找到进程，则杀掉它
if [ ! -z "$PID" ]; then
    echo "Killing process $PID using port 8000"
    kill -9 $PID
else
    echo "No process found using port 8000"
fi

# 切换到 ComfyUI 目录
cd "$CUR_DIR"

# 清空 nohup.out 文件
> nohup.out

# 重新启动
echo "Starting api server"
nohup uvicorn aigc_hub_api:app --host 0.0.0.0 --port 8000 --workers 1 &

echo "api server restarted"

