#!/usr/bin/env python3
"""
WhatIf Backend Service 启动脚本

这个脚本用于启动 FastAPI 后端服务
"""

import os
import sys
import uvicorn
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 添加 backend_services 目录到 Python 路径
backend_services_path = project_root / "backend_services"
sys.path.insert(0, str(backend_services_path))

def main():
    """启动 FastAPI 应用"""
    
    # 设置环境变量
    os.environ.setdefault("PYTHONPATH", str(backend_services_path))
    
    # 启动配置
    config = {
        "app": "backend_services.app.main:app",
        "host": "0.0.0.0",
        "port": 8000,
        "reload": True,
        "reload_dirs": [str(backend_services_path)],
        "log_level": "info",
    }
    
    print("🚀 启动 WhatIf Backend Service...")
    print(f"📍 服务地址: http://localhost:{config['port']}")
    print(f"📚 API文档: http://localhost:{config['port']}/docs")
    print(f"🔧 重载模式: {'开启' if config['reload'] else '关闭'}")
    print("=" * 50)
    
    try:
        # 启动 uvicorn 服务器
        uvicorn.run(**config)
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
