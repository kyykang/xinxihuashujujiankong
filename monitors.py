import psutil
import requests
import pymysql
import json
from datetime import datetime
from database import get_db
from alerts import send_alert
from remote_monitor import RemoteServerMonitor

class ServerMonitor:
    """服务器监控"""
    
    @staticmethod
    def check_local_cpu():
        # 使用非阻塞方式获取CPU使用率（更快但可能不太准确）
        return psutil.cpu_percent(interval=0)
    
    @staticmethod
    def check_local_memory():
        mem = psutil.virtual_memory()
        return mem.percent
    
    @staticmethod
    def check_local_disk():
        disk = psutil.disk_usage('/')
        return disk.percent
    
    @staticmethod
    def check_local_network():
        net = psutil.net_io_counters()
        return {
            'bytes_sent': net.bytes_sent,
            'bytes_recv': net.bytes_recv
        }
    
    @staticmethod
    def check_local_process(process_name):
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] == process_name:
                return True
        return False
    
    @staticmethod
    def check_remote_server(config):
        """检查远程服务器"""
        try:
            monitor = RemoteServerMonitor(
                host=config['host'],
                port=config.get('port', 22),
                username=config['username'],
                password=config.get('password'),
                key_file=config.get('key_file')
            )
            
            if not monitor.connect():
                return {'status': 'offline', 'error': '无法连接到服务器'}
            
            result = {
                'status': 'online',
                'cpu': monitor.check_cpu(),
                'memory': monitor.check_memory(),
                'disk': monitor.check_disk(config.get('disk_path', '/')),
            }
            
            # 如果配置了进程监控
            if 'process_name' in config:
                result['process_running'] = monitor.check_process(config['process_name'])
            
            monitor.disconnect()
            return result
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

class StorageMonitor:
    """存储监控"""
    
    @staticmethod
    def check_storage(path='/'):
        disk = psutil.disk_usage(path)
        return {
            'total': disk.total,
            'used': disk.used,
            'free': disk.free,
            'percent': disk.percent
        }

class ApplicationMonitor:
    """应用监控"""
    
    @staticmethod
    def check_http(url, timeout=3):
        try:
            response = requests.get(url, timeout=timeout)
            return {
                'status': 'online' if response.status_code == 200 else 'error',
                'status_code': response.status_code,
                'response_time': response.elapsed.total_seconds()
            }
        except Exception as e:
            return {
                'status': 'offline',
                'error': str(e)
            }

class DatabaseMonitor:
    """数据库监控"""
    
    @staticmethod
    def check_mysql(host, port, user, password, database=''):
        try:
            conn = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                connect_timeout=3
            )
            conn.close()
            return {'status': 'online'}
        except Exception as e:
            return {'status': 'offline', 'error': str(e)}
    
    @staticmethod
    def query_mysql(host, port, user, password, database, query):
        try:
            conn = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database
            )
            cursor = conn.cursor()
            cursor.execute(query)
            result = cursor.fetchall()
            conn.close()
            return {'status': 'success', 'data': result}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

class BusinessMonitor:
    """业务指标监控"""
    
    @staticmethod
    def check_business_metric(config):
        db_type = config.get('db_type')
        query = config.get('query')
        threshold = config.get('threshold')
        
        if db_type == 'mysql':
            result = DatabaseMonitor.query_mysql(
                config['host'],
                config['port'],
                config['user'],
                config['password'],
                config['database'],
                query
            )
            if result['status'] == 'success' and result['data']:
                # 获取第一行第一列作为数值（用于阈值比较）
                value = result['data'][0][0] if result['data'] else 0
                
                # 获取总行数
                row_count = len(result['data'])
                
                # 判断是否需要告警
                alert = value > threshold if threshold and isinstance(value, (int, float)) else False
                
                # 保存所有查询结果（用于显示）
                all_data = result['data']
                
                # 如果触发告警，保存详细数据用于告警信息
                detail_data = None
                if alert and len(result['data']) > 0:
                    detail_data = result['data']
                
                return {
                    'value': value,
                    'alert': alert,
                    'detail_data': detail_data,
                    'all_data': all_data,  # 新增：保存所有数据
                    'row_count': row_count
                }
        
        return {'status': 'error'}
