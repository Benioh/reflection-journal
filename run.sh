#!/bin/bash

# 复盘日志启动脚本
cd "$(dirname "$0")"

# 检查虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "../venv" ]; then
    source ../venv/bin/activate
fi

# 运行应用
python main.py 