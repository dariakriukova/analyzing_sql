<#
    .SYNOPSIS
    Installs analyzing.exe

    .DESCRIPTION
    Installs analyzing.exe to $HOME\.pyenv

    .INPUTS
    None.

    .OUTPUTS
    None.

    .EXAMPLE
    PS> install.ps1

    .LINK
    Online version: https://github.com/dariakriukova/analyzing_sql/
#>

$AnalyzingDir = "${env:USERPROFILE}\.analyzing"


Function Main() {
    if (Test-Path -Path $AnalyzingDir) {
      Remove-Item -Path $AnalyzingDir -Recurse -Force
    }

    New-Item -Path $AnalyzingDir -ItemType Directory

    $DownloadPath = "$AnalyzingDir\analyzing.zip"

    Invoke-WebRequest -UseBasicParsing -Uri "https://github.com/dariakriukova/analyzing_sql/releases/download/release/analyzing.zip" -OutFile $DownloadPath
    Expand-Archive -Path $DownloadPath -DestinationPath $AnalyzingDir
    Remove-Item -Path $DownloadPath

    # Update env vars

    $PathParts = [System.Environment]::GetEnvironmentVariable('PATH', "User") -Split ";"

    # Remove existing paths, so we don't add duplicates
    $NewPathParts = $PathParts.Where{ $_ -ne $AnalyzingDir }
    $NewPathParts = $NewPathParts + $AnalyzingDir
    $NewPath = $NewPathParts -Join ";"
    [System.Environment]::SetEnvironmentVariable('PATH', $NewPath, "User")


    Write-Host "analyzing.exe is successfully installed. You may need to close and reopen your terminal before using it."
}

Main
