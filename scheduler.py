from apscheduler.schedulers.background import BackgroundScheduler
from monitors import ServerMonitor, StorageMonitor, ApplicationMonitor, DatabaseMonitor, BusinessMonitor, BackupMonitor
from database import get_db
from alerts import send_alert
from config import Config
from crypto_utils import decrypt_config
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

scheduler = BackgroundScheduler()
executor = ThreadPoolExecutor(max_workers=10)  # 最多10个并发任务

def run_monitors():
    """执行所有监控任务（并行）"""
    start_time = time.time()
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT * FROM monitor_targets WHERE enabled = 1')
    targets = cursor.fetchall()
    db.close()
    
    if not targets:
        return
    
    # 使用线程池并行执行监控任务
    futures = []
    for target in targets:
        future = executor.submit(run_single_monitor, dict(target))
        futures.append(future)
    
    # 等待所有任务完成
    completed = 0
    failed = 0
    for future in as_completed(futures):
        try:
            result = future.result()
            if result:
                completed += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            print(f"监控任务异常: {e}")
    
    elapsed = time.time() - start_time
    print(f"监控任务完成: {completed} 成功, {failed} 失败, 耗时 {elapsed:.2f}秒")

def run_single_monitor(target):
    """执行单个监控任务"""
    import time
    start_time = time.time()
    
    target_id = target['id']
    target_type = target['type']
    target_name = target['name']
    
    try:
        config = json.loads(target['config'])
        
        # 解密配置中的敏感信息
        config = decrypt_config(config)
        
        elapsed = 0
        
        if target_type == 'server':
            elapsed = check_server(target_id, config)
        elif target_type == 'storage':
            elapsed = check_storage(target_id, config)
        elif target_type == 'application':
            elapsed = check_application(target_id, config)
        elif target_type == 'database':
            elapsed = check_database(target_id, config)
        elif target_type == 'business':
            elapsed = check_business(target_id, config)
        elif target_type == 'backup':
            elapsed = check_backup(target_id, config)
        
        if elapsed == 0:
            elapsed = time.time() - start_time
        print(f"  [{target_name}] 完成，耗时 {elapsed:.2f}秒")
        return True
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"  [{target_name}] 失败，耗时 {elapsed:.2f}秒: {e}")
        return False

def check_server(target_id, config):
    """检查服务器"""
    import time
    start_time = time.time()
    
    # 判断是本地还是远程服务器
    is_remote = config.get('is_remote', False)
    
    if is_remote:
        # 远程服务器监控
        result = ServerMonitor.check_remote_server(config)
        
        if result['status'] == 'offline' or result['status'] == 'error':
            elapsed = time.time() - start_time
            result['execution_time'] = round(elapsed, 2)
            
            db = get_db()
            cursor = db.cursor()
            cursor.execute(
                'INSERT INTO monitor_data (target_id, metric_type, metric_value, status) VALUES (?, ?, ?, ?)',
                (target_id, 'server', json.dumps(result), 'error')
            )
            db.commit()
            send_alert(target_id, 'server', f"远程服务器连接失败: {config['host']}")
            db.close()
            return elapsed
        
        cpu = result.get('cpu')
        memory = result.get('memory')
        disk = result.get('disk')
    else:
        # 本地服务器监控
        cpu = ServerMonitor.check_local_cpu()
        memory = ServerMonitor.check_local_memory()
        disk = ServerMonitor.check_local_disk()
    
    elapsed = time.time() - start_time
    
    db = get_db()
    cursor = db.cursor()
    
    metrics = {
        'cpu': cpu,
        'memory': memory,
        'disk': disk,
        'execution_time': round(elapsed, 2)
    }
    
    cursor.execute(
        'INSERT INTO monitor_data (target_id, metric_type, metric_value, status) VALUES (?, ?, ?, ?)',
        (target_id, 'server', json.dumps(metrics), 'normal')
    )
    db.commit()
    
    if cpu and cpu > Config.CPU_THRESHOLD:
        send_alert(target_id, 'cpu', f"CPU使用率过高: {cpu}%")
    if memory and memory > Config.MEMORY_THRESHOLD:
        send_alert(target_id, 'memory', f"内存使用率过高: {memory}%")
    if disk and disk > Config.DISK_THRESHOLD:
        send_alert(target_id, 'disk', f"磁盘使用率过高: {disk}%")
    
    db.close()
    return elapsed

def check_storage(target_id, config):
    """检查存储"""
    import time
    start_time = time.time()
    
    path = config.get('path', '/')
    storage = StorageMonitor.check_storage(path)
    
    elapsed = time.time() - start_time
    storage['execution_time'] = round(elapsed, 2)
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute(
        'INSERT INTO monitor_data (target_id, metric_type, metric_value, status) VALUES (?, ?, ?, ?)',
        (target_id, 'storage', json.dumps(storage), 'normal')
    )
    db.commit()
    
    if storage['percent'] > Config.STORAGE_THRESHOLD:
        send_alert(target_id, 'storage', f"存储使用率过高: {storage['percent']}%")
    
    db.close()
    return elapsed

def check_application(target_id, config):
    """检查应用"""
    import time
    start_time = time.time()
    
    url = config.get('url')
    result = ApplicationMonitor.check_http(url)
    
    elapsed = time.time() - start_time
    result['execution_time'] = round(elapsed, 2)
    
    db = get_db()
    cursor = db.cursor()
    
    status = 'normal' if result['status'] == 'online' else 'error'
    
    cursor.execute(
        'INSERT INTO monitor_data (target_id, metric_type, metric_value, status) VALUES (?, ?, ?, ?)',
        (target_id, 'application', json.dumps(result), status)
    )
    db.commit()
    
    if result['status'] != 'online':
        send_alert(target_id, 'application', f"应用服务异常: {url}")
    
    db.close()
    return elapsed

def check_database(target_id, config):
    """检查数据库"""
    import time
    start_time = time.time()
    
    # 获取数据库类型，默认为mysql
    db_type = config.get('db_type', 'mysql').lower()
    
    if db_type == 'sqlserver':
        result = DatabaseMonitor.check_sqlserver(
            config['host'],
            config['port'],
            config['user'],
            config['password'],
            config.get('database', '')
        )
    else:  # mysql
        result = DatabaseMonitor.check_mysql(
            config['host'],
            config['port'],
            config['user'],
            config['password'],
            config.get('database', '')
        )
    
    elapsed = time.time() - start_time
    result['execution_time'] = round(elapsed, 2)
    
    db = get_db()
    cursor = db.cursor()
    
    status = 'normal' if result['status'] == 'online' else 'error'
    
    cursor.execute(
        'INSERT INTO monitor_data (target_id, metric_type, metric_value, status) VALUES (?, ?, ?, ?)',
        (target_id, 'database', json.dumps(result), status)
    )
    db.commit()
    
    if result['status'] != 'online':
        send_alert(target_id, 'database', f"数据库连接失败: {config['host']}")
    
    db.close()
    return elapsed

def check_business(target_id, config):
    """检查业务指标"""
    import time
    start_time = time.time()
    
    result = BusinessMonitor.check_business_metric(config)
    
    elapsed = time.time() - start_time
    result['execution_time'] = round(elapsed, 2)
    
    db = get_db()
    cursor = db.cursor()
    
    status = 'normal' if not result.get('alert') else 'warning'
    
    cursor.execute(
        'INSERT INTO monitor_data (target_id, metric_type, metric_value, status) VALUES (?, ?, ?, ?)',
        (target_id, 'business', json.dumps(result), status)
    )
    db.commit()
    
    if result.get('alert'):
        # 构建详细的告警信息
        alert_message = f"业务指标异常: {result.get('value')}"
        
        # 如果有详细数据，添加到告警信息中
        if result.get('detail_data'):
            detail_data = result.get('detail_data')
            row_count = result.get('row_count', 0)
            
            # 限制显示的行数，避免信息过长
            max_display_rows = 10
            display_rows = min(row_count, max_display_rows)
            
            alert_message += f" (共{row_count}条记录"
            if row_count > max_display_rows:
                alert_message += f"，显示前{max_display_rows}条"
            alert_message += ")\n"
            
            # 添加详细数据
            for i, row in enumerate(detail_data[:max_display_rows]):
                # 将元组转换为字符串
                row_str = ', '.join(str(item) for item in row)
                alert_message += f"  [{i+1}] {row_str}\n"
            
            if row_count > max_display_rows:
                alert_message += f"  ... 还有 {row_count - max_display_rows} 条记录"
        
        send_alert(target_id, 'business', alert_message)
    
    db.close()
    return elapsed

def check_backup(target_id, config):
    """检查备份文件"""
    import time
    start_time = time.time()
    
    result = BackupMonitor.check_backup(config)
    
    elapsed = time.time() - start_time
    result['execution_time'] = round(elapsed, 2)
    
    db = get_db()
    cursor = db.cursor()
    
    status = result.get('status', 'error')
    
    cursor.execute(
        'INSERT INTO monitor_data (target_id, metric_type, metric_value, status) VALUES (?, ?, ?, ?)',
        (target_id, 'backup', json.dumps(result), status)
    )
    db.commit()
    
    if result.get('alert'):
        alert_message = result.get('alert_message', '备份文件检查异常')
        send_alert(target_id, 'backup', alert_message)
    elif result.get('status') == 'error':
        send_alert(target_id, 'backup', f"备份检查失败: {result.get('error', '未知错误')}")
    
    db.close()
    return elapsed

def start_scheduler():
    """启动调度器"""
    # 从数据库读取检查间隔配置
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT value FROM system_config WHERE key = 'check_interval'")
    result = cursor.fetchone()
    db.close()
    
    # 使用数据库配置，如果没有则使用默认值
    check_interval = int(result['value']) if result else Config.CHECK_INTERVAL
    
    print(f"启动监控调度器，检查间隔: {check_interval}秒")
    scheduler.add_job(run_monitors, 'interval', seconds=check_interval)
    scheduler.start()



def trigger_manual_check():
    """手动触发一次监控检查
    
    Returns:
        dict: 包含执行结果的字典
    """
    import time
    start_time = time.time()
    
    print("手动触发监控检查...")
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT * FROM monitor_targets WHERE enabled = 1')
    targets = cursor.fetchall()
    db.close()
    
    if not targets:
        return {
            'success': True,
            'message': '没有启用的监控目标',
            'completed': 0,
            'failed': 0,
            'elapsed': 0
        }
    
    # 使用线程池并行执行监控任务
    futures = []
    for target in targets:
        future = executor.submit(run_single_monitor, dict(target))
        futures.append(future)
    
    # 等待所有任务完成
    completed = 0
    failed = 0
    for future in as_completed(futures):
        try:
            result = future.result()
            if result:
                completed += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            print(f"监控任务异常: {e}")
    
    elapsed = time.time() - start_time
    print(f"手动监控完成: {completed} 成功, {failed} 失败, 耗时 {elapsed:.2f}秒")
    
    return {
        'success': True,
        'message': f'监控检查完成',
        'completed': completed,
        'failed': failed,
        'total': len(targets),
        'elapsed': round(elapsed, 2)
    }
