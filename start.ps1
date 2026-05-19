Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Money App - 个人记账程序启动脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
# 检查前端依赖
if (-not (Test-Path "frontend/node_modules")) {
    Write-Host "[检查] 前端依赖..." -ForegroundColor Yellow
Set-Location frontend
    npm install
Set-Location ..
}
# 构建前端
Write-Host "[1/2] 构建前端..." -ForegroundColor Green
Set-Location frontend
npx vite build
Set-Location ..
# 获取本机IP（简化版）
$ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.IPAddress -like '192.*'}).IPAddress | Select-Object -First 1
Write-Host ""
Write-Host "[2/2] 启动后端服务..." -ForegroundColor Green
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   Money App 已启动！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   本机访问: http://localhost:8000" -ForegroundColor White
if ($ip) {
    Write-Host "   手机访问: http://$($ip):8000" -ForegroundColor White
}
Write-Host "   API文档:  http://localhost:8000/docs" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "按 Ctrl+C 停止服务" -ForegroundColor Gray
Write-Host ""
# 启动后端
Set-Location backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

