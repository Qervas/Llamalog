@echo off
setlocal EnableDelayedExpansion

:: Enable ANSI escape sequences for Windows 10 and later
reg add HKEY_CURRENT_USER\Console /v VirtualTerminalLevel /t REG_DWORD /d 1 /f >nul 2>&1

:: Colors
set "RED=[91m"
set "GREEN=[92m"
set "BLUE=[94m"
set "YELLOW=[93m"
set "BOLD=[1m"
set "NC=[0m"

:: Initialize variables
set "START_TIME=%TIME%"
set "LLAMA_PID="
set "BACKEND_PID="
set "FRONTEND_PID="

:: Function to print centered text (called via call)
:print_centered
set "text=%~1"
for /f "tokens=2" %%a in ('mode con ^| findstr "Columns"') do set "cols=%%a"
set /a "padding=%cols% - %text:~0,1%"
set /a "padding/=2"
set "spaces="
for /l %%i in (1,1,%padding%) do set "spaces=!spaces! "
echo.%spaces%%~1
goto :eof

:: Function for countdown timer
:countdown
set "seconds=%~1"
set "message=%~2"
for /l %%i in (%seconds%,-1,1) do (
    echo.|set /p="%message% in %%i seconds... "
    timeout /t 1 /nobreak >nul
    echo.
)
echo %message% now!
goto :eof

:: Clear screen and show welcome message
cls
call :print_centered "%BOLD%=== Llamalog Server Startup ===%NC%"
echo.
echo %BLUE%Starting all services...%NC%
echo.

:: Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

:: Start llama.cpp server
echo %BLUE%[1/3]%NC% Starting llama.cpp server...
start /B "" cmd /c "llama.cpp\build\Release\llama-server.exe -m llama.cpp\models\Llama-3.2-3B-Instruct-f16.gguf > logs\llama.log 2>&1"
for /f "tokens=2" %%a in ('tasklist ^| findstr "llama-server.exe"') do set LLAMA_PID=%%a

:: Wait for llama.cpp server to initialize
call :countdown 5 "Initializing llama.cpp server"

:: Start Python backend
echo.
echo %BLUE%[2/3]%NC% Starting Python backend...
call .venv\Scripts\activate.bat
cd backend
start /B "" cmd /c "uvicorn main:app --reload > ..\logs\backend.log 2>&1"
for /f "tokens=2" %%a in ('tasklist ^| findstr "python.exe"') do set BACKEND_PID=%%a
cd ..

:: Wait for backend to initialize
call :countdown 3 "Initializing backend server"

:: Start frontend
echo.
echo %BLUE%[3/3]%NC% Starting frontend...
cd my-chat-app
start /B "" cmd /c "npm run dev > ..\logs\frontend.log 2>&1"
for /f "tokens=2" %%a in ('tasklist ^| findstr "node.exe"') do set FRONTEND_PID=%%a
cd ..

:: Wait for frontend to initialize
call :countdown 3 "Initializing frontend"

:: Show status dashboard
cls
call :print_centered "%BOLD%=== Llamalog Services Status ===%NC%"
echo.
echo %GREEN%✓ All services are running!%NC%
echo.
echo 📍 Access points:
echo    %BOLD%Frontend:%NC%    http://localhost:5173
echo    %BOLD%Backend API:%NC%  http://localhost:8000
echo    %BOLD%LLM Server:%NC%   http://localhost:8080
echo.
echo %YELLOW%ℹ️  Press Ctrl+C to stop all services%NC%
echo.
echo %BLUE%Log files:%NC%
echo    • Frontend:  logs\frontend.log
echo    • Backend:   logs\backend.log
echo    • LLM:       logs\llama.log
echo.

:: Function to show elapsed time
:show_elapsed_time
set "current_time=%TIME%"
call :calc_elapsed "!START_TIME!" "!current_time!"
echo Elapsed time: !hours!:!minutes!:!seconds!
timeout /t 1 /nobreak >nul
goto show_elapsed_time

:: Calculate elapsed time
:calc_elapsed
set "start=%~1"
set "end=%~2"
set /a "hours=1%end:~0,2%-1%start:~0,2%"
set /a "minutes=1%end:~3,2%-1%start:~3,2%"
set /a "seconds=1%end:~6,2%-1%start:~6,2%"
if %seconds% lss 0 (
    set /a "minutes-=1"
    set /a "seconds+=60"
)
if %minutes% lss 0 (
    set /a "hours-=1"
    set /a "minutes+=60"
)
if %hours% lss 0 set /a "hours+=24"
if %hours% lss 10 set "hours=0%hours%"
if %minutes% lss 10 set "minutes=0%minutes%"
if %seconds% lss 10 set "seconds=0%seconds%"
goto :eof

:: Cleanup function (called on Ctrl+C)
:cleanup
echo.
echo %YELLOW%Shutting down services...%NC%
if defined LLAMA_PID taskkill /F /PID %LLAMA_PID% >nul 2>&1
if defined BACKEND_PID taskkill /F /PID %BACKEND_PID% >nul 2>&1
if defined FRONTEND_PID taskkill /F /PID %FRONTEND_PID% >nul 2>&1
echo %GREEN%All services stopped successfully%NC%
exit /b 0

:: Set up cleanup on script exit
if not "%1"=="am_admin" (
    powershell -Command "Start-Process -Verb RunAs -FilePath '%0' -ArgumentList 'am_admin'"
    exit /b
)
