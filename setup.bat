@echo off
setlocal EnableDelayedExpansion

echo Starting Llamalog setup...

:: Initialize and update submodules
echo Initializing submodules...
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
echo Setting up llama.cpp...
cd llama.cpp
cmake -B build -DGGML_CUDA=ON
cmake --build build --config Release
cd ..

:: Ask about model download
set "MODEL_PATH=llama.cpp\models\Llama-3.2-3B-Instruct-f16.gguf"
echo.
echo Would you like to download the default model (Llama-3.2-3B-Instruct)?
echo Size: ~6GB
echo Path: %MODEL_PATH%
set /p DOWNLOAD_CHOICE="Download? (Y/N): "

if /i "%DOWNLOAD_CHOICE%"=="Y" (
    if not exist "%MODEL_PATH%" (
        echo Downloading model to llama.cpp\models directory...
        powershell -Command "& {Invoke-WebRequest -Uri 'https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-f16.gguf' -OutFile '%MODEL_PATH%'}"
        if !errorlevel! equ 0 (
            echo Model downloaded successfully
        ) else (
            echo Failed to download model
            if exist "%MODEL_PATH%" del "%MODEL_PATH%"
            exit /b 1
        )
    ) else (
        echo Model already exists in llama.cpp\models directory
    )
) else (
    echo.
    echo Skipping model download.
    echo Remember to download GGUF models and place them in: llama.cpp\models\
    echo You can find models at: https://huggingface.co/models?search=gguf
    echo.
    timeout /t 5
)

:: Setup Python environment
echo Setting up Python environment...

:: Check Python installation
echo Checking Python installation...
where python >nul 2>&1
if !errorlevel! neq 0 (
    echo Error: No Python installation found. Please install Python 3.
    exit /b 1
)

:: Check Python version
for /f "tokens=2 delims=." %%I in ('python -c "import sys; print(sys.version.split()[0])"') do (
    if %%I LSS 3 (
        echo Error: Python 3.x is required. Found version %%I
        exit /b 1
    )
)

:: Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo Creating Python virtual environment...
    python -m venv .venv
    if !errorlevel! neq 0 (
        echo Error: Failed to create virtual environment
        exit /b 1
    )
) else (
    echo Virtual environment already exists, skipping creation...
)

:: Activate virtual environment and install requirements
call .venv\Scripts\activate.bat
echo Upgrading pip...
python -m pip install --upgrade pip

if exist "backend\requirements.txt" (
    echo Installing Python dependencies...
    pip install -r backend\requirements.txt
) else (
    echo Error: requirements.txt not found in backend directory
    exit /b 1
)

:: Setup Frontend
echo Setting up frontend...
cd my-chat-app
call npm install
cd ..

:: Create start.bat
echo Creating start script...
(
echo @echo off
echo setlocal EnableDelayedExpansion
echo.
echo :: Create required directories
echo if not exist "backend\data\logs" mkdir "backend\data\logs"
echo if not exist "logs" mkdir "logs"
echo.
echo :: Start services
echo echo Starting services...
echo.
echo :: Start backend
echo echo [1/2] Starting backend...
echo call .venv\Scripts\activate.bat
echo cd backend
echo start /B cmd /C "uvicorn main:app --reload ^> ..\logs\backend.log 2^>^&1"
echo cd ..
echo.
echo :: Start frontend
echo echo [2/2] Starting frontend...
echo cd my-chat-app
echo start /B cmd /C "npm run dev ^> ..\logs\frontend.log 2^>^&1"
echo cd ..
echo.
echo cls
echo echo === Llamalog Services ===
echo echo.
echo echo Running at:
echo echo    http://localhost:5173
echo echo.
echo echo Press Ctrl+C to quit
echo echo.
echo.
echo :: Simple wait and cleanup
echo cmd /C pause ^> nul
echo.
echo echo.
echo echo Cleaning up...
echo taskkill /F /IM node.exe ^>nul 2^>^&1
echo taskkill /F /IM python.exe ^>nul 2^>^&1
echo taskkill /F /IM uvicorn.exe ^>nul 2^>^&1
echo taskkill /F /IM llama-server.exe ^>nul 2^>^&1
echo exit /b 0
) > start.bat

echo Setup complete!
echo To start all servers, run: start.bat

goto :eof

:: Function to check if a prerequisite is installed
:check_prerequisite
set "cmd=%~1"
set "name=%~2"
where %cmd% >nul 2>&1
if !errorlevel! neq 0 (
    echo Error: %name% is not installed
    exit /b 1
)
goto :eof
