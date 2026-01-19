Option Explicit

Dim objShell, objFSO, strScriptPath, strBatPath

' 创建对象
Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' 获取脚本所在目录
strScriptPath = objFSO.GetParentFolderName(WScript.ScriptFullName)
strBatPath = objFSO.BuildPath(strScriptPath, "stop_all.bat")

' 确认停止
If MsgBox("确定要停止 LocalClip Editor 的所有服务吗？", vbYesNo + vbQuestion, "停止服务") = vbNo Then
    WScript.Quit 0
End If

' 检查 BAT 文件是否存在
If Not objFSO.FileExists(strBatPath) Then
    MsgBox "错误：找不到 stop_all.bat 文件！" & vbCrLf & vbCrLf & "路径: " & strBatPath, vbCritical, "停止失败"
    WScript.Quit 1
End If

' 运行 BAT 文件
objShell.Run """" & strBatPath & """", 1, True

' 显示完成提示
MsgBox "所有服务已停止！", vbInformation, "LocalClip Editor"

' 清理对象
Set objShell = Nothing
Set objFSO = Nothing
