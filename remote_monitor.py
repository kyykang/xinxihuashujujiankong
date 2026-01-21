import paramiko
import json

class RemoteServerMonitor:
    """远程服务器监控"""
    
    def __init__(self, host, port, username, password=None, key_file=None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_file = key_file
        self.client = None
    
    def connect(self):
        """建立SSH连接"""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if self.key_file:
                self.client.connect(
                    hostname=self.host,
                    port=self.port,
                    username=self.username,
                    key_filename=self.key_file,
                    timeout=15,  # TCP连接超时15秒
                    banner_timeout=10,  # Banner读取超时10秒
                    auth_timeout=30  # 认证超时30秒
                )
            else:
                self.client.connect(
                    hostname=self.host,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    timeout=15,  # TCP连接超时15秒
                    banner_timeout=10,  # Banner读取超时10秒
                    auth_timeout=30  # 认证超时30秒
                )
            return True
        except Exception as e:
            print(f"SSH连接失败 [{self.host}]: {e}")
            return False
    
    def disconnect(self):
        """断开SSH连接"""
        if self.client:
            self.client.close()
    
    def execute_command(self, command, timeout=5):
        """执行远程命令"""
        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
            output = stdout.read().decode('utf-8').strip()
            error = stderr.read().decode('utf-8').strip()
            
            if error:
                return {'success': False, 'error': error}
            return {'success': True, 'output': output}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def check_cpu(self):
        """检查CPU使用率 - 使用更快的命令"""
        # 直接读取/proc/stat，更快
        result = self.execute_command("awk '/^cpu /{print 100-($5*100/($2+$3+$4+$5+$6+$7+$8))}' /proc/stat", timeout=3)
        if result['success']:
            try:
                return float(result['output'])
            except:
                pass
        return None
    
    def check_memory(self):
        """检查内存使用率 - 使用更快的命令"""
        result = self.execute_command("awk '/MemTotal/{t=$2}/MemAvailable/{a=$2}END{print 100-100*a/t}' /proc/meminfo", timeout=3)
        if result['success']:
            try:
                return float(result['output'])
            except:
                pass
        return None
    
    def check_disk(self, path='/'):
        """检查磁盘使用率 - 使用更快的命令"""
        result = self.execute_command(f"df {path} | tail -1 | awk '{{print $5}}' | sed 's/%//'", timeout=3)
        if result['success']:
            try:
                return float(result['output'])
            except:
                pass
        return None
    
    def check_process(self, process_name):
        """检查进程是否运行"""
        result = self.execute_command(f"ps aux | grep '{process_name}' | grep -v grep | wc -l")
        if result['success']:
            try:
                count = int(result['output'])
                return count > 0
            except:
                pass
        return False
    
    def get_system_info(self):
        """获取系统信息"""
        info = {}
        
        # 主机名
        result = self.execute_command("hostname")
        if result['success']:
            info['hostname'] = result['output']
        
        # 操作系统
        result = self.execute_command("cat /etc/os-release | grep PRETTY_NAME | cut -d'=' -f2 | tr -d '\"'")
        if result['success']:
            info['os'] = result['output']
        
        # 内核版本
        result = self.execute_command("uname -r")
        if result['success']:
            info['kernel'] = result['output']
        
        # 运行时间
        result = self.execute_command("uptime -p")
        if result['success']:
            info['uptime'] = result['output']
        
        return info
    
    def check_backup_files(self, backup_path, file_pattern='*'):
        """检查备份文件
        
        Args:
            backup_path: 备份文件目录路径
            file_pattern: 文件匹配模式，如 *.sql, *.tar.gz, backup_*
        
        Returns:
            dict: 包含文件列表和统计信息
        """
        try:
            # 使用find命令查找文件，获取详细信息
            # 格式：文件名|大小(字节)|修改时间(时间戳)
            cmd = f"find {backup_path} -maxdepth 1 -type f -name '{file_pattern}' -printf '%f|%s|%T@\\n' 2>/dev/null | sort -t'|' -k3 -r"
            result = self.execute_command(cmd, timeout=10)
            
            if not result['success']:
                return {
                    'success': False,
                    'error': result.get('error', '执行命令失败'),
                    'files': [],
                    'total_count': 0,
                    'total_size': 0
                }
            
            files = []
            total_size = 0
            
            if result['output']:
                for line in result['output'].split('\n'):
                    if not line.strip():
                        continue
                    
                    try:
                        parts = line.split('|')
                        if len(parts) >= 3:
                            filename = parts[0]
                            size = int(parts[1])
                            mtime = float(parts[2])
                            
                            files.append({
                                'name': filename,
                                'size': size,
                                'size_human': self._format_size(size),
                                'mtime': mtime,
                                'mtime_str': self._format_timestamp(mtime)
                            })
                            total_size += size
                    except Exception as e:
                        print(f"解析文件信息失败: {line}, 错误: {e}")
                        continue
            
            return {
                'success': True,
                'files': files,
                'total_count': len(files),
                'total_size': total_size,
                'total_size_human': self._format_size(total_size)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'files': [],
                'total_count': 0,
                'total_size': 0
            }
    
    def _format_size(self, size_bytes):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
    
    def _format_timestamp(self, timestamp):
        """格式化时间戳"""
        from datetime import datetime
        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return 'N/A'
