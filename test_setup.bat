@echo off
REM AI Art Bot - Quick Test Script
REM Double-click this file to test your bot setup

echo ========================================
echo    AI Art Bot - Quick Test
echo ========================================
echo.

echo Checking Python installation...
python --version
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)
echo.

echo Checking dependencies...
python -c "import openai, selenium, requests" 2>nul
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
) else (
    echo ✓ All dependencies installed
)
echo.

echo ========================================
echo    Testing Prompt Generation
echo ========================================
python art_bot.py test
echo.

echo ========================================
echo    Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Edit config.json with your OpenAI API key
echo 2. Make sure Instagram is logged in on Chrome
echo 3. Run: python art_bot.py generate (to test)
echo 4. Run: python art_bot.py post (to test posting)
