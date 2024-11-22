Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# 配置信息
$NGINX_PATH = ".\"
$NGINX_CONF = "$NGINX_PATH\conf\my-nginx.conf"
$currentConfigFile = ""
$configStorePath = Join-Path $NGINX_PATH "current_config.txt"  # 提取配置存储路径

# 保存当前配置文件路径
function Save-CurrentConfig {
    if ($script:currentConfigFile) {  # 增加健壮性检查
        $script:currentConfigFile | Out-File -FilePath $configStorePath -Force
        Write-Host "Debug - Saved config: $script:currentConfigFile"  # 调试输出
    } else {
        Write-Host "Debug - No config to save."  # 调试输出
    }
}

# 读取保存的配置文件路径
function Load-CurrentConfig {
    if (Test-Path $configStorePath) {
        $script:currentConfigFile = Get-Content $configStorePath
        Write-Host "Debug - Loaded config: $script:currentConfigFile"  # 调试输出
        return $script:currentConfigFile
    }
    return ""
}

# Function to check if port is in use
function Test-PortInUse {
    param($Port)
    
    $listener = $null
    try {
        $listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Any, $Port)
        $listener.Start()
        return $false
    } catch {
        return $true
    } finally {
        if ($listener) {
            $listener.Stop()
        }
    }
}

# Function to check if Nginx is already running with specific config
function Test-NginxRunning {
    param($ConfigPath)
    
    $processes = Get-Process nginx -ErrorAction SilentlyContinue
    if (-not $processes) {
        return $false
    }
    
    # 检查是否有相同配置的 Nginx 实例在运行
    $nginxProcess = Get-WmiObject Win32_Process -Filter "name = 'nginx.exe'" | 
        Where-Object { $_.CommandLine -like "*$ConfigPath*" }
    
    return $null -ne $nginxProcess
}



# Function to check Nginx status
function Get-NginxStatus {
    $processes = Get-Process nginx -ErrorAction SilentlyContinue
    $status = New-Object System.Text.StringBuilder
    
    $status.AppendLine("Status Check Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
    $status.AppendLine("=".PadRight(50, "="))
    
    if ($processes) {
        $status.AppendLine("Nginx is RUNNING")
        $status.AppendLine("-".PadRight(50, "-"))
        
        foreach ($proc in $processes) {
            $status.AppendLine("Process Details:")
            $status.AppendLine("  - PID: $($proc.Id)")
            $status.AppendLine("  - Process Name: $($proc.ProcessName)")
            $status.AppendLine("  - Memory Usage: $([math]::Round($proc.WorkingSet / 1MB, 2)) MB")
            $status.AppendLine("  - CPU Time: $($proc.TotalProcessorTime)")
            $status.AppendLine("  - Start Time: $($proc.StartTime)")
            $status.AppendLine("  - Running Time: $((Get-Date) - $proc.StartTime)")
            $status.AppendLine("  - Threads: $($proc.Threads.Count)")
            $status.AppendLine("")
        }
        
        # Check if Nginx is responding
        try {
            $testPort = 8088  # Replace with your Nginx port
            $tcpClient = New-Object System.Net.Sockets.TcpClient
            $tcpClient.Connect("localhost", $testPort)
            $status.AppendLine("Port Status:")
            $status.AppendLine("  - Port $testPort is OPEN and responding")
            $tcpClient.Close()
        } catch {
            $status.AppendLine("Port Status:")
            $status.AppendLine("  - Port $testPort is NOT responding")
        }
        
        # Check config file
        $status.AppendLine("")
        $status.AppendLine("Configuration:")
        $status.AppendLine("-".PadRight(50, "-"))
        $configPath = "$NGINX_PATH\conf\my-nginx.conf"
        if (Test-Path $configPath) {
            $status.AppendLine("  - Config File: Found")
            $status.AppendLine("  - Last Modified: $((Get-Item $configPath).LastWriteTime)")
            $status.AppendLine("  - File Size: $([math]::Round((Get-Item $configPath).Length / 1KB, 2)) KB")
        } else {
            $status.AppendLine("  - Config File: Not Found")
        }
        
        # Check logs
        $status.AppendLine("")
        $status.AppendLine("Log Files:")
        $status.AppendLine("-".PadRight(50, "-"))
        $errorLog = "$NGINX_PATH\logs\error.log"
        $accessLog = "$NGINX_PATH\logs\access.log"
        
        if (Test-Path $errorLog) {
            $status.AppendLine("  - Error Log:")
            $status.AppendLine("    Size: $([math]::Round((Get-Item $errorLog).Length / 1KB, 2)) KB")
            $status.AppendLine("    Last Modified: $((Get-Item $errorLog).LastWriteTime)")
        }
        
        if (Test-Path $accessLog) {
            $status.AppendLine("  - Access Log:")
            $status.AppendLine("    Size: $([math]::Round((Get-Item $accessLog).Length / 1KB, 2)) KB")
            $status.AppendLine("    Last Modified: $((Get-Item $accessLog).LastWriteTime)")
        }
        
        return @{
            IsRunning = $true
            Status = $status.ToString()
        }
    } else {
        $status.AppendLine("Nginx is NOT running!")
        return @{
            IsRunning = $false
            Status = $status.ToString()
        }
    }
}



# Create Form
$form = New-Object System.Windows.Forms.Form
$form.Text = "Nginx Manager"
$form.Size = New-Object System.Drawing.Size(800,620)
$form.StartPosition = "CenterScreen"
$form.BackColor = [System.Drawing.Color]::White

# Create Buttons Panel
$buttonPanel = New-Object System.Windows.Forms.Panel
$buttonPanel.Location = New-Object System.Drawing.Point(10,10)
$buttonPanel.Size = New-Object System.Drawing.Size(770,100)
$form.Controls.Add($buttonPanel)
# Function to update running status
function UpdateRunningStatus {
    $nginxStatus = Get-NginxStatus
    if ($nginxStatus.IsRunning) {
        $runningLabel.Text = "Status: RUNNING"
        $runningLabel.ForeColor = [System.Drawing.Color]::Green
        $buttonStart.Enabled = $false
        $buttonStartDefault.Enabled = $false
        $buttonStop.Enabled = $true
        $buttonReload.Enabled = $true
    } else {
        $runningLabel.Text = "Status: STOPPED"
        $runningLabel.ForeColor = [System.Drawing.Color]::Red
        $buttonStart.Enabled = $true
        $buttonStartDefault.Enabled = $true
        $buttonStop.Enabled = $false
        $buttonReload.Enabled = $false
    }
}


# Create Buttons
$buttonStart = New-Object System.Windows.Forms.Button
$buttonStart.Location = New-Object System.Drawing.Point(0,10)
$buttonStart.Size = New-Object System.Drawing.Size(150,30)
$buttonStart.Text = "Start Nginx (Custom)"
# 修改 Start Nginx (Custom) 按钮
$buttonStart.Add_Click({
    try {
        # 检查端口是否被占用
        if (Test-PortInUse -Port 8088) {
            $statusLabel.Text = "Error: Port 8088 is already in use!"
            $statusLabel.ForeColor = [System.Drawing.Color]::Red
            return
        }
        
        # 检查是否已经有使用相同配置的 Nginx 在运行
        if (Test-NginxRunning -ConfigPath "conf/my-nginx.conf") {
            $statusLabel.Text = "Warning: Nginx is already running with this config!"
            $statusLabel.ForeColor = [System.Drawing.Color]::Orange
            return
        }
        
        Set-Location $NGINX_PATH
        Start-Process "nginx.exe" -ArgumentList "-c","conf/my-nginx.conf" -NoNewWindow
        $script:currentConfigFile = "conf/my-nginx.conf"
        Save-CurrentConfig
        $statusLabel.Text = "Nginx started with custom config"
        $statusLabel.ForeColor = [System.Drawing.Color]::Green
        Start-Sleep -Seconds 1
        $nginxStatus = Get-NginxStatus
        $textBox.Text = $nginxStatus.Status
        UpdateRunningStatus
    } catch {
        $statusLabel.Text = "Error starting Nginx: $($_.Exception.Message)"
        $statusLabel.ForeColor = [System.Drawing.Color]::Red
    }
})

$buttonPanel.Controls.Add($buttonStart)

$buttonStartDefault = New-Object System.Windows.Forms.Button
$buttonStartDefault.Location = New-Object System.Drawing.Point(160,10)
$buttonStartDefault.Size = New-Object System.Drawing.Size(150,30)
$buttonStartDefault.Text = "Start Nginx (Default)"

# 修改 Start Nginx (Default) 按钮
$buttonStartDefault.Add_Click({
    try {
        # 检查端口是否被占用
        if (Test-PortInUse -Port 8088) {
            $statusLabel.Text = "Error: Port 8088 is already in use!"
            $statusLabel.ForeColor = [System.Drawing.Color]::Red
            return
        }
        
        # 检查是否已经有使用默认配置的 Nginx 在运行
        if (Test-NginxRunning -ConfigPath "conf/nginx.conf") {
            $statusLabel.Text = "Warning: Nginx is already running with default config!"
            $statusLabel.ForeColor = [System.Drawing.Color]::Orange
            return
        }
        
        Set-Location $NGINX_PATH
        Start-Process "nginx.exe" -NoNewWindow
        $script:currentConfigFile = ""
        Save-CurrentConfig
        $statusLabel.Text = "Nginx started with default config"
        $statusLabel.ForeColor = [System.Drawing.Color]::Green
        Start-Sleep -Seconds 1
        $nginxStatus = Get-NginxStatus
        $textBox.Text = $nginxStatus.Status
        UpdateRunningStatus
    } catch {
        $statusLabel.Text = "Error starting Nginx: $($_.Exception.Message)"
        $statusLabel.ForeColor = [System.Drawing.Color]::Red
    }
})

$buttonPanel.Controls.Add($buttonStartDefault)

$buttonStop = New-Object System.Windows.Forms.Button
$buttonStop.Location = New-Object System.Drawing.Point(320,10)
$buttonStop.Size = New-Object System.Drawing.Size(150,30)
$buttonStop.Text = "Stop Nginx"
$buttonStop.Add_Click({
    try {
        Set-Location $NGINX_PATH
        Start-Process "nginx.exe" -ArgumentList "-s","stop" -NoNewWindow
        $statusLabel.Text = "Nginx stopped"
        $statusLabel.ForeColor = [System.Drawing.Color]::Orange
        Start-Sleep -Seconds 1
        $nginxStatus = Get-NginxStatus
        $textBox.Text = $nginxStatus.Status
        UpdateRunningStatus
    } catch {
        $statusLabel.Text = "Error stopping Nginx: $($_.Exception.Message)"
        $statusLabel.ForeColor = [System.Drawing.Color]::Red
    }
})
$buttonPanel.Controls.Add($buttonStop)

$buttonReload = New-Object System.Windows.Forms.Button
$buttonReload.Location = New-Object System.Drawing.Point(0,50)
$buttonReload.Size = New-Object System.Drawing.Size(150,30)
$buttonReload.Text = "Reload Config"
# Modify the Reload Config button to use the current config file
# Modify the Reload Config button
$buttonReload.Add_Click({
    try {
        Set-Location $NGINX_PATH
        if ($script:currentConfigFile -ne "") {  # 使用 $script: 前缀
            Start-Process "nginx.exe" -ArgumentList "-s","reload","-c",$script:currentConfigFile -NoNewWindow
            $statusLabel.Text = "Configuration reloaded ($script:currentConfigFile)"
        } else {
            Start-Process "nginx.exe" -ArgumentList "-s","reload" -NoNewWindow
            $statusLabel.Text = "Configuration reloaded (default config)"
        }
        $statusLabel.ForeColor = [System.Drawing.Color]::Green
        Start-Sleep -Seconds 1
        $nginxStatus = Get-NginxStatus
        $textBox.Text = $nginxStatus.Status
        UpdateRunningStatus
    } catch {
        $statusLabel.Text = "Error reloading config: $($_.Exception.Message)"
        $statusLabel.ForeColor = [System.Drawing.Color]::Red
    }
})
$buttonPanel.Controls.Add($buttonReload)

$buttonTest = New-Object System.Windows.Forms.Button
$buttonTest.Location = New-Object System.Drawing.Point(160,50)
$buttonTest.Size = New-Object System.Drawing.Size(150,30)
$buttonTest.Text = "Test Config"
$buttonTest.Add_Click({
    try {
        Set-Location $NGINX_PATH
        # 使用完整路径来执行nginx.exe
        $nginxExe = Join-Path $NGINX_PATH "nginx.exe"
        $result = & $nginxExe -t 2>&1
        $textBox.Text = $result
        $statusLabel.Text = "Configuration tested successfully"
        $statusLabel.ForeColor = [System.Drawing.Color]::Green
    } catch {
        $statusLabel.Text = "Configuration tested error: $($_.Exception.Message)"
        $statusLabel.ForeColor = [System.Drawing.Color]::Red
    }
})
$buttonPanel.Controls.Add($buttonTest)

$buttonStatus = New-Object System.Windows.Forms.Button
$buttonStatus.Location = New-Object System.Drawing.Point(320,50)
$buttonStatus.Size = New-Object System.Drawing.Size(150,30)
$buttonStatus.Text = "Check Status"
$buttonStatus.Add_Click({
    try {
        $nginxStatus = Get-NginxStatus
        $textBox.Text = $nginxStatus.Status
        $statusLabel.Text = "Status check completed"
        $statusLabel.ForeColor = [System.Drawing.Color]::Blue
        UpdateRunningStatus
    } catch {
        $statusLabel.Text = "Error checking status: $($_.Exception.Message)"
        $statusLabel.ForeColor = [System.Drawing.Color]::Red
    }
})
$buttonPanel.Controls.Add($buttonStatus)

# Running Status Label
$runningLabel = New-Object System.Windows.Forms.Label
$runningLabel.Location = New-Object System.Drawing.Point(480,10)
$runningLabel.Size = New-Object System.Drawing.Size(280,30)
$runningLabel.Font = New-Object System.Drawing.Font("Arial", 12, [System.Drawing.FontStyle]::Bold)
$runningLabel.TextAlign = [System.Drawing.ContentAlignment]::MiddleRight
$buttonPanel.Controls.Add($runningLabel)

# Create Status Panel
$statusPanel = New-Object System.Windows.Forms.Panel
$statusPanel.Location = New-Object System.Drawing.Point(10,120)
$statusPanel.Size = New-Object System.Drawing.Size(770,430)
$statusPanel.BorderStyle = [System.Windows.Forms.BorderStyle]::FixedSingle
$form.Controls.Add($statusPanel)

# Create TextBox for logs and status
$textBox = New-Object System.Windows.Forms.TextBox
$textBox.Location = New-Object System.Drawing.Point(5,5)
$textBox.Size = New-Object System.Drawing.Size(758,420)
$textBox.Multiline = $true
$textBox.ScrollBars = "Vertical"
$textBox.Font = New-Object System.Drawing.Font("Consolas", 10)
$textBox.BackColor = [System.Drawing.Color]::White
$textBox.ReadOnly = $true
$statusPanel.Controls.Add($textBox)

# Status Label at bottom
$statusLabel = New-Object System.Windows.Forms.Label
$statusLabel.Location = New-Object System.Drawing.Point(10,560)
$statusLabel.Size = New-Object System.Drawing.Size(770,30)
$statusLabel.Text = "Ready"
$statusLabel.TextAlign = [System.Drawing.ContentAlignment]::MiddleLeft
$form.Controls.Add($statusLabel)

# Form Load Event
$form.Add_Shown({
    UpdateRunningStatus
    $nginxStatus = Get-NginxStatus
    $textBox.Text = $nginxStatus.Status
    
    # 首先尝试从保存的文件加载配置
    $savedConfig = Load-CurrentConfig
    if ($savedConfig) {
        $script:currentConfigFile = $savedConfig
    } else {
        # 如果没有保存的配置，则抛出警告
        $statusLabel.Text = "Warning: No saved config found!"
    }
    
    if ($script:currentConfigFile) {
        $statusLabel.Text = "Current config: $script:currentConfigFile"
    } else {
        $statusLabel.Text = "Current config: Default"
    }
})
# Auto refresh timer
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 10000  # 10 seconds
$timer.Add_Tick({
    UpdateRunningStatus
})
$timer.Start()

# Show Form
$form.ShowDialog()

# Cleanup
$timer.Stop()
$timer.Dispose()