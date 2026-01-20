import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DATABASE = 'monitoring.db'
    
    # 监控配置
    CHECK_INTERVAL = 60  # 检查间隔（秒）
    
    # 时区配置
    TIMEZONE = os.environ.get('TIMEZONE') or 'Asia/Shanghai'  # 默认中国时区
    
    # 告警阈值
    CPU_THRESHOLD = 80  # CPU使用率阈值（%）
    MEMORY_THRESHOLD = 80  # 内存使用率阈值（%）
    DISK_THRESHOLD = 80  # 磁盘使用率阈值（%）
    STORAGE_THRESHOLD = 80  # 存储使用率阈值（%）
    
    # 企业微信配置
    WECHAT_WEBHOOK = os.environ.get('WECHAT_WEBHOOK') or ''
