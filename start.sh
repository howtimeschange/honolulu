#!/bin/bash
# Honolulu Quick Start Script
# Usage: ./start.sh [server|cli|install|help]

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
    echo "  cli       Start the CLI interface"
    echo "  install   Install all dependencies"
    echo "  test      Run tests"
    echo "  help      Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  ANTHROPIC_API_KEY    Required for Claude models"
    echo "  ANTHROPIC_BASE_URL   Optional: API proxy URL (OneRouter, OpenRouter, etc.)"
    echo "  OPENAI_API_KEY       Optional for OpenAI models"
    echo ""
    echo "Examples:"
    echo "  ./start.sh              # Start server"
    echo "  ./start.sh server       # Start server"
    echo "  ./start.sh cli          # Start CLI"
    echo "  ./start.sh install      # Install dependencies"
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
        echo -e "${YELLOW}Warning: Node.js is not installed (needed for CLI)${NC}"
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
        echo -e "${CYAN}Installing Node.js dependencies...${NC}"
        cd "$CLI_DIR"
        npm install --silent
        npm run build --silent
        npm link --silent
        echo -e "${GREEN}✓ Node.js dependencies installed${NC}"
        echo -e "${GREEN}✓ CLI installed globally as 'honolulu'${NC}"
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

    echo ""
    echo -e "${GREEN}Installation complete!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Set your API key: export ANTHROPIC_API_KEY='your-key'"
    echo "  2. Start the server: ./start.sh server"
    echo "  3. Start the CLI:    ./start.sh cli (or just: honolulu)"
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
