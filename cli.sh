#!/bin/bash

# Telegram Panel CLI Launcher
# Smart script to manage virtual environment and launch interactive CLI

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/venv"
VENV_PYTHON="$VENV_DIR/bin/python"
VENV_ACTIVATE="$VENV_DIR/bin/activate"
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"
CLI_SCRIPT="$SCRIPT_DIR/interactive_cli.py"

# Function to print colored messages
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

# Check if virtual environment is already active
check_venv_active() {
    if [[ -n "$VIRTUAL_ENV" ]]; then
        print_info "Virtual environment is already active: $VIRTUAL_ENV"
        return 0
    else
        return 1
    fi
}

# Check if venv directory exists
check_venv_exists() {
    if [[ -d "$VENV_DIR" ]] && [[ -f "$VENV_PYTHON" ]]; then
        print_info "Virtual environment found at: $VENV_DIR"
        return 0
    else
        return 1
    fi
}

# Activate existing virtual environment
activate_venv() {
    print_info "Activating virtual environment..."
    if [[ -f "$VENV_ACTIVATE" ]]; then
        source "$VENV_ACTIVATE"
        print_success "Virtual environment activated"
        return 0
    else
        print_error "Activation script not found: $VENV_ACTIVATE"
        return 1
    fi
}

# Create new virtual environment
create_venv() {
    print_info "Creating new virtual environment..."
    
    # Check if python3 is available
    if ! command -v python3 &> /dev/null; then
        print_error "python3 is not installed or not in PATH"
        exit 1
    fi
    
    # Get python version
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    print_info "Using Python $PYTHON_VERSION"
    
    # Create venv
    if python3 -m venv "$VENV_DIR"; then
        print_success "Virtual environment created successfully"
        return 0
    else
        print_error "Failed to create virtual environment"
        exit 1
    fi
}

# Install requirements
install_requirements() {
    print_info "Installing requirements..."
    
    if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
        print_warning "Requirements file not found: $REQUIREMENTS_FILE"
        print_warning "Skipping requirements installation"
        return 0
    fi
    
    # Check if pip is available
    if ! command -v pip &> /dev/null && ! "$VENV_PYTHON" -m pip --version &> /dev/null; then
        print_error "pip is not available"
        exit 1
    fi
    
    # Upgrade pip first
    print_info "Upgrading pip..."
    "$VENV_PYTHON" -m pip install --upgrade pip --quiet
    
    # Install requirements
    print_info "Installing packages from requirements.txt..."
    if "$VENV_PYTHON" -m pip install -r "$REQUIREMENTS_FILE" --quiet; then
        print_success "Requirements installed successfully"
        return 0
    else
        print_error "Failed to install requirements"
        exit 1
    fi
}

# Check if CLI script exists
check_cli_script() {
    if [[ ! -f "$CLI_SCRIPT" ]]; then
        print_error "CLI script not found: $CLI_SCRIPT"
        exit 1
    fi
}

# Main execution
main() {
    print_info "Telegram Panel CLI Launcher"
    print_info "=========================="
    
    # Check if CLI script exists
    check_cli_script
    
    # Check if venv is already active
    if check_venv_active; then
        print_success "Using active virtual environment"
        # Update VENV_PYTHON to use active venv's python
        if [[ -f "$VIRTUAL_ENV/bin/python" ]]; then
            VENV_PYTHON="$VIRTUAL_ENV/bin/python"
        fi
    else
        # Check if venv exists
        if check_venv_exists; then
            # Activate existing venv
            if ! activate_venv; then
                print_error "Failed to activate virtual environment"
                exit 1
            fi
        else
            # Create new venv
            if ! create_venv; then
                exit 1
            fi
            
            # Activate new venv
            if ! activate_venv; then
                print_error "Failed to activate newly created virtual environment"
                exit 1
            fi
            
            # Install requirements
            install_requirements
        fi
    fi
    
    # Verify Python is available
    if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
        print_error "Python is not available"
        exit 1
    fi
    
    # Use python from venv if available, otherwise use system python
    if [[ -n "$VIRTUAL_ENV" ]] && [[ -f "$VENV_PYTHON" ]]; then
        PYTHON_CMD="$VENV_PYTHON"
    elif command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        print_error "Python interpreter not found"
        exit 1
    fi
    
    print_info "Using Python: $($PYTHON_CMD --version 2>&1)"
    print_info "Python path: $(which $PYTHON_CMD)"
    
    # Launch CLI
    print_info "Launching Interactive CLI..."
    print_info "=========================="
    echo ""
    
    # Execute CLI script
    exec "$PYTHON_CMD" "$CLI_SCRIPT" "$@"
}

# Run main function
main "$@"

