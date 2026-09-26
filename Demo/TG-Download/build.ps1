# 打 onefile 到桌面 TG-Download\（保留 config/session/history）
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Get-Process -Name "TG-Download" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1
Remove-Item "$env:USERPROFILE\Desktop\TG-Download\.instance.lock" -Force -ErrorAction SilentlyContinue

$desk = Join-Path $env:USERPROFILE "Desktop\TG-Download"
New-Item -ItemType Directory -Force -Path $desk | Out-Null

Get-ChildItem -Path .\tgdl -Filter *.py | ForEach-Object { python -m py_compile $_.FullName }
python -m py_compile gui.py tg_download.py smoke_test.py

pyinstaller --noconfirm --clean --windowed --onefile --name "TG-Download" `
  --distpath $desk `
  --workpath ".\build_pyi" `
  --specpath ".\build_pyi" `
  --collect-all cryptg `
  --collect-all yt_dlp `
  --hidden-import tgdl `
  --hidden-import tgdl.paths --hidden-import tgdl.control --hidden-import tgdl.config `
  --hidden-import tgdl.links --hidden-import tgdl.proxy --hidden-import tgdl.media `
  --hidden-import tgdl.progress --hidden-import tgdl.downloader --hidden-import tgdl.runner `
  --hidden-import tgdl.x_download `
  --hidden-import cryptg --hidden-import socks --hidden-import yt_dlp `
  --exclude-module trio --exclude-module IPython --exclude-module jupyter `
  --exclude-module pytest --exclude-module unittest `
  gui.py

Copy-Item ".\config.json" "$desk\config.json" -Force -ErrorAction SilentlyContinue
Copy-Item ".\config.example.json" "$desk\config.example.json" -Force
if (Test-Path ".\tg_download.session") {
  Copy-Item ".\tg_download.session" "$desk\tg_download.session" -Force
}
if (Test-Path ".\history.jsonl") {
  Copy-Item ".\history.jsonl" "$desk\history.jsonl" -Force
}

Get-Item "$desk\TG-Download.exe" | Format-Table Name, @{N = "MB"; E = { [math]::Round($_.Length / 1MB, 2) } }, LastWriteTime
Write-Host "done: $desk"
