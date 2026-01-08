#!/bin/bash
# Honolulu Quick Start Script
# Usage: ./start.sh [server|web|cli|install|help]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Project directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE_DIR="$SCRIPT_DIR/packages/core"
CLI_DIR="$SCRIPT_DIR/packages/cli"
WEB_DIR="$SCRIPT_DIR/packages/web"
VENV_DIR="$CORE_DIR/.venv"
ENV_FILE="$SCRIPT_DIR/.env"

# Load .env file if exists
load_env() {
    if [ -f "$ENV_FILE" ]; then
        echo -e "${GREEN}Loading environment from .env${NC}"
        set -a
        source "$ENV_FILE"
        set +a
    fi
}

print_banner() {
    echo -e "${CYAN}"
    echo "  ╔═══════════════════════════════════════════╗"
    echo "  ║     🌋 Honolulu - AI Agent Assistant      ║"
    echo "  ║          by 易成 Kim                       ║"
    echo "  ╚═══════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_help() {
    print_banner
    echo "Usage: ./start.sh [command]"
    echo ""
    echo "Commands:"
    echo "  server    Start the API server (default)"
    echo "  web       Start the Web UI (opens browser automatically)"
    echo "  cli       Start the CLI interface"
    echo "  dev       Start both server and Web UI for development"
    echo "  install   Install all dependencies"
    echo "  test      Run tests"
    echo "  help      Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  ANTHROPIC_API_KEY    Required for Claude models"
    echo "  ANTHROPIC_BASE_URL   Optional: API proxy URL (OneRouter, OpenRouter, etc.)"
    echo "  OPENAI_API_KEY       Optional for OpenAI models"
    echo ""
    echo "Quick Start:"
    echo "  ./start.sh install    # First time setup"
    echo "  ./start.sh dev        # Start server + Web UI"
    echo ""
    echo "Or start separately:"
    echo "  ./start.sh server     # Terminal 1: Start API server"
    echo "  ./start.sh web        # Terminal 2: Start Web UI"
    echo "  ./start.sh cli        # Terminal 2: Start CLI (alternative)"
}

check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Error: Python 3 is not installed${NC}"
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
}

check_node() {
    if ! command -v node &> /dev/null; then
        echo -e "${YELLOW}Warning: Node.js is not installed (needed for CLI/Web UI)${NC}"
        return 1
    fi

    NODE_VERSION=$(node -v)
    echo -e "${GREEN}✓ Node.js $NODE_VERSION found${NC}"
    return 0
}

check_api_key() {
    if [ -z "$ANTHROPIC_API_KEY" ]; then
        echo -e "${YELLOW}Warning: ANTHROPIC_API_KEY is not set${NC}"
        echo -e "${YELLOW}Please set it with: export ANTHROPIC_API_KEY='your-key'${NC}"
        echo ""
        read -p "Do you want to continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        echo -e "${GREEN}✓ ANTHROPIC_API_KEY is set${NC}"
    fi
}

setup_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${CYAN}Creating virtual environment...${NC}"
        python3 -m venv "$VENV_DIR"
    fi

    source "$VENV_DIR/bin/activate"
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
}

install_python_deps() {
    echo -e "${CYAN}Installing Python dependencies...${NC}"
    cd "$CORE_DIR"
    pip install -e ".[dev]" --quiet
    echo -e "${GREEN}✓ Python dependencies installed${NC}"
}

install_node_deps() {
    if check_node; then
        echo -e "${CYAN}Installing CLI dependencies...${NC}"
        cd "$CLI_DIR"
        npm install --silent
        npm run build --silent
        npm link --silent 2>/dev/null || true
        echo -e "${GREEN}✓ CLI installed globally as 'honolulu'${NC}"
    fi
}

install_web_deps() {
    if check_node; then
        echo -e "${CYAN}Installing Web UI dependencies...${NC}"
        cd "$WEB_DIR"
        npm install --silent
        echo -e "${GREEN}✓ Web UI dependencies installed${NC}"
    fi
}

do_install() {
    print_banner
    echo -e "${CYAN}Installing Honolulu...${NC}"
    echo ""

    check_python
    setup_venv
    install_python_deps
    install_node_deps
    install_web_deps

    echo ""
    echo -e "${GREEN}Installation complete!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Set your API key: export ANTHROPIC_API_KEY='your-key'"
    echo "     Or create a .env file: cp .env.example .env && edit .env"
    echo ""
    echo "  2. Start the application:"
    echo "     ./start.sh dev     # Start server + Web UI (recommended)"
    echo "     ./start.sh server  # Start server only"
    echo "     ./start.sh web     # Start Web UI only"
    echo "     ./start.sh cli     # Start CLI only"
}

start_server() {
    print_banner

    load_env
    check_python
    check_api_key
    setup_venv

    # Check if dependencies are installed
    if ! pip show honolulu &> /dev/null; then
        echo -e "${YELLOW}Dependencies not installed. Running install...${NC}"
        install_python_deps
    fi

    echo ""
    echo -e "${GREEN}Starting Honolulu API Server...${NC}"
    echo -e "${CYAN}Server URL: http://127.0.0.1:8420${NC}"
    echo -e "${CYAN}API Docs:   http://127.0.0.1:8420/docs${NC}"
    echo ""
    echo "Press Ctrl+C to stop"
    echo ""

    cd "$SCRIPT_DIR"
    honolulu-server
}

start_web() {
    print_banner

    if ! check_node; then
        echo -e "${RED}Error: Node.js is required for Web UI${NC}"
        exit 1
    fi

    cd "$WEB_DIR"

    # Check if dependencies are installed
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}Dependencies not installed. Running npm install...${NC}"
        npm install --silent
    fi

    echo ""
    echo -e "${GREEN}Starting Honolulu Web UI...${NC}"
    echo -e "${CYAN}Web UI:  http://localhost:5173${NC}"
    echo -e "${CYAN}Server:  http://127.0.0.1:8420 (make sure it's running)${NC}"
    echo ""
    echo "Press Ctrl+C to stop"
    echo ""

    npm run dev
}

start_dev() {
    print_banner

    load_env
    check_python
    check_node
    check_api_key
    setup_venv

    # Check Python dependencies
    if ! pip show honolulu &> /dev/null; then
        echo -e "${YELLOW}Python dependencies not installed. Running install...${NC}"
        install_python_deps
    fi

    # Check Web dependencies
    if [ ! -d "$WEB_DIR/node_modules" ]; then
        echo -e "${YELLOW}Web dependencies not installed. Running npm install...${NC}"
        cd "$WEB_DIR"
        npm install --silent
    fi

    echo ""
    echo -e "${GREEN}Starting Honolulu in development mode...${NC}"
    echo ""
    echo -e "${CYAN}API Server: http://127.0.0.1:8420${NC}"
    echo -e "${CYAN}Web UI:     http://localhost:5173${NC}"
    echo -e "${CYAN}API Docs:   http://127.0.0.1:8420/docs${NC}"
    echo ""
    echo "Press Ctrl+C to stop all services"
    echo ""

    cd "$SCRIPT_DIR"

    # Start server in background
    honolulu-server &
    SERVER_PID=$!

    # Wait for server to start
    sleep 2

    # Start web UI
    cd "$WEB_DIR"
    npm run dev &
    WEB_PID=$!

    # Wait a bit then open browser
    sleep 3
    if command -v open &> /dev/null; then
        open "http://localhost:5173"
    elif command -v xdg-open &> /dev/null; then
        xdg-open "http://localhost:5173"
    fi

    # Handle cleanup on exit
    trap "kill $SERVER_PID $WEB_PID 2>/dev/null" EXIT

    # Wait for processes
    wait
}

start_cli() {
    print_banner

    load_env

    if ! check_node; then
        echo -e "${RED}Error: Node.js is required for CLI${NC}"
        exit 1
    fi

    cd "$CLI_DIR"

    # Check if dependencies are installed
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}Dependencies not installed. Running npm install...${NC}"
        npm install --silent
        npm run build --silent
    fi

    echo ""
    echo -e "${GREEN}Starting Honolulu CLI...${NC}"
    echo ""

    npm start
}

run_tests() {
    print_banner

    check_python
    setup_venv

    echo -e "${CYAN}Running tests...${NC}"
    cd "$CORE_DIR"
    pytest tests/ -v
}

# Main
cd "$SCRIPT_DIR"

case "${1:-server}" in
    server)
        start_server
        ;;
    web)
        start_web
        ;;
    dev)
        start_dev
        ;;
    cli)
        start_cli
        ;;
    install)
        do_install
        ;;
    test)
        run_tests
        ;;
    help|--help|-h)
        print_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        print_help
        exit 1
        ;;
esac
