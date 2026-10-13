$ErrorActionPreference = "Stop"

$url = "http://127.0.0.1:8000/"
try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 2
    if ($response.StatusCode -eq 200) {
        Start-Process $url
        Write-Host "Doccano 已在运行：$url"
        exit 0
    }
} catch {
    # The service is not running yet; start it below.
}

$webCommand = "cd /root/doccano && exec /root/.local/share/execplaneval-doccano/venv/bin/doccano webserver --port 8000"
$workerCommand = "cd /root/doccano && exec /root/.local/share/execplaneval-doccano/venv/bin/doccano task"

Start-Process -FilePath "wsl.exe" -ArgumentList @("-d", "Ubuntu-22.04", "--", "bash", "-lc", $webCommand) -WindowStyle Hidden
Start-Process -FilePath "wsl.exe" -ArgumentList @("-d", "Ubuntu-22.04", "--", "bash", "-lc", $workerCommand) -WindowStyle Hidden

for ($attempt = 0; $attempt -lt 30; $attempt++) {
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            Start-Process $url
            Write-Host "Doccano 已启动：$url"
            exit 0
        }
    } catch {
        # Continue waiting for the web server.
    }
}

throw "Doccano 未能在30秒内启动，请检查WSL Ubuntu-22.04。"
