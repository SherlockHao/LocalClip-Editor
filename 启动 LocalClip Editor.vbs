Option Explicit

Dim objShell, objFSO, strScriptPath, strBatPath

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

strScriptPath = objFSO.GetParentFolderName(WScript.ScriptFullName)
strBatPath = objFSO.BuildPath(strScriptPath, "start_all.bat")

If Not objFSO.FileExists(strBatPath) Then
    MsgBox "Cannot find start_all.bat", vbCritical, "Error"
    WScript.Quit 1
End If

objShell.Run "cmd /c """ & strBatPath & """", 1, False

Set objShell = Nothing
Set objFSO = Nothing