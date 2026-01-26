$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $DesktopPath "Ascendia.lnk"

$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "D:\ai_editing\workspace\LocalClip-Editor\start_all.bat"
$Shortcut.WorkingDirectory = "D:\ai_editing\workspace\LocalClip-Editor"
$Shortcut.Description = "Ascendia - AI-Powered Video Translation Platform"
$Shortcut.IconLocation = "D:\ai_editing\workspace\LocalClip-Editor\logo.ico,0"
$Shortcut.Save()

Write-Host "Shortcut created at: $ShortcutPath"
