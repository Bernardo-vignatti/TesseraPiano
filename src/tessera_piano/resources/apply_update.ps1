param(
    [Parameter(Mandatory=$true)][string]$Installer,
    [Parameter(Mandatory=$true)][int]$AppProcessId,
    [Parameter(Mandatory=$true)][string]$InstallDirectory,
    [Parameter(Mandatory=$true)][string]$ProfileDirectory,
    [Parameter(Mandatory=$true)][string]$ExpectedVersion,
    [switch]$IsolatedTest,
    [switch]$NoRestart
)
$ErrorActionPreference = 'Stop'
$updateDirectory = Join-Path $ProfileDirectory 'updates'
$backupDirectory = Join-Path $updateDirectory 'previous-installation'
$logFile = Join-Path $updateDirectory 'installation.log'
$executable = Join-Path $InstallDirectory 'TesseraPiano.exe'
try {
    $installResolved = [System.IO.Path]::GetFullPath($InstallDirectory).TrimEnd('\')
    $backupResolved = [System.IO.Path]::GetFullPath($backupDirectory).TrimEnd('\')
    if ($installResolved.Length -lt 10 -or $backupResolved.StartsWith($installResolved + '\')) {
        throw 'Diretório de recuperação inválido.'
    }
    $running = Get-Process -Id $AppProcessId -ErrorAction SilentlyContinue
    if ($running) { $running.WaitForExit() }
    if (Test-Path -LiteralPath $backupDirectory) {
        # Este caminho é fixo dentro do perfil, fora da instalação.
        if (-not $backupResolved.StartsWith([System.IO.Path]::GetFullPath($updateDirectory).TrimEnd('\') + '\')) { throw 'Backup fora do perfil.' }
        Remove-Item -LiteralPath $backupDirectory -Recurse -Force
    }
    Copy-Item -LiteralPath $InstallDirectory -Destination $backupDirectory -Recurse -Force
    $preferences = Join-Path $ProfileDirectory 'preferencias.json'
    if (Test-Path -LiteralPath $preferences) { Copy-Item -LiteralPath $preferences -Destination (Join-Path $updateDirectory 'preferences-before-update.json') -Force }
    $arguments = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/NOICONS', '/TASKS=""', "/DIR=`"$InstallDirectory`"", "/LOG=`"$logFile`"")
    if ($IsolatedTest) { $arguments += '/ISOLATEDTEST=1' }
    $setup = Start-Process -FilePath $Installer -ArgumentList $arguments -PassThru -WindowStyle Hidden -Wait
    if ($setup.ExitCode -notin @(0,3010)) { throw "Instalação interrompida: $($setup.ExitCode)" }
    $healthFile = Join-Path $updateDirectory 'health.json'
    Remove-Item -LiteralPath $healthFile -ErrorAction SilentlyContinue
    $health = Start-Process -FilePath $executable -ArgumentList @('--health-check', "`"$healthFile`"") -PassThru -WindowStyle Hidden
    if (-not $health.WaitForExit(30000)) { $health.Kill(); throw 'A nova versão não respondeu.' }
    if (-not (Test-Path -LiteralPath $healthFile)) { throw 'A nova versão não iniciou corretamente.' }
    $report = Get-Content -LiteralPath $healthFile -Raw | ConvertFrom-Json
    if ($report.version -ne $ExpectedVersion -or -not $report.ok) { throw 'A verificação da nova versão falhou.' }
    'Atualização concluída.' | Set-Content -LiteralPath (Join-Path $updateDirectory 'result.txt') -Encoding UTF8
} catch {
    $_.ToString() | Set-Content -LiteralPath (Join-Path $updateDirectory 'result.txt') -Encoding UTF8
    if (Test-Path -LiteralPath (Join-Path $backupDirectory 'TesseraPiano.exe')) {
        $internalDirectory = [System.IO.Path]::GetFullPath((Join-Path $InstallDirectory '_internal'))
        if ($internalDirectory.StartsWith($installResolved + '\') -and (Test-Path -LiteralPath $internalDirectory)) {
            Remove-Item -LiteralPath $internalDirectory -Recurse -Force
        }
        Get-ChildItem -LiteralPath $backupDirectory | Copy-Item -Destination $InstallDirectory -Recurse -Force
        $savedPreferences = Join-Path $updateDirectory 'preferences-before-update.json'
        if (Test-Path -LiteralPath $savedPreferences) { Copy-Item -LiteralPath $savedPreferences -Destination (Join-Path $ProfileDirectory 'preferencias.json') -Force }
    }
}
if (-not $NoRestart -and (Test-Path -LiteralPath $executable)) {
    Start-Process -FilePath $executable -ArgumentList @('--profile', "`"$ProfileDirectory`"") -WindowStyle Hidden
}
