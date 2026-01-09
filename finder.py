import os
import threading
from pathlib import Path
import time
from utils import get_file_size, format_bytes

class BigFileFinder:
    def __init__(self, callback_func=None):
        self.callback_func = callback_func # 用于更新GUI的回调函数
        self._stop_scan = False
        self.scan_results = []

    def scan(self, path, size_threshold_mb):
        """
        扫描指定路径下的大文件。
        :param path: 要扫描的路径 (str)
        :param size_threshold_mb: 大小阈值 (int or float)，单位MB
        """
        self._stop_scan = False
        self.scan_results = []
        size_threshold_bytes = size_threshold_mb * 1024 * 1024
        total_files_scanned = 0
        start_time = time.time()

        # 使用 Path 对象处理路径，更安全
        root_path = Path(path)

        if not root_path.exists():
            self._update_callback("error", "指定的路径不存在！")
            return

        # 使用 os.walk 进行高效遍历
        for root, dirs, files in os.walk(root_path):
            # 检查是否需要停止扫描
            if self._stop_scan:
                self._update_callback("status", "扫描已由用户停止。")
                break

            for file in files:
                # 检查是否需要停止扫描
                if self._stop_scan:
                    self._update_callback("status", "扫描已由用户停止。")
                    break

                # --- 修改这里：将文件名转换为 Path 对象 ---
                filepath = Path(root) / file
                # --- 修改这里：使用 file 作为文件名 ---
                filename = file
                # --- 或者，也可以使用 filepath.name ---
                # filename = filepath.name
                # ---

                try:
                    # 检查文件大小
                    file_size = get_file_size(filepath)
                    if file_size >= size_threshold_bytes:
                        # 将结果存储为字典，方便GUI处理
                        result = {
                            "path": str(filepath),
                            "name": filename, # 使用获取到的文件名
                            "size_bytes": file_size,
                            "size_formatted": format_bytes(file_size),
                            "mtime": time.ctime(filepath.stat().st_mtime)
                        }
                        self.scan_results.append(result)

                        # 更新GUI
                        self._update_callback("add_result", result)

                except (OSError, PermissionError):
                    # 跳过无法访问的文件，继续处理下一个
                    pass

                total_files_scanned += 1

                # 每扫描一定数量的文件，更新一次状态
                if total_files_scanned % 1000 == 0:
                    elapsed = time.time() - start_time
                    self._update_callback("status", f"已扫描 {total_files_scanned} 个文件... (用时: {elapsed:.2f}s)")

        # 扫描完成
        elapsed = time.time() - start_time
        self._update_callback("status", f"扫描完成。共扫描 {total_files_scanned} 个文件，找到 {len(self.scan_results)} 个大文件。用时: {elapsed:.2f}s")
        self._update_callback("scan_finished", self.scan_results)

    def stop(self):
        """设置停止标志，请求扫描线程停止。"""
        self._stop_scan = True

    def _update_callback(self, event_type, data):
        """内部方法，用于执行回调函数更新GUI。"""
        if self.callback_func:
            self.callback_func(event_type, data)