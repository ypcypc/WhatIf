#!/bin/bash

# WhatIf Backend Service 启动脚本
# 自动设置环境变量和启动后端服务

set -e  # 遇到错误时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否在正确的目录
check_directory() {
    if [[ ! -f "pyproject.toml" ]]; then
        print_error "未找到 pyproject.toml 文件！请确保在项目根目录中运行此脚本。"
        exit 1
    fi
    
    if [[ ! -d "backend_services" ]]; then
        print_error "未找到 backend_services 目录！请确保在项目根目录中运行此脚本。"
        exit 1
    fi
    
    print_success "项目目录检查通过"
}

# 检查Poetry是否可用
check_poetry() {
    if ! command -v poetry &> /dev/null; then
        print_error "Poetry 未安装或不在 PATH 中！"
        print_info "请安装 Poetry 或确保它在您的 PATH 中："
        echo "  curl -sSL https://install.python-poetry.org | python3 -"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        exit 1
    fi
    
    print_success "Poetry 检查通过: $(poetry --version)"
}

# 检查Python版本
check_python() {
    local python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
    print_info "Python 版本: $python_version"
    
    if [[ $(python3 -c "import sys; print(sys.version_info >= (3, 10))") == "False" ]]; then
        print_warning "建议使用 Python 3.10+ 版本"
    fi
}

# 设置环境变量
setup_environment() {
    print_info "设置环境变量..."
    
    # 检查配置文件是否存在
    if [[ ! -f "config" ]]; then
        print_error "配置文件 'config' 未找到！"
        print_info "请复制 config.example 到 config 并填入您的 OpenAI API Key："
        print_info "  cp config.example config"
        print_info "  # 然后编辑 config 文件添加您的 API Key"
        exit 1
    fi
    
    # 从配置文件读取API Key（如果存在）
    if [[ -f "config" ]] && grep -q "OPENAI_API_KEY" config; then
        source config
        print_success "从配置文件加载 API Key"
    fi
    
    # 检查API Key是否设置
    if [[ -z "$OPENAI_API_KEY" ]]; then
        print_error "OPENAI_API_KEY 未设置！"
        print_info "请在 config 文件中设置您的 OpenAI API Key："
        print_info "  echo 'export OPENAI_API_KEY=\"your-api-key-here\"' >> config"
        exit 1
    fi
    
    print_success "环境变量设置完成"
}

# 检查端口是否被占用
check_port() {
    local port=${1:-8000}
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "端口 $port 已被占用！正在尝试终止现有进程..."
        # 尝试终止占用端口的进程
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
        sleep 2
        
        # 再次检查
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            print_error "无法释放端口 $port，请手动终止相关进程"
            exit 1
        fi
    fi
    
    print_success "端口 $port 可用"
}

# 启动服务
start_service() {
    print_info "启动 WhatIf Backend Service..."
    print_info "服务将在 http://localhost:8000 启动"
    print_info "按 Ctrl+C 停止服务"
    echo ""
    
    # 启动服务
    poetry run python start_backend.py
}

# 清理函数
cleanup() {
    print_info "正在清理..."
    # 这里可以添加清理逻辑
    exit 0
}

# 设置信号处理
trap cleanup SIGINT SIGTERM

# 显示帮助信息
show_help() {
    echo "WhatIf Backend Service 启动脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示此帮助信息"
    echo "  -p, --port     指定端口号 (默认: 8000)"
    echo "  --no-check     跳过环境检查"
    echo ""
    echo "示例:"
    echo "  $0              # 使用默认设置启动"
    echo "  $0 -p 8080      # 在端口8080启动"
    echo "  $0 --no-check   # 跳过环境检查直接启动"
}

# 主函数
main() {
    local port=8000
    local skip_check=false
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -p|--port)
                port="$2"
                shift 2
                ;;
            --no-check)
                skip_check=true
                shift
                ;;
            *)
                print_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    print_info "启动 WhatIf Backend Service..."
    echo "================================"
    
    if [[ "$skip_check" == false ]]; then
        # 执行检查
        check_directory
        check_poetry
        check_python
        check_port $port
    fi
    
    # 设置环境
    setup_environment
    
    echo "================================"
    print_success "环境检查完成，准备启动服务..."
    echo ""
    
    # 启动服务
    start_service
}

# 如果直接运行此脚本，则执行主函数
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
