' LocalClip Editor - 创建桌面快捷方式
' 运行此脚本将在桌面创建一个快捷方式，方便快速启动应用

Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

' 获取脚本所在目录
ScriptDir = FSO.GetParentFolderName(WScript.ScriptFullName)

' 获取桌面路径
DesktopPath = WshShell.SpecialFolders("Desktop")

' 快捷方式路径
ShortcutPath = DesktopPath & "\LocalClip Editor.lnk"

' 检查 start.vbs 是否存在
StartVbsPath = ScriptDir & "\start.vbs"
If Not FSO.FileExists(StartVbsPath) Then
    MsgBox "错误：未找到 start.vbs 文件！", vbCritical, "创建快捷方式失败"
    WScript.Quit
End If

' 创建快捷方式
Set Shortcut = WshShell.CreateShortcut(ShortcutPath)
Shortcut.TargetPath = StartVbsPath
Shortcut.WorkingDirectory = ScriptDir
Shortcut.Description = "LocalClip Editor - AI配音编辑器"
Shortcut.IconLocation = "%SystemRoot%\System32\shell32.dll,13"  ' 使用系统图标
Shortcut.Save

' 显示成功消息
MsgBox "桌面快捷方式创建成功！" & vbCrLf & vbCrLf & _
       "快捷方式位置：" & vbCrLf & ShortcutPath & vbCrLf & vbCrLf & _
       "双击桌面上的 'LocalClip Editor' 图标即可启动应用", vbInformation, "创建成功"

' 清理对象
Set Shortcut = Nothing
Set WshShell = Nothing
Set FSO = Nothing
