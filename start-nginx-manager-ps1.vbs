Set objShell = CreateObject("WScript.Shell")
strPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
objShell.Run "powershell -windowstyle hidden -executionpolicy bypass -file """ & strPath & "\nginx-manager.ps1""", 0, False