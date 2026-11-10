param([Parameter(Mandatory = $true)][string]$ExePath)
$ErrorActionPreference = "Stop"

$app = Start-Process -FilePath (Resolve-Path $ExePath).Path -PassThru
try {
    $deadline = [DateTime]::UtcNow.AddSeconds(45)
    do {
        Start-Sleep -Milliseconds 250
        $app.Refresh()
        if ($app.HasExited) { throw "Packaged GUI exited with code $($app.ExitCode)" }
        if ($app.MainWindowTitle -eq "Unhandled exception in script") {
            throw "PyInstaller displayed its startup error dialog"
        }
        # The first-run guide can become the active window before the main
        # window. Both titles are only set after the packaged Qt UI loads.
        if ($app.MainWindowTitle -like "EasyColab *" -and $app.Responding) {
            Write-Host "Packaged GUI opened: $($app.MainWindowTitle)"
            return
        }
    } while ([DateTime]::UtcNow -lt $deadline)
    throw "Packaged GUI did not show an EasyColab window"
} finally {
    if (-not $app.HasExited) { taskkill /PID $app.Id /T /F | Out-Null }
}
