Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "cmd /c python ./nginx_manager.py", 0, True