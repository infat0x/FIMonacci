@echo off
REM Easy SSH Connection Script for FIMonacci Server
REM Server IP: 13.62.224.164
REM Username: ubuntu
REM Password: fimonacci123

echo ========================================
echo   FIMonacci Server SSH Connection
echo ========================================
echo Server: 13.62.224.164
echo User: ubuntu
echo.
echo Connecting...
echo.

ssh -o StrictHostKeyChecking=no ubuntu@13.62.224.164

pause
