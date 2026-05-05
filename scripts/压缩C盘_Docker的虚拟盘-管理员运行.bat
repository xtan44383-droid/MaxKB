@echo off
chcp 65001 >nul
title 压缩 C 盘上 Docker 的 WSL 虚拟盘 (回收 C 盘空间)
echo.
echo [说明] 你的 Ubuntu 系统在 D:\wsl\ubuntu，不占用 C 盘这块。
echo 占 C 盘、且能压缩的 WSL 相关大文件，通常是 Docker Desktop 的:
echo   - docker_data.vhdx  (约 7~8GB 起，会随镜像变大)
echo   - main\ext4.vhdx    (较小)
echo.
echo [必须] 1) 在任务栏托盘里 退出 Docker Desktop (完全退出)
echo        2) 本文件 右键 - 以管理员身份运行
echo        3) 执行前会自动 wsl --shutdown
echo.
pause
wsl --shutdown
echo 已尝试关闭 WSL，若 Docker 仍在用盘，请确认已退出 Docker 后再重试本脚本
timeout /t 5
diskpart /s "%~dp0compact-docker-C盘.txt"
echo.
echo 压缩后查看大小:
dir "C:\Users\tlx\AppData\Local\Docker\wsl\disk\docker_data.vhdx"
dir "C:\Users\tlx\AppData\Local\Docker\wsl\main\ext4.vhdx"
echo.
echo 若仍缺空间: 在 Docker Desktop 里 清理不用的镜像/卷，或 设置 里看数据目录是否可迁到 D 盘
pause
