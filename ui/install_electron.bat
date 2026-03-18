@echo off
echo ========================================
echo Installing Electron Dependencies
echo ========================================
echo.

REM Check if pnpm is installed
where pnpm >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] pnpm is not installed!
    echo.
    echo Installing dependencies with npm instead...
    call npm install
) else (
    echo Installing dependencies with pnpm...
    call pnpm install
)

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo You can now run:
echo   - start_electron.bat      (to start development)
echo   - build_electron.bat      (to build the app)
echo.

pause

