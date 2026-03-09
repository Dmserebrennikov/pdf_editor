# Creates a desktop shortcut for PDF Editor
$ProjectDir = $PSScriptRoot
$BatPath = Join-Path $ProjectDir "run_pdf_editor.bat"
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "PDF Editor.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($ShortcutPath)
$shortcut.TargetPath = $BatPath
$shortcut.WorkingDirectory = $ProjectDir
$shortcut.Description = "Join PDFs and images into one PDF"
$IconPath = Join-Path $ProjectDir "icon.ico"
if (Test-Path $IconPath) {
    $shortcut.IconLocation = "$IconPath,0"
}
$shortcut.Save()
[System.Runtime.Interopservices.Marshal]::ReleaseComObject($shell) | Out-Null

Write-Host "Shortcut created: $ShortcutPath"
