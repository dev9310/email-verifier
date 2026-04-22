@echo off

echo Creating project structure...

REM Create main folder
mkdir email-verifier
cd email-verifier

REM Create .github workflow folder
mkdir .github
mkdir .github\workflows

REM Create files
type nul > .github\workflows\verify.yml
type nul > email_system.py
type nul > verify_and_push.py
type nul > requirements.txt

echo.
echo ===============================
echo Project structure created!
echo ===============================

REM Show structure
tree /f

pause