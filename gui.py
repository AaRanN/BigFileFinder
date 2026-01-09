import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from finder import BigFileFinder
import csv
import os

class BigFileFinderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Windows 大文件查找器")
        self.root.geometry("1000x700")

        # 创建实例
        self.finder = BigFileFinder(callback_func=self.update_from_scanner)

        # --- 控件 ---
        # 1. 顶部控制面板
        control_frame = ttk.Frame(root)
        control_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(control_frame, text="扫描路径:").grid(row=0, column=0, sticky=tk.W)
        self.path_var = tk.StringVar(value="C:\\") # 默认值
        path_entry = ttk.Entry(control_frame, textvariable=self.path_var, width=50)
        path_entry.grid(row=0, column=1, padx=(5, 0), sticky=tk.EW)
        ttk.Button(control_frame, text="浏览", command=self.browse_path).grid(row=0, column=2, padx=(5, 0))

        ttk.Label(control_frame, text="最小文件大小 (MB):").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.size_var = tk.StringVar(value="100") # 默认100MB
        size_entry = ttk.Entry(control_frame, textvariable=self.size_var, width=10)
        size_entry.grid(row=1, column=1, sticky=tk.W, pady=(5, 0))

        self.scan_button = ttk.Button(control_frame, text="开始扫描", command=self.start_scan)
        self.scan_button.grid(row=2, column=0, pady=(10, 0))

        self.stop_button = ttk.Button(control_frame, text="停止扫描", command=self.stop_scan, state=tk.DISABLED)
        self.stop_button.grid(row=2, column=1, pady=(10, 0), sticky=tk.W)

        # 2. 结果表格
        # --- 修改这里：添加 'size_bytes' 列 ---
        columns = ("name", "path", "size", "mtime", "size_bytes")
        # ---
        self.tree = ttk.Treeview(root, columns=columns, show="headings", height=20)
        self.tree.heading("name", text="文件名")
        self.tree.heading("path", text="路径")
        self.tree.heading("size", text="大小", command=lambda: self.sort_tree("size"))
        self.tree.heading("mtime", text="修改日期", command=lambda: self.sort_tree("mtime"))
        # 不为 size_bytes 添加 heading，使其不可见

        self.tree.column("name", width=150)
        self.tree.column("path", width=500)
        self.tree.column("size", width=100, anchor=tk.CENTER)
        self.tree.column("mtime", width=150)
        # --- 修改这里：隐藏 size_bytes 列 ---
        self.tree.column("size_bytes", width=0, stretch=tk.NO) # 宽度为0，且不拉伸
        # ---

        # 添加滚动条
        tree_scroll_y = ttk.Scrollbar(root, orient=tk.VERTICAL, command=self.tree.yview)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=tree_scroll_y.set)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 右键菜单
        self.popup_menu = tk.Menu(self.tree, tearoff=0)
        self.popup_menu.add_command(label="在资源管理器中打开", command=self.open_in_explorer)
        self.popup_menu.add_command(label="删除文件", command=self.delete_selected_file)
        self.popup_menu.add_separator()
        self.popup_menu.add_command(label="导出结果", command=self.export_results)
        self.tree.bind("<Button-3>", self.show_popup_menu) # 绑定右键点击事件

        # 3. 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # --- 内部状态 ---
        self.current_results = []
        self.sort_reverse = {"size": False, "mtime": False}

    def browse_path(self):
        """弹出文件夹选择对话框。"""
        path = filedialog.askdirectory(initialdir=self.path_var.get())
        if path:
            self.path_var.set(path)

    def start_scan(self):
        """启动扫描线程。"""
        path = self.path_var.get().strip()
        try:
            size_threshold = float(self.size_var.get())
            if size_threshold <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("输入错误", "请输入一个有效的大于0的数字作为文件大小阈值。")
            return

        if not os.path.exists(path):
            messagebox.showerror("路径错误", "指定的扫描路径不存在！")
            return

        # 清空旧结果
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.current_results = []
        self.sort_reverse = {"size": False, "mtime": False}

        # 更新按钮状态
        self.scan_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_var.set(f"开始扫描路径: {path} (阈值: {size_threshold} MB)...")

        # 在新线程中运行扫描，避免阻塞GUI
        self.scan_thread = threading.Thread(target=self.finder.scan, args=(path, size_threshold))
        self.scan_thread.daemon = True # 设置为守护线程
        self.scan_thread.start()

    def stop_scan(self):
        """请求停止扫描。"""
        self.finder.stop()
        self.scan_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

    def update_from_scanner(self, event_type, data):
        """由扫描线程调用，更新GUI。此方法在GUI线程中执行。"""
        # 使用 after 方法将GUI更新操作推送到GUI主线程队列
        self.root.after(0, self._handle_scanner_update, event_type, data)

    def _handle_scanner_update(self, event_type, data):
        """处理来自扫描器的更新。"""
        if event_type == "add_result":
            # 添加单个结果到表格
            # --- 修改这里：将原始数据存储在 size_bytes 列中 ---
            item_id = self.tree.insert("", "end", values=(data["name"], data["path"], data["size_formatted"], data["mtime"], data["size_bytes"]))
            # ---
            # 将原始数据存储在item的tags中，方便后续操作 (可选，当前逻辑用不到)
            # self.tree.set(item_id, "size_bytes", data["size_bytes"]) # 这行现在不需要了，因为值已经作为第5个value插入
            self.current_results.append(data)
        elif event_type == "status":
            self.status_var.set(data)
        elif event_type == "scan_finished":
            # 扫描完成，更新按钮状态
            self.scan_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
        elif event_type == "error":
            messagebox.showerror("扫描错误", data)

    def sort_tree(self, col):
        """根据指定列对Treeview进行排序。"""
        # 获取所有项目及其数据
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        # 对于大小列，需要按字节大小排序，而不是格式化后的字符串
        if col == "size":
            # --- 修改这里：从隐藏的 size_bytes 列获取数值进行排序 ---
            l = [(int(self.tree.set(k, "size_bytes")), k) for k in self.tree.get_children('')]
            # ---
            l.sort(reverse=self.sort_reverse[col], key=lambda x: x[0])
        else:
            l.sort(reverse=self.sort_reverse[col])

        # 重新排列项目
        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)

        # 切换排序顺序
        self.sort_reverse[col] = not self.sort_reverse[col]

    def show_popup_menu(self, event):
        """显示右键菜单。"""
        # 选择被右键点击的项目
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.popup_menu.post(event.x_root, event.y_root)

    def open_in_explorer(self):
        """在文件资源管理器中打开选中文件的所在文件夹。"""
        selected_item = self.tree.selection()
        if not selected_item:
            return
        item_values = self.tree.item(selected_item[0], "values")
        filepath = item_values[1] # 路径是第二列
        folder_path = os.path.dirname(filepath)
        os.startfile(folder_path) # Windows下打开文件夹

    def delete_selected_file(self):
        """删除选中的文件。"""
        selected_item = self.tree.selection()
        if not selected_item:
            return
        item_values = self.tree.item(selected_item[0], "values")
        filepath = item_values[1]

        if messagebox.askyesno("确认删除", f"您确定要删除以下文件吗？\n\n{filepath}\n\n此操作不可逆！"):
            try:
                os.remove(filepath)
                # 从GUI中移除该项目
                self.tree.delete(selected_item[0])
                # 从内部列表中也移除
                self.current_results = [r for r in self.current_results if r["path"] != filepath]
                self.status_var.set(f"已删除文件: {filepath}")
            except OSError as e:
                messagebox.showerror("删除失败", f"无法删除文件: {e}")

    def export_results(self):
        """导出扫描结果到CSV文件。"""
        if not self.current_results:
            messagebox.showinfo("导出", "没有结果可导出。")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                    fieldnames = ["name", "path", "size_formatted", "mtime"]
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                    writer.writeheader()
                    for row in self.current_results:
                        # 写入格式化后的大小，而不是字节大小
                        writer.writerow({
                            "name": row["name"],
                            "path": row["path"],
                            "size_formatted": row["size_formatted"],
                            "mtime": row["mtime"]
                        })
                self.status_var.set(f"结果已导出到: {file_path}")
            except IOError as e:
                messagebox.showerror("导出失败", f"无法保存文件: {e}")

def run():
    root = tk.Tk()
    app = BigFileFinderGUI(root)
    root.mainloop()