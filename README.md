# 可视化UI界面有三个支持：

0. nginx-manager.ps1   使用power shell打开（界面较好，会出现power shell命令行）

1. start-nginx-manager.vbs  在Windows平台可以直接运行vb脚本（界面和power shell脚本一样，这是个套壳，使用vb的方式将power shell命令行隐藏了）

2. start-nginx-manager.bat 在Windows直接运行批处理脚本(dos界面，较丑)

3. nginx_manager.py  需要依赖python环境 （界面优雅！）

建议使用nginx_manager.py，UI比较美观。

有其他需求的可以打开文件更改源码。
