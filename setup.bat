@echo off
setlocal EnableDelayedExpansion

:: Colors
set "RED=[91m"
set "GREEN=[92m"
set "BLUE=[94m"
set "YELLOW=[93m"
set "BOLD=[1m"
set "NC=[0m"

echo %BLUE%Starting Llamalog setup...%NC%

:: Initialize and update submodules
echo %BLUE%Initializing submodules...%NC%
git submodule update --init --recursive

:: Check prerequisites
call :check_prerequisite "python" "Python"
call :check_prerequisite "npm" "Node.js"
call :check_prerequisite "git" "Git"
call :check_prerequisite "cmake" "CMake"

:: Create directory structure
if not exist "llama.cpp\models" mkdir "llama.cpp\models"
if not exist "logs" mkdir "logs"

:: Setup llama.cpp
echo %BLUE%Setting up llama.cpp...%NC%
cd llama.cpp
cmake -B build -DGGML_CUDA=ON
cmake --build build --config Release
cd ..

:: Download model if it doesn't exist
set "MODEL_PATH=llama.cpp\models\Llama-3.2-3B-Instruct-f16.gguf"
if not exist "%MODEL_PATH%" (
    echo %BLUE%Downloading model to llama.cpp\models directory...%NC%
    powershell -Command "& {Invoke-WebRequest -Uri 'https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-f16.gguf' -OutFile '%MODEL_PATH%'}"
    if !errorlevel! equ 0 (
        echo %GREEN%Model downloaded successfully%NC%
    ) else (
        echo %RED%Failed to download model%NC%
        if exist "%MODEL_PATH%" del "%MODEL_PATH%"
        exit /b 1
    )
) else (
    echo %GREEN%Model already exists in llama.cpp\models directory%NC%
)

:: Setup Python environment
echo %BLUE%Setting up Python environment...%NC%

:: Check Python version
python --version > nul 2>&1
if !errorlevel! neq 0 (
    echo %RED%Python is not installed or not in PATH%NC%
    exit /b 1
)

:: Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo %BLUE%Creating Python virtual environment...%NC%
    python -m venv .venv
    if !errorlevel! neq 0 (
        echo %RED%Failed to create virtual environment%NC%
        exit /b 1
    )
) else (
    echo %YELLOW%Virtual environment already exists, skipping creation...%NC%
)

:: Activate virtual environment and install requirements
call .venv\Scripts\activate.bat
echo %BLUE%Upgrading pip...%NC%
python -m pip install --upgrade pip

if exist "backend\requirements.txt" (
    echo %BLUE%Installing Python dependencies...%NC%
    pip install -r backend\requirements.txt
) else (
    echo %RED%requirements.txt not found in backend directory%NC%
    exit /b 1
)

:: Setup Frontend
echo %BLUE%Setting up frontend...%NC%
cd my-chat-app
call npm install
cd ..

:: Create start.bat if it doesn't exist
echo %BLUE%Creating start script...%NC%
copy housekeeper\start.bat start.bat >nul

echo %GREEN%Setup complete!%NC%
echo %GREEN%To start all servers, run: start.bat%NC%

goto :eof

:: Function to check if a prerequisite is installed
:check_prerequisite
set "cmd=%~1"
set "name=%~2"
where %cmd% >nul 2>&1
if !errorlevel! neq 0 (
    echo %RED%Error: %name% is not installed%NC%
    exit /b 1
)
goto :eof
