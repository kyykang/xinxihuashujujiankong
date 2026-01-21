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
                connect_timeout=10,  # 增加连接超时到10秒
                read_timeout=10,     # 增加读取超时
                write_timeout=10     # 增加写入超时
            )
            # 执行一个简单的查询来确认连接
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            cursor.fetchone()
            cursor.close()
            conn.close()
            return {'status': 'online'}
        except Exception as e:
            return {'status': 'offline', 'error': str(e)}
    
    @staticmethod
    def check_sqlserver(host, port, user, password, database=''):
        """检查SQL Server数据库连接"""
        try:
            import pymssql
            # 如果端口为空或0，使用默认端口1433
            if not port or port == 0:
                port = 1433
            
            conn = pymssql.connect(
                server=host,
                port=int(port),
                user=user,
                password=password,
                database=database if database else 'master',
                timeout=10,
                login_timeout=10,
                tds_version='7.0'  # 使用TDS 7.0协议，兼容性更好
            )
            # 执行一个简单的查询来确认连接
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            cursor.fetchone()
            cursor.close()
            conn.close()
            return {'status': 'online'}
        except Exception as e:
            error_msg = str(e)
            # 提供更友好的错误提示
            if '20002' in error_msg or 'connection failed' in error_msg.lower():
                error_msg = f"无法连接到SQL Server ({host}:{port})。请检查：\n1. 服务器地址和端口是否正确\n2. SQL Server是否启用了TCP/IP协议\n3. 防火墙是否允许连接\n4. SQL Server是否允许远程连接"
            return {'status': 'offline', 'error': error_msg}
    
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
    
    @staticmethod
    def query_sqlserver(host, port, user, password, database, query):
        """查询SQL Server数据库"""
        try:
            import pymssql
            # 如果端口为空或0，使用默认端口1433
            if not port or port == 0:
                port = 1433
            
            conn = pymssql.connect(
                server=host,
                port=int(port),
                user=user,
                password=password,
                database=database if database else 'master',
                timeout=10,
                login_timeout=10,
                tds_version='7.0'  # 使用TDS 7.0协议，兼容性更好
            )
            cursor = conn.cursor()
            cursor.execute(query)
            result = cursor.fetchall()
            conn.close()
            return {'status': 'success', 'data': result}
        except Exception as e:
            error_msg = str(e)
            # 提供更友好的错误提示
            if '20002' in error_msg or 'connection failed' in error_msg.lower():
                error_msg = f"无法连接到SQL Server ({host}:{port})。请检查：\n1. 服务器地址和端口是否正确（默认1433）\n2. SQL Server是否启用了TCP/IP协议\n3. 防火墙是否允许连接\n4. SQL Server是否允许远程连接"
            return {'status': 'error', 'error': error_msg}

class BusinessMonitor:
    """业务指标监控"""
    
    @staticmethod
    def check_business_metric(config):
        db_type = config.get('db_type', 'mysql').lower()
        query = config.get('query')
        threshold = config.get('threshold')
        
        # 根据数据库类型选择查询方法
        if db_type == 'sqlserver':
            result = DatabaseMonitor.query_sqlserver(
                config['host'],
                config['port'],
                config['user'],
                config['password'],
                config['database'],
                query
            )
        elif db_type == 'mysql':
            result = DatabaseMonitor.query_mysql(
                config['host'],
                config['port'],
                config['user'],
                config['password'],
                config['database'],
                query
            )
        else:
            return {'status': 'error', 'error': f'不支持的数据库类型: {db_type}'}
        
        if result['status'] == 'success':
            # 获取总行数
            row_count = len(result['data']) if result['data'] else 0
            
            # 获取第一行第一列作为数值（用于显示和阈值比较）
            value = result['data'][0][0] if result['data'] and len(result['data']) > 0 else 0
            
            # 保存所有查询结果（用于显示）
            all_data = result['data'] if result['data'] else []
            
            # 判断是否需要告警
            alert = False
            if threshold is None or threshold == 0:
                # 阈值为0或未设置：只要有数据就告警（存在模式）
                alert = row_count > 0
            else:
                # 阈值大于0：当值超过阈值时告警（阈值模式）
                if isinstance(value, (int, float)):
                    alert = value > threshold
                else:
                    # 如果第一列不是数字，则按记录数判断
                    alert = row_count > threshold
            
            # 如果触发告警，保存详细数据用于告警信息
            detail_data = None
            if alert and len(all_data) > 0:
                detail_data = all_data
            
            return {
                'value': value,
                'alert': alert,
                'detail_data': detail_data,
                'all_data': all_data,
                'row_count': row_count
            }
        
        return {'status': 'error'}

class BackupMonitor:
    """备份文件监控"""
    
    @staticmethod
    def check_backup(config):
        """检查备份文件
        
        Args:
            config: 配置字典，包含：
                - host: 服务器地址
                - port: SSH端口
                - username: 用户名
                - password: 密码
                - key_file: SSH密钥文件（可选）
                - backup_path: 备份目录路径
                - file_pattern: 文件匹配模式（可选，默认*）
                - max_age_hours: 最大文件年龄（小时），超过此时间没有新文件则告警（可选）
        
        Returns:
            dict: 检查结果
        """
        from remote_monitor import RemoteServerMonitor
        from datetime import datetime
        import time
        
        try:
            monitor = RemoteServerMonitor(
                host=config['host'],
                port=config.get('port', 22),
                username=config['username'],
                password=config.get('password'),
                key_file=config.get('key_file')
            )
            
            if not monitor.connect():
                return {
                    'status': 'error',
                    'error': '无法连接到服务器',
                    'files': [],
                    'total_count': 0,
                    'total_size': 0
                }
            
            # 获取备份文件列表
            backup_path = config.get('backup_path', '/backup')
            file_pattern = config.get('file_pattern', '*')
            
            result = monitor.check_backup_files(backup_path, file_pattern)
            monitor.disconnect()
            
            if not result['success']:
                return {
                    'status': 'error',
                    'error': result.get('error', '获取备份文件失败'),
                    'files': [],
                    'total_count': 0,
                    'total_size': 0
                }
            
            # 检查是否需要告警
            alert = False
            alert_message = ''
            
            # 检查文件数量
            if result['total_count'] == 0:
                alert = True
                alert_message = f"备份目录 {backup_path} 中没有找到匹配的备份文件"
            else:
                # 检查最新文件的年龄
                max_age_hours = config.get('max_age_hours')
                if max_age_hours and result['files']:
                    latest_file = result['files'][0]  # 文件已按时间倒序排列
                    file_age_seconds = time.time() - latest_file['mtime']
                    file_age_hours = file_age_seconds / 3600
                    
                    if file_age_hours > max_age_hours:
                        alert = True
                        alert_message = f"最新备份文件 {latest_file['name']} 已超过 {max_age_hours} 小时（实际: {file_age_hours:.1f}小时）"
            
            return {
                'status': 'normal' if not alert else 'warning',
                'alert': alert,
                'alert_message': alert_message,
                'files': result['files'][:10],  # 只保留最新的10个文件
                'total_count': result['total_count'],
                'total_size': result['total_size'],
                'total_size_human': result.get('total_size_human', '0 B'),
                'backup_path': backup_path,
                'file_pattern': file_pattern
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'files': [],
                'total_count': 0,
                'total_size': 0
            }
