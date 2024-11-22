import tkinter as tk
from tkinter import ttk  # 添加ttk导入
from tkinter import messagebox, simpledialog, scrolledtext
import subprocess
import os
import psutil
import json
import time
import threading

# 配置文件路径
CONFIG_DIR = "conf"  # 生成到conf目录
PID_FILE = "nginx_pids.json"  # 存储nginx进程信息的JSON文件

if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)

# 常用配置项
DEFAULT_CONFIG_OPTIONS = {
    "worker_processes": ["1", "2", "4", "8"],
    "worker_connections": ["1024", "2048", "4096"],
    "keepalive_timeout": ["65", "75", "90"],
    "server_name": ["localhost", "example.com"],
}

# 读取配置文件
def load_configs():
    return [f for f in os.listdir(CONFIG_DIR) if f.endswith('.conf') and f.startswith('custom_')]

# 获取nginx的所有进程PID（主进程和工作进程）
def get_nginx_pids():
    try:
        # 使用Windows原生命令获取nginx进程信息
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq nginx.exe', '/FO', 'CSV'], 
                              capture_output=True, text=True)
        
        # 解析输出取PID
        lines = result.stdout.strip().split('\n')[1:]  # 跳过标题行
        pids = []
        for line in lines:
            # 格式: "nginx.exe","1234","Console","1","8,192 K"
            pid = int(line.split(',')[1].strip('"'))
            pids.append(pid)
        
        return pids
    except Exception as e:
        messagebox.showerror("Error", f"获取进程PID失败: {str(e)}")
        return []

# 启动nginx
def start_nginx(config_file):
    if not config_file:
        messagebox.showwarning("警告", "请先选择配置文件")
        return
        
    try:
        # 启动nginx进程
        process = subprocess.Popen(["nginx", "-c", os.path.join(CONFIG_DIR, config_file)])
        time.sleep(1)  # 等待进程完全启动
        
        # 获取所有nginx进程的PID
        pids = get_nginx_pids()
        if pids:
            port = get_nginx_port(config_file)
            save_nginx_info(pids, port, config_file)
            messagebox.showinfo("成功", f"Nginx已启动，主进程PID: {pids[0]}")
            update_running_status()
        else:
            messagebox.showerror("错误", "Nginx启动失败")
    except Exception as e:
        messagebox.showerror("Error", f"启动失败: {str(e)}")

# 获取nginx使用的端口
def get_nginx_port(config_file):
    try:
        with open(os.path.join(CONFIG_DIR, config_file), 'r') as f:
            for line in f:
                if 'listen' in line:
                    # 提取端口号
                    port = line.split('listen')[1].strip().split()[0].strip(';')
                    return int(port)
    except Exception:
        return 80  # 默认端口
    return 80

# 保存nginx进程信息
def save_nginx_info(pids, port, config_file):
    nginx_info = {}
    if os.path.exists(PID_FILE):
        with open(PID_FILE, 'r') as f:
            nginx_info = json.load(f)

    # 记录进程类型（主进程或工作进程）
    for i, pid in enumerate(pids):
        nginx_info[str(pid)] = {
            "port": port,
            "config_file": config_file,
            "type": "master" if i == 0 else "worker",
            "start_time": time.strftime("%Y-%m-%d %H:%M:%S")
        }

    with open(PID_FILE, 'w') as f:
        json.dump(nginx_info, f, indent=4)

# 停止指定nginx
def stop_selected_nginx():
    selected_config = config_list.get(tk.ACTIVE)
    if not selected_config:
        messagebox.showwarning("警告", "请先选择要停止的 Nginx 实例。")
        return

    try:
        with open(PID_FILE, 'r') as f:
            nginx_info = json.load(f)

        stopped_pids = []
        for pid, info in list(nginx_info.items()):  # 使用list()创建副本进行迭代
            if info["config_file"] == selected_config:
                try:
                    os.kill(int(pid), 15)  # 发送SIGTERM信号
                    stopped_pids.append(pid)
                    del nginx_info[pid]
                except ProcessLookupError:
                    # 如果进程已经不存在，直接从记录中删除
                    del nginx_info[pid]

        # 更新JSON文件
        with open(PID_FILE, 'w') as f:
            json.dump(nginx_info, f, indent=4)

        if stopped_pids:
            messagebox.showinfo("信息", f"已停止 Nginx 实例: PID {', '.join(stopped_pids)}")
        else:
            messagebox.showinfo("信息", "没有找到正在运行的对应Nginx实例")

        update_running_status()
    except Exception as e:
        messagebox.showwarning("警告", f"停止 Nginx 实例失败: {str(e)}")

# 停止所有nginx
def stop_all_nginx():
    try:
        with open(PID_FILE, 'r') as f:
            nginx_info = json.load(f)

        stopped_pids = []
        for pid in list(nginx_info.keys()):  # 使用list()创建副本进行迭代
            try:
                os.kill(int(pid), 15)  # 发送SIGTERM信号
                stopped_pids.append(pid)
            except ProcessLookupError:
                pass  # 忽略已经不存在的进程

        # 清空JSON文件
        with open(PID_FILE, 'w') as f:
            json.dump({}, f)

        if stopped_pids:
            messagebox.showinfo("信息", f"已停止所有 Nginx 实例: PID {', '.join(stopped_pids)}")
        else:
            messagebox.showinfo("信息", "没有找到正在运行的Nginx实例")

        update_running_status()
    except Exception as e:
        messagebox.showwarning("警告", f"停止所有 Nginx 实例失败: {str(e)}")

# 添加监控控制变量和函数
monitoring = False

# 修改监控间隔时间
MONITOR_INTERVAL = 10.0  # 30秒更新一次
UPDATE_BATCH_SIZE = 1    # 由于间隔较长，每次都完整更新
last_cpu_times = {}      # 缓存上次CPU时间

def create_monitor_frame(right_panel):
    monitor_frame = tk.LabelFrame(right_panel, text="进程监控")
    monitor_frame.pack(fill=tk.BOTH, expand=True, pady=5)

    # 使用ttk.Style美化表格外观
    style = ttk.Style()
    style.configure("Treeview", 
                   rowheight=25,
                   font=('Arial', 9))
    style.configure("Treeview.Heading",
                   font=('Arial', 9, 'bold'))

    # 创建表格并设性能优化选项
    tree = ttk.Treeview(monitor_frame,
                       columns=('pid', 'type', 'cpu', 'mem', 'threads', 'start_time', 'runtime', 'config'),
                       show='headings',
                       height=15,
                       selectmode='browse')  # 单选模式，减少开销

    # 配置列
    columns_config = {
        'pid': ('PID', 80),
        'type': ('类型', 80),
        'cpu': ('CPU(%)', 80),
        'mem': ('内存(MB)', 100),
        'threads': ('线程数', 80),
        'start_time': ('启动时间', 150),
        'runtime': ('运行时长', 100),
        'config': ('配置文件', 200)
    }

    for col, (text, width) in columns_config.items():
        tree.heading(col, text=text)
        tree.column(col, width=width, minwidth=50)

    # 使用性能优化的滚动条
    vsb = ttk.Scrollbar(monitor_frame, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(monitor_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    # 布局
    tree.grid(row=0, column=0, sticky='nsew')
    vsb.grid(row=0, column=1, sticky='ns')
    hsb.grid(row=1, column=0, sticky='ew')

    # 添加监控按钮
    button_frame = tk.Frame(monitor_frame)
    button_frame.grid(row=2, column=0, columnspan=2, pady=5)

    monitor_button = tk.Button(
        button_frame,
        text="开始监控",
        command=lambda: start_monitoring(tree),
        width=15,
        height=1
    )
    monitor_button.pack(pady=5)

    monitor_frame.grid_columnconfigure(0, weight=1)
    monitor_frame.grid_rowconfigure(0, weight=1)

    return tree, monitor_button  # 返回树形视图和按钮

def monitor_nginx(tree):
    if not monitoring:
        return
        
    try:
        # 清除现有数据
        for item in tree.get_children():
            tree.delete(item)

        if os.path.exists(PID_FILE):
            with open(PID_FILE, 'r') as f:
                nginx_info = json.load(f)

            for pid, info in list(nginx_info.items()):
                try:
                    # 使用更轻量级的方式检查进程
                    proc = psutil.Process(int(pid))
                    
                    # 基本信息获取
                    memory_mb = proc.memory_info().rss / (1024 * 1024)
                    threads = proc.num_threads()
                    
                    # 计算运行时间
                    start_time = info['start_time']
                    start_timestamp = time.mktime(time.strptime(start_time, "%Y-%m-%d %H:%M:%S"))
                    running_time = time.time() - start_timestamp
                    runtime_str = time.strftime("%H:%M:%S", time.gmtime(running_time))

                    # 插入数据到表格
                    values = (
                        pid,
                        info['type'],
                        "N/A",  # 不再实时获取CPU使用率
                        f"{memory_mb:.1f}",
                        threads,
                        start_time,
                        runtime_str,
                        info['config_file']
                    )
                    
                    tags = ('master',) if info['type'] == 'master' else ('worker',)
                    tree.insert('', 'end', values=values, tags=tags)

                except psutil.NoSuchProcess:
                    # 进程不存在，从JSON中删除
                    del nginx_info[pid]
                    with open(PID_FILE, 'w') as f:
                        json.dump(nginx_info, f, indent=4)
                except Exception as e:
                    print(f"获取进程 {pid} 信息失败: {str(e)}")

            # 配置标签颜色
            tree.tag_configure('master', foreground='blue')
            tree.tag_configure('worker', foreground='green')

    except Exception as e:
        print(f"监控错误: {str(e)}")
    finally:
        # 如果还在监控中，安排下一次更新
        if monitoring:
            root.after(int(MONITOR_INTERVAL * 1000), lambda: monitor_nginx(tree))

def start_monitoring(tree):
    global monitoring
    monitoring = True
    monitor_button.config(
        text="停止监控",
        command=lambda: stop_monitoring(tree),
        bg="red",
        fg="white"
    )
    # 直接在主线程中开始监控
    monitor_nginx(tree)

def stop_monitoring(tree):
    global monitoring
    monitoring = False
    monitor_button.config(
        text="开始监控",
        command=lambda: start_monitoring(tree),
        bg="SystemButtonFace",
        fg="black"
    )

# 更新运行状态
def update_running_status():
    if os.path.exists(PID_FILE):
        with open(PID_FILE, 'r') as f:
            nginx_info = json.load(f)
        
        running_nginx = []
        for pid, info in list(nginx_info.items()):
            try:
                psutil.Process(int(pid))
                instance_info = (
                    f"实例信息: [配置文件: {info['config_file']}]\n"
                    f"进程信息: [PID: {pid} ({info['type']})] "
                    f"[端口: {info['port']}] "
                    f"[启动时间: {info['start_time']}]\n"
                )
                running_nginx.append(instance_info)
            except psutil.NoSuchProcess:
                del nginx_info[pid]
                with open(PID_FILE, 'w') as f:
                    json.dump(nginx_info, f, indent=4)

        status_text.config(state=tk.NORMAL)
        status_text.delete(1.0, tk.END)
        if running_nginx:
            status_text.insert(tk.END, "\n".join(running_nginx))
            status_text.tag_add("running", "1.0", tk.END)
            status_text.tag_config("running", foreground="green")
        else:
            status_text.insert(tk.END, "没有运行的Nginx实例")
            status_text.tag_add("not_running", "1.0", tk.END)
            status_text.tag_config("not_running", foreground="red")
        status_text.config(state=tk.DISABLED)
    else:
        status_text.config(state=tk.NORMAL)
        status_text.delete(1.0, tk.END)
        status_text.insert(tk.END, "没有运行的Nginx实例")
        status_text.tag_add("not_running", "1.0", tk.END)
        status_text.tag_config("not_running", foreground="red")
        status_text.config(state=tk.DISABLED)

# 创建配置文件
def create_config():
    config_name = simpledialog.askstring("创建配置", "请输入配置文件名:")
    if config_name:
        # 确保配置文件名以custom_开头
        if not config_name.startswith('custom_'):
            config_name = 'custom_' + config_name
        # 确保配置文件名以.conf结尾
        if not config_name.endswith('.conf'):
            config_name += '.conf'
            
        try:
            with open(os.path.join(CONFIG_DIR, config_name), 'w', encoding='utf-8') as f:
                f.write(f"""
worker_processes {worker_processes_var.get()};

events {{
    worker_connections {worker_connections_var.get()};
}}

http {{
    include       mime.types;
    default_type  application/octet-stream;

    sendfile        on;
    keepalive_timeout  {keepalive_timeout_var.get()};

    server {{
        listen       {listen_port_var.get()};
        server_name  {server_name_var.get()};

        location / {{
            root   html;
            index  index.html index.htm;
        }}

        error_page   500 502 503 504  /50x.html;
        location = /50x.html {{
            root   html;
        }}
    }}
}}
""")
            update_config_list()
            messagebox.showinfo("成功", f"配置文件 {config_name} 已创建")
        except Exception as e:
            messagebox.showerror("错误", f"创建配置文件失败: {str(e)}")

# 检查配置
def check_config():
    selected_config = config_list.get(tk.ACTIVE)
    if selected_config:
        try:
            result = subprocess.run(
                ["nginx", "-t", "-c", os.path.join(CONFIG_DIR, selected_config)],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                messagebox.showinfo("成功", "配置文件检查通过")
            else:
                messagebox.showerror("错误", f"配置文件检查失败:\n{result.stderr}")
        except Exception as e:
            messagebox.showerror("错误", f"检查配置失败: {str(e)}")
    else:
        messagebox.showwarning("警告", "请先选择配置文件")

# 更新配置文件列表
def update_config_list():
    config_list.delete(0, tk.END)
    configs = load_configs()
    for config in configs:
        config_list.insert(tk.END, config)

# 删除配置文件
def delete_config():
    selected_config = config_list.get(tk.ACTIVE)
    if selected_config:
        confirm = messagebox.askyesno("确认删除", f"您确定要删除配置文件 {selected_config} 吗？")
        if confirm:
            try:
                os.remove(os.path.join(CONFIG_DIR, selected_config))
                update_config_list()
                messagebox.showinfo("成功", f"配置文件 {selected_config} 已删除")
            except Exception as e:
                messagebox.showerror("错误", f"删除配置文件失败: {str(e)}")
    else:
        messagebox.showwarning("警告", "请先选择要删除的配置文件")

# 创建主窗口
root = tk.Tk()
root.title("Nginx 管理系统")
root.geometry("1200x800")  # 增加窗口宽度

# 创建主框架
main_frame = tk.Frame(root)
main_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

# 左侧面板（配置文件列表和功能按钮）
left_panel = tk.Frame(main_frame)
left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=5)

# 配置文件列表
list_frame = tk.LabelFrame(left_panel, text="配置文件列表")
list_frame.pack(fill=tk.BOTH, expand=True)

# 使用Listbox和Scrollbar组合
list_frame_inner = tk.Frame(list_frame)
list_frame_inner.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

scrollbar = tk.Scrollbar(list_frame_inner)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

config_list = tk.Listbox(
    list_frame_inner, 
    width=40, 
    height=10,
    yscrollcommand=scrollbar.set,
    selectmode=tk.SINGLE,
    font=("Consolas", 10)
)
config_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar.config(command=config_list.yview)

# 功能按钮
button_frame = tk.Frame(left_panel)
button_frame.pack(fill=tk.X, pady=5)

start_button = tk.Button(button_frame, text="启动 Nginx", command=lambda: start_nginx(config_list.get(tk.ACTIVE)))
start_button.pack(fill=tk.X, pady=2)

stop_selected_button = tk.Button(button_frame, text="停止选定 Nginx", command=stop_selected_nginx)
stop_selected_button.pack(fill=tk.X, pady=2)

stop_all_button = tk.Button(button_frame, text="停止所有 Nginx", command=stop_all_nginx)
stop_all_button.pack(fill=tk.X, pady=2)

create_button = tk.Button(button_frame, text="创建配置文件", command=create_config)
create_button.pack(fill=tk.X, pady=2)

check_button = tk.Button(button_frame, text="检查配置", command=check_config)
check_button.pack(fill=tk.X, pady=2)

delete_button = tk.Button(button_frame, text="删除配置文件", command=delete_config)
delete_button.pack(fill=tk.X, pady=2)

# 右侧面板（配置选项和监控）
right_panel = tk.Frame(main_frame)
right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

# 配置选项
config_frame = tk.LabelFrame(right_panel, text="配置选项")
config_frame.pack(fill=tk.X, pady=5)

tk.Label(config_frame, text="Worker Processes:").grid(row=0, column=0, padx=5, pady=2)
worker_processes_var = tk.StringVar(value="1")
tk.OptionMenu(config_frame, worker_processes_var, *DEFAULT_CONFIG_OPTIONS["worker_processes"]).grid(row=0, column=1, padx=5, pady=2)

tk.Label(config_frame, text="Worker Connections:").grid(row=1, column=0, padx=5, pady=2)
worker_connections_var = tk.StringVar(value="1024")
tk.OptionMenu(config_frame, worker_connections_var, *DEFAULT_CONFIG_OPTIONS["worker_connections"]).grid(row=1, column=1, padx=5, pady=2)

tk.Label(config_frame, text="Keepalive Timeout:").grid(row=2, column=0, padx=5, pady=2)
keepalive_timeout_var = tk.StringVar(value="65")
tk.OptionMenu(config_frame, keepalive_timeout_var, *DEFAULT_CONFIG_OPTIONS["keepalive_timeout"]).grid(row=2, column=1, padx=5, pady=2)

tk.Label(config_frame, text="Server Name:").grid(row=3, column=0, padx=5, pady=2)
server_name_var = tk.StringVar(value="localhost")
tk.OptionMenu(config_frame, server_name_var, *DEFAULT_CONFIG_OPTIONS["server_name"]).grid(row=3, column=1, padx=5, pady=2)

tk.Label(config_frame, text="Listen Port:").grid(row=4, column=0, padx=5, pady=2)
listen_port_var = tk.StringVar(value="80")
tk.Entry(config_frame, textvariable=listen_port_var).grid(row=4, column=1, padx=5, pady=2)

# 创建监控区域
monitor_tree, monitor_button = create_monitor_frame(right_panel)

# 底部面板（运行实例信息）
bottom_panel = tk.Frame(root)
bottom_panel.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

# 运行实例信息区
instance_frame = tk.LabelFrame(bottom_panel, text="运行实例信息")
instance_frame.pack(fill=tk.X, pady=5)

status_text = scrolledtext.ScrolledText(
    instance_frame,
    wrap=tk.WORD,
    width=50,
    height=6,  # 固定高度
    font=("Consolas", 10)
)
status_text.pack(fill=tk.X, padx=5, pady=5)
status_text.config(state=tk.DISABLED)

# 初始化
update_config_list()
update_running_status()

# 启动主循环
root.mainloop()