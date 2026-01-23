# QFNU 成绩监控服务 - Windows 启动脚本
# 使用方法: 右键 -> 使用 PowerShell 运行，或在终端执行: .\start.ps1

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  QFNU 成绩监控服务启动脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 获取脚本所在目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# 检查 .env 文件
if (-not (Test-Path ".env")) {
    Write-Host "[警告] 未找到 .env 配置文件" -ForegroundColor Yellow
    if (Test-Path ".env.example") {
        Write-Host "[提示] 正在从 .env.example 创建 .env 文件..." -ForegroundColor Yellow
        Copy-Item ".env.example" ".env"
        Write-Host "[重要] 请编辑 .env 文件，修改 ADMIN_PASSWORD 后重新运行此脚本" -ForegroundColor Red
        Write-Host ""
        notepad ".env"
        exit 1
    }
}

# 检查 uv 是否安装
$uvPath = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uvPath) {
    Write-Host "[错误] 未找到 uv 包管理器" -ForegroundColor Red
    Write-Host "[提示] 请先安装 uv: https://docs.astral.sh/uv/getting-started/installation/" -ForegroundColor Yellow
    Write-Host "       Windows 安装命令: irm https://astral.sh/uv/install.ps1 | iex" -ForegroundColor Yellow
    exit 1
}

Write-Host "[1/3] 检查 Python 环境..." -ForegroundColor Green

# 同步依赖
Write-Host "[2/3] 同步项目依赖..." -ForegroundColor Green
uv sync
if ($LASTEXITCODE -ne 0) {
    Write-Host "[错误] 依赖安装失败" -ForegroundColor Red
    exit 1
}

Write-Host "[3/3] 启动服务..." -ForegroundColor Green
Write-Host ""
Write-Host "服务启动中，按 Ctrl+C 停止服务" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 启动 Flask 应用
uv run python app.py
