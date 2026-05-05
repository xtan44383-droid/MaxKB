# 在 Windows PowerShell 中：若仓库与 Python 均在 WSL 内，用 WSL 执行与 Linux 相同的构建脚本。
# 用法（请把路径改成你的 WSL 里仓库路径）:
#   wsl -e bash -lc "cd /home/tlx/projects/MaxKB && bash scripts/build-ui-static.sh"

param(
    [string]$WslRepoPath = "/home/tlx/projects/MaxKB"
)

$cmd = "cd $WslRepoPath && bash scripts/build-ui-static.sh"
Write-Host "执行: wsl -e bash -lc `"$cmd`""
wsl -e bash -lc $cmd
