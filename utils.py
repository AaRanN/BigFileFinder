import os

def format_bytes(bytes_value):
    """
    将字节数转换为更易读的格式 (B, KB, MB, GB)
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} TB"

def get_file_size(filepath):
    """
    安全地获取文件大小，处理可能的异常。
    """
    try:
        return os.path.getsize(filepath)
    except (OSError, FileNotFoundError):
        # 如果文件不存在或无法访问，返回0或抛出异常
        # 这里选择返回0，让上层逻辑决定如何处理
        return 0