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
                    timeout=5
                )
            else:
                self.client.connect(
                    hostname=self.host,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    timeout=5
                )
            return True
        except Exception as e:
            print(f"SSH连接失败 [{self.host}]: {e}")
            return False
    
    def disconnect(self):
        """断开SSH连接"""
        if self.client:
            self.client.close()
    
    def execute_command(self, command):
        """执行远程命令"""
        try:
            stdin, stdout, stderr = self.client.exec_command(command)
            output = stdout.read().decode('utf-8').strip()
            error = stderr.read().decode('utf-8').strip()
            
            if error:
                return {'success': False, 'error': error}
            return {'success': True, 'output': output}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def check_cpu(self):
        """检查CPU使用率"""
        # 使用 top 命令获取CPU使用率
        result = self.execute_command("top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1")
        if result['success']:
            try:
                return float(result['output'])
            except:
                # 如果上面的命令不工作，尝试另一种方式
                result = self.execute_command("grep 'cpu ' /proc/stat | awk '{usage=($2+$4)*100/($2+$4+$5)} END {print usage}'")
                if result['success']:
                    return float(result['output'])
        return None
    
    def check_memory(self):
        """检查内存使用率"""
        result = self.execute_command("free | grep Mem | awk '{print ($3/$2) * 100.0}'")
        if result['success']:
            try:
                return float(result['output'])
            except:
                pass
        return None
    
    def check_disk(self, path='/'):
        """检查磁盘使用率"""
        result = self.execute_command(f"df -h {path} | tail -1 | awk '{{print $5}}' | sed 's/%//'")
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
