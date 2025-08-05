#!/bin/bash

# WhatIf Backend Service 启动脚本
# 支持统一配置文件 (llm_config.json) 和多 LLM 提供商

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
    
    if [[ ! -f "llm_config.json" ]]; then
        print_error "未找到统一配置文件 llm_config.json！"
        print_info "请创建配置文件或从模板复制："
        print_info "  cp llm_config.json.example llm_config.json"
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

# 检查统一配置文件
check_unified_config() {
    print_info "检查统一配置文件..."
    
    if [[ ! -f "llm_config.json" ]]; then
        print_error "统一配置文件 'llm_config.json' 未找到！"
        print_info "请创建配置文件："
        print_info "  1. 从模板复制: cp llm_config.json.example llm_config.json"
        print_info "  2. 或手动创建配置文件"
        exit 1
    fi
    
    # 检查配置文件是否是有效的JSON
    if ! python3 -c "import json; json.load(open('llm_config.json'))" 2>/dev/null; then
        print_error "llm_config.json 不是有效的JSON格式！"
        print_info "请检查配置文件语法"
        exit 1
    fi
    
    # 提取配置信息
    eval $(python3 -c "
import json
config = json.load(open('llm_config.json'))
provider = config.get('llm_provider', {})
api_keys = config.get('api_keys', {})

print(f'DEFAULT_PROVIDER=\"{provider.get(\"default_provider\", \"\")}\"')
print(f'DEFAULT_MODEL=\"{provider.get(\"default_model\", \"\")}\"')
print(f'OPENAI_API_KEY=\"{api_keys.get(\"openai_api_key\", \"\")}\"')
print(f'GOOGLE_API_KEY=\"{api_keys.get(\"google_api_key\", \"\")}\"')
print(f'ANTHROPIC_API_KEY=\"{api_keys.get(\"anthropic_api_key\", \"\")}\"')
")
    
    print_success "配置文件格式检查通过"
    print_info "当前LLM提供商: $DEFAULT_PROVIDER"
    print_info "当前模型: $DEFAULT_MODEL"
    
    # 检查对应提供商的API密钥
    case "$DEFAULT_PROVIDER" in
        "openai")
            if [[ -z "$OPENAI_API_KEY" ]]; then
                print_warning "OpenAI API Key 未设置！请在 llm_config.json 中添加 api_keys.openai_api_key"
            else
                print_success "OpenAI API Key 已配置"
            fi
            ;;
        "gemini")
            if [[ -z "$GOOGLE_API_KEY" ]]; then
                print_warning "Google API Key 未设置！请在 llm_config.json 中添加 api_keys.google_api_key"
            else
                print_success "Google API Key 已配置"
            fi
            ;;
        "anthropic")
            if [[ -z "$ANTHROPIC_API_KEY" ]]; then
                print_warning "Anthropic API Key 未设置！请在 llm_config.json 中添加 api_keys.anthropic_api_key"
            else
                print_success "Anthropic API Key 已配置"
            fi
            ;;
        *)
            print_warning "未知的LLM提供商: $DEFAULT_PROVIDER"
            ;;
    esac
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
    print_info "使用 LLM 提供商: $DEFAULT_PROVIDER ($DEFAULT_MODEL)"
    print_info "统一配置文件: llm_config.json"
    print_info "记忆系统: 现代化 LangGraph 架构"
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

# 显示配置信息
show_config_info() {
    print_info "WhatIf Backend Service 配置信息"
    echo "================================"
    
    if [[ ! -f "llm_config.json" ]]; then
        print_error "配置文件 llm_config.json 不存在！"
        return 1
    fi
    
    python3 -c "
import json
from datetime import datetime

try:
    config = json.load(open('llm_config.json'))
    
    print('📋 LLM 提供商配置:')
    provider = config.get('llm_provider', {})
    print(f'  默认提供商: {provider.get(\"default_provider\", \"未设置\")}')
    print(f'  默认模型: {provider.get(\"default_model\", \"未设置\")}')
    
    providers = provider.get('providers', {})
    for prov_name, prov_config in providers.items():
        print(f'  {prov_name.upper()}: {prov_config.get(\"models\", [])}')
    
    print()
    print('🔑 API 密钥状态:')
    api_keys = config.get('api_keys', {})
    for key_name, key_value in api_keys.items():
        status = '✓ 已配置' if key_value else '✗ 未配置'
        masked_key = key_value[:8] + '...' + key_value[-4:] if key_value and len(key_value) > 12 else '未设置'
        print(f'  {key_name}: {status} ({masked_key})')
    
    print()
    print('⚙️  生成设置:')
    gen_settings = config.get('generation_settings', {})
    print(f'  默认温度: {gen_settings.get(\"default_temperature\", \"未设置\")}')
    print(f'  最大Token: {gen_settings.get(\"max_tokens\", \"未设置\")}')
    
    memory_settings = gen_settings.get('memory_settings', {})
    print(f'  最大最近事件: {memory_settings.get(\"max_recent_events\", \"未设置\")}')
    print(f'  快照最大大小: {memory_settings.get(\"max_snapshot_size\", \"未设置\")} bytes')
    
    print()
    print('📂 数据路径:')
    data_paths = config.get('data_paths', {})
    for path_name, path_value in data_paths.items():
        print(f'  {path_name}: {path_value}')
    
    print()
    print('🌐 应用设置:')
    app_config = config.get('application', {})
    print(f'  端口: {app_config.get(\"port\", \"未设置\")}')
    print(f'  调试模式: {app_config.get(\"debug\", \"未设置\")}')
    
except Exception as e:
    print(f'❌ 读取配置文件失败: {e}')
"
}

# 显示帮助信息
show_help() {
    echo "WhatIf Backend Service 启动脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help       显示此帮助信息"
    echo "  -p, --port       指定端口号 (默认: 8000)"
    echo "  --no-check       跳过环境检查"
    echo "  --config-info    显示当前配置信息"
    echo ""
    echo "功能:"
    echo "  - 支持多 LLM 提供商 (OpenAI, Gemini, Anthropic)"
    echo "  - 统一配置文件 (llm_config.json)"
    echo "  - 现代化记忆管理系统"
    echo "  - 智能锚点处理和三步法生成"
    echo ""
    echo "示例:"
    echo "  $0                 # 使用默认设置启动"
    echo "  $0 -p 8080         # 在端口8080启动"
    echo "  $0 --no-check      # 跳过环境检查直接启动"
    echo "  $0 --config-info   # 显示配置信息"
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
            --config-info)
                show_config_info
                exit 0
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
        check_unified_config
        check_port $port
    fi
    
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
