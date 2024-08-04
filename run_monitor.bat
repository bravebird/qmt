@echo off  
REM 关闭快速编辑模式  
reg add "HKCU\Console" /v QuickEdit /t REG_DWORD /d 0 /f  

REM 继续执行其他命令  
echo 快速编辑模式已关闭

D:
cd d:\qmt
poetry run python -m monitor