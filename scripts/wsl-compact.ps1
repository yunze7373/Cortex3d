# Cortex3d WSL 空间压缩脚本
# 在 Windows PowerShell (管理员) 中运行

Write-Host "======================================"
Write-Host "Cortex3d WSL 磁盘压缩工具"
Write-Host "======================================"
Write-Host ""

# 检查是否以管理员身份运行
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "❌ 错误: 此脚本需要管理员权限" -ForegroundColor Red
    Write-Host ""
    Write-Host "请右键点击 PowerShell 并选择 '以管理员身份运行'" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "按 Enter 退出"
    exit 1
}

Write-Host "✅ 管理员权限已确认" -ForegroundColor Green
Write-Host ""

# Docker WSL 磁盘路径
$dockerVhdxPath = "$env:LOCALAPPDATA\Docker\wsl\data\ext4.vhdx"

# 检查文件是否存在
if (-not (Test-Path $dockerVhdxPath)) {
    Write-Host "❌ 错误: 找不到 Docker WSL 磁盘" -ForegroundColor Red
    Write-Host "路径: $dockerVhdxPath" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "请确保 Docker Desktop 已安装并启用 WSL 2 后端" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "按 Enter 退出"
    exit 1
}

# 显示当前磁盘大小
$currentSize = (Get-Item $dockerVhdxPath).Length / 1GB
Write-Host "📊 当前 Docker WSL 磁盘大小: $([math]::Round($currentSize, 2)) GB" -ForegroundColor Cyan
Write-Host ""

# 确认继续
Write-Host "⚠️  即将执行以下操作:" -ForegroundColor Yellow
Write-Host "1. 关闭所有 WSL 实例"
Write-Host "2. 压缩 Docker WSL 磁盘"
Write-Host "3. 可能需要 10-30 分钟"
Write-Host ""

$confirm = Read-Host "确认继续? (Y/N)"

if ($confirm -ne 'Y' -and $confirm -ne 'y') {
    Write-Host "已取消"
    exit 0
}

Write-Host ""
Write-Host "======================================"
Write-Host "开始压缩..."
Write-Host "======================================"
Write-Host ""

# 1. 关闭 WSL
Write-Host "🛑 关闭 WSL..." -ForegroundColor Yellow
wsl --shutdown
Start-Sleep -Seconds 3

# 确认 WSL 已关闭
$wslRunning = wsl -l --running
if ($wslRunning) {
    Write-Host "⚠️  警告: WSL 仍在运行，再次尝试关闭..." -ForegroundColor Yellow
    wsl --shutdown
    Start-Sleep -Seconds 5
}

Write-Host "✅ WSL 已关闭" -ForegroundColor Green
Write-Host ""

# 2. 压缩磁盘
Write-Host "🗜️  压缩磁盘 (这可能需要 10-30 分钟)..." -ForegroundColor Yellow
Write-Host "请耐心等待，不要中断操作..." -ForegroundColor Yellow
Write-Host ""

try {
    $startTime = Get-Date
    
    Optimize-VHD -Path $dockerVhdxPath -Mode Full
    
    $endTime = Get-Date
    $duration = ($endTime - $startTime).TotalMinutes
    
    Write-Host ""
    Write-Host "✅ 压缩完成! 耗时: $([math]::Round($duration, 1)) 分钟" -ForegroundColor Green
    Write-Host ""
    
    # 显示压缩后的大小
    $newSize = (Get-Item $dockerVhdxPath).Length / 1GB
    $saved = $currentSize - $newSize
    
    Write-Host "======================================"
    Write-Host "压缩结果:"
    Write-Host "======================================"
    Write-Host "压缩前: $([math]::Round($currentSize, 2)) GB" -ForegroundColor Cyan
    Write-Host "压缩后: $([math]::Round($newSize, 2)) GB" -ForegroundColor Green
    Write-Host "节省空间: $([math]::Round($saved, 2)) GB" -ForegroundColor Yellow
    Write-Host ""
    
} catch {
    Write-Host ""
    Write-Host "❌ 压缩失败: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "可能的原因:" -ForegroundColor Yellow
    Write-Host "1. WSL 仍在运行 (需要完全关闭)"
    Write-Host "2. Docker Desktop 正在运行"
    Write-Host "3. 磁盘被其他程序占用"
    Write-Host ""
    Read-Host "按 Enter 退出"
    exit 1
}

# 3. 提示重启 Docker
Write-Host "💡 下一步:" -ForegroundColor Yellow
Write-Host "1. 重启 Docker Desktop"
Write-Host "2. 等待 Docker 完全启动"
Write-Host "3. 运行 'docker ps' 验证容器状态"
Write-Host ""

Read-Host "按 Enter 退出"
