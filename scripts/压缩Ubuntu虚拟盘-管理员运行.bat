@echo off
chcp 65001 >nul
echo 将关闭 WSL 并压缩 D:\wsl\ubuntu\ext4.vhdx（释放删除大文件后的空洞）
echo 若本窗口不是「以管理员身份运行」，会失败。请关闭后右键本 bat - 以管理员身份运行
pause
wsl --shutdown
timeout /t 4
diskpart /s "%~dp0compact-wsl-vhdx.txt"
echo.
dir "D:\wsl\ubuntu\ext4.vhdx"
echo 完成。按任意键退出
pause
