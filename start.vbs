' LocalClip Editor - Silent Startup Script
' Double-click this file to start the application (no console window)

Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

' Get script directory
ScriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)

' Build full path to start.bat
BatPath = ScriptDir & "\start.bat"

' Check if start.bat exists
If Not FSO.FileExists(BatPath) Then
    MsgBox "Error: start.bat not found!" & vbCrLf & "Path: " & BatPath, vbCritical, "Startup Failed"
    WScript.Quit
End If

' Run start.bat hidden (window style=0 means hidden, bWaitOnReturn=False means don't wait)
' start.bat will handle service detection and browser opening
WshShell.Run Chr(34) & BatPath & Chr(34), 0, False

' Cleanup objects
Set WshShell = Nothing
Set FSO = Nothing
