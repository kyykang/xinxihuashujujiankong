from datetime import datetime
import pytz
from config import Config

def utc_to_local(utc_time_str, timezone=None):
    """
    将 UTC 时间字符串转换为本地时区时间
    
    Args:
        utc_time_str: UTC 时间字符串，格式如 '2026-01-19 08:30:00'
        timezone: 目标时区，默认使用配置中的时区
    
    Returns:
        本地时区时间字符串
    """
    if not utc_time_str:
        return ''
    
    if timezone is None:
        timezone = Config.TIMEZONE
    
    try:
        # 解析 UTC 时间
        utc_time = datetime.strptime(utc_time_str, '%Y-%m-%d %H:%M:%S')
        
        # 设置为 UTC 时区
        utc_time = pytz.utc.localize(utc_time)
        
        # 转换为目标时区
        local_tz = pytz.timezone(timezone)
        local_time = utc_time.astimezone(local_tz)
        
        # 返回格式化的字符串
        return local_time.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(f"时间转换失败: {e}")
        return utc_time_str

def get_local_time(timezone=None):
    """
    获取当前本地时间
    
    Args:
        timezone: 时区，默认使用配置中的时区
    
    Returns:
        本地时间字符串
    """
    if timezone is None:
        timezone = Config.TIMEZONE
        
    local_tz = pytz.timezone(timezone)
    local_time = datetime.now(local_tz)
    return local_time.strftime('%Y-%m-%d %H:%M:%S')

def format_relative_time(time_str):
    """
    将时间转换为相对时间描述（如：5分钟前）
    
    Args:
        time_str: 时间字符串
    
    Returns:
        相对时间描述
    """
    if not time_str:
        return ''
    
    try:
        time_obj = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
        now = datetime.now()
        diff = now - time_obj
        
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return f"{int(seconds)}秒前"
        elif seconds < 3600:
            return f"{int(seconds / 60)}分钟前"
        elif seconds < 86400:
            return f"{int(seconds / 3600)}小时前"
        elif seconds < 2592000:
            return f"{int(seconds / 86400)}天前"
        else:
            return time_str
    except Exception as e:
        return time_str
