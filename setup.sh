!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting Llamalog setup...${NC}"

# Initialize and update submodules
echo -e "${BLUE}Initializing submodules...${NC}"
git submodule update --init --recursive

# Check prerequisites
check_prerequisite() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}Error: $1 is not installed${NC}"
        exit 1
    fi
}

check_prerequisite "python3"
check_prerequisite "npm"
check_prerequisite "git"
check_prerequisite "cmake"

# Create directory structure
mkdir -p llama.cpp/models
mkdir -p logs

# Setup llama.cpp
echo -e "${BLUE}Setting up llama.cpp...${NC}"
cd llama.cpp
cmake -B build -DGGML_CUDA=ON
cmake --build build --config Release
cd ..

# Download model if it doesn't exist
MODEL_PATH="llama.cpp/models/Llama-3.2-3B-Instruct-f16.gguf"
if [ ! -f "$MODEL_PATH" ]; then
    echo -e "${BLUE}Downloading model to llama.cpp/models directory...${NC}"
    wget -O "$MODEL_PATH" https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-f16.gguf

    # Verify download was successful
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Model downloaded successfully${NC}"
    else
        echo -e "${RED}Failed to download model${NC}"
        rm -f "$MODEL_PATH"  # Remove partial download if failed
        exit 1
    fi
else
    echo -e "${GREEN}Model already exists in llama.cpp/models directory${NC}"
fi

# Setup Python backend
get_python_command() {
    # Try different Python commands in order of preference
    for cmd in "python3" "python" "python3.12" "python3.11" "python3.10"; do
        if command -v "$cmd" &> /dev/null; then
            echo "$cmd"
            return 0
        fi
    done
    return 1
}

# Function to install venv if needed
ensure_venv_package() {
    local OS_TYPE
    OS_TYPE="$(uname -s)"
    local PACKAGE_MANAGER

    case "$OS_TYPE" in
        Linux*)
            # Detect Linux distribution
            if [ -f /etc/os-release ]; then
                . /etc/os-release
                case "$ID" in
                    debian|ubuntu)
                        PACKAGE_MANAGER="apt-get"
                        VENV_PACKAGE="python3-venv"
                        ;;
                    fedora|rhel|centos)
                        PACKAGE_MANAGER="dnf"
                        VENV_PACKAGE="python3-venv"
                        ;;
                    arch)
                        PACKAGE_MANAGER="pacman"
                        VENV_PACKAGE="python-virtualenv"
                        ;;
                    *)
                        echo -e "${YELLOW}Unknown distribution. Please install Python venv package manually.${NC}"
                        return 1
                        ;;
                esac

                echo -e "${BLUE}Installing Python venv package...${NC}"
                if [ "$EUID" -ne 0 ]; then
                    echo -e "${YELLOW}This operation may require sudo privileges${NC}"
                    sudo $PACKAGE_MANAGER install -y $VENV_PACKAGE
                else
                    $PACKAGE_MANAGER install -y $VENV_PACKAGE
                fi
            fi
            ;;
        Darwin*)
            # macOS - usually comes with venv
            return 0
            ;;
        MINGW*|MSYS*|CYGWIN*)
            # Windows - Python usually comes with venv
            return 0
            ;;
        *)
            echo -e "${YELLOW}Unknown operating system. Please install Python venv package manually.${NC}"
            return 1
            ;;
    esac
}

# Setup Python environment
echo -e "${BLUE}Setting up Python environment...${NC}"

# Find available Python command
PYTHON_CMD=$(get_python_command)
if [ $? -ne 0 ]; then
    echo -e "${RED}No Python installation found. Please install Python 3.${NC}"
    exit 1
fi

# Verify Python version is 3.x
PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if [[ $(echo "$PYTHON_VERSION < 3.0" | bc) -eq 1 ]]; then
    echo -e "${RED}Python 3.x is required. Found version $PYTHON_VERSION${NC}"
    exit 1
fi

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo -e "${BLUE}Creating Python virtual environment...${NC}"
    if ! $PYTHON_CMD -m venv .venv 2>/dev/null; then
        echo -e "${YELLOW}Failed to create virtual environment. Attempting to install venv...${NC}"
        ensure_venv_package
        if ! $PYTHON_CMD -m venv .venv; then
            echo -e "${RED}Failed to create virtual environment. Please install Python venv package manually.${NC}"
            exit 1
        fi
    fi
else
    echo -e "${YELLOW}Virtual environment already exists, skipping creation...${NC}"
fi

# Activate virtual environment
if [[ "$OS_TYPE" == "MINGW"* ]] || [[ "$OS_TYPE" == "MSYS"* ]] || [[ "$OS_TYPE" == "CYGWIN"* ]]; then
    # Windows
    source .venv/Scripts/activate
else
    # Unix-like systems
    source .venv/bin/activate
fi

# Upgrade pip to latest version
echo -e "${BLUE}Upgrading pip...${NC}"
$PYTHON_CMD -m pip install --upgrade pip

# Install requirements
if [ -f "backend/requirements.txt" ]; then
    echo -e "${BLUE}Installing Python dependencies...${NC}"
    pip install -r backend/requirements.txt
else
    echo -e "${RED}requirements.txt not found in backend directory${NC}"
    exit 1
fi
# Setup Frontend
echo -e "${BLUE}Setting up frontend...${NC}"
cd my-chat-app
npm install
cd ..

# Create start script
cat > start.sh << 'EOF'
#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Cursor movement
SAVE='\033[s'
RESTORE='\033[u'
CLEAR_LINE='\033[K'

# Initialize variables
LLAMA_PID=""
BACKEND_PID=""
FRONTEND_PID=""
START_TIME=$(date +%s)

# Function to print centered text
print_centered() {
    local text="$1"
    local width=$(tput cols)
    local padding=$(( (width - ${#text}) / 2 ))
    printf "%${padding}s%s%${padding}s\n" "" "$text" ""
}

# Function to show elapsed time
show_elapsed_time() {
    local current_time=$(date +%s)
    local elapsed=$((current_time - START_TIME))
    printf "${SAVE}${CLEAR_LINE}Elapsed time: %02d:%02d${RESTORE}" $((elapsed/60)) $((elapsed%60))
}

# Function for countdown timer
countdown() {
    local seconds=$1
    local message=$2
    for (( i=$seconds; i>0; i-- )); do
        echo -ne "\r$message in $i seconds... ${CLEAR_LINE}"
        sleep 1
    done
    echo -e "\r$message now! ${CLEAR_LINE}"
}

# Cleanup function
cleanup() {
    echo -e "\n\n${YELLOW}Shutting down services...${NC}"
    [ ! -z "$LLAMA_PID" ] && kill $LLAMA_PID
    [ ! -z "$BACKEND_PID" ] && kill $BACKEND_PID
    [ ! -z "$FRONTEND_PID" ] && kill $FRONTEND_PID
    echo -e "${GREEN}All services stopped successfully${NC}"
    exit 0
}

# Set up cleanup on script exit
trap cleanup SIGINT SIGTERM

# Clear screen and show welcome message
clear
print_centered "${BOLD}=== Llamalog Server Startup ===${NC}"
echo -e "\n${BLUE}Starting all services...${NC}\n"

# Start llama.cpp server
echo -e "${BLUE}[1/3]${NC} Starting llama.cpp server..."
./llama.cpp/build/bin/llama-server -m llama.cpp/models/Llama-3.2-3B-Instruct-f16.gguf > logs/llama.log 2>&1 &
LLAMA_PID=$!

# Wait for llama.cpp server to initialize
countdown 5 "Initializing llama.cpp server"

# Start Python backend
echo -e "\n${BLUE}[2/3]${NC} Starting Python backend..."
source .venv/bin/activate
cd backend
uvicorn main:app --reload > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait for backend to initialize
countdown 3 "Initializing backend server"

# Start frontend
echo -e "\n${BLUE}[3/3]${NC} Starting frontend..."
cd my-chat-app
npm run dev > ../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait for frontend to initialize
countdown 3 "Initializing frontend"

# Show status dashboard
clear
print_centered "${BOLD}=== Llamalog Services Status ===${NC}"
echo -e "\n${GREEN}✓ All services are running!${NC}\n"
echo -e "📍 Access points:"
echo -e "   ${BOLD}Frontend:${NC}    http://localhost:5173"
echo -e "   ${BOLD}Backend API:${NC}  http://localhost:8000"
echo -e "   ${BOLD}LLM Server:${NC}   http://localhost:8080\n"
echo -e "${YELLOW}ℹ️  Press Ctrl+C to stop all services${NC}\n"
echo -e "${BLUE}Log files:${NC}"
echo -e "   • Frontend:  logs/frontend.log"
echo -e "   • Backend:   logs/backend.log"
echo -e "   • LLM:       logs/llama.log\n"

# Start elapsed time counter
while true; do
    show_elapsed_time
    sleep 1
done
EOF

chmod +x start.sh

echo -e "${GREEN}Setup complete!${NC}"
echo -e "${GREEN}To start all servers, run: ./start.sh${NC}"
