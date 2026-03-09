@echo off
cd /d "%~dp0"
"C:\Users\ASUS\anaconda3\python.exe" main.py
if errorlevel 1 pause
