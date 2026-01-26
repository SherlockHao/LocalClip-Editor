Option Explicit

Dim objShell, objShortcut, strDesktop, strTarget, strIcon

Set objShell = CreateObject("WScript.Shell")
strDesktop = objShell.SpecialFolders("Desktop")

' Create shortcut
Set objShortcut = objShell.CreateShortcut(strDesktop & "\Ascendia.lnk")

' Set shortcut properties
objShortcut.TargetPath = "D:\ai_editing\workspace\LocalClip-Editor\start_all.bat"
objShortcut.WorkingDirectory = "D:\ai_editing\workspace\LocalClip-Editor"
objShortcut.Description = "Ascendia - AI-Powered Video Translation Platform"
objShortcut.WindowStyle = 1

' Use a nice icon (video/multimedia icon from shell32.dll)
' Icon index 176 = Video camera icon
' Icon index 21 = Computer with audio icon
' Icon index 238 = Blue globe/network icon
objShortcut.IconLocation = "D:\ai_editing\workspace\LocalClip-Editor\logo.ico,0"

objShortcut.Save

MsgBox "Desktop shortcut created successfully!" & vbCrLf & vbCrLf & "Location: " & strDesktop & "\Ascendia.lnk", vbInformation, "Ascendia"

Set objShortcut = Nothing
Set objShell = Nothing
