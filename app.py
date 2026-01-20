from flask import Flask, render_template, request, jsonify, redirect, url_for
from database import init_db, get_db
from scheduler import start_scheduler
from config import Config
from utils import utc_to_local, format_relative_time, get_local_time
import json
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)

# 注册模板过滤器
@app.template_filter('local_time')
def local_time_filter(utc_time_str):
    """将 UTC 时间转换为本地时间"""
    return utc_to_local(utc_time_str)

@app.template_filter('relative_time')
def relative_time_filter(time_str):
    """将时间转换为相对时间"""
    return format_relative_time(time_str)

@app.template_filter('from_json')
def from_json_filter(json_str):
    """将JSON字符串转换为Python对象"""
    try:
        return json.loads(json_str) if isinstance(json_str, str) else json_str
    except:
        return {}

@app.route('/test')
def test():
    """测试页面"""
    return render_template('test.html', current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

@app.route('/test-modal')
def test_modal():
    """模态框测试页面"""
    return render_template('test_modal.html')

@app.route('/test-refresh')
def test_refresh():
    """刷新功能测试页面"""
    return render_template('test_refresh.html')

@app.route('/')
def index():
    """首页 - 监控概览"""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """监控仪表板"""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('SELECT COUNT(*) as total FROM monitor_targets WHERE enabled = 1')
    total_targets = cursor.fetchone()['total']
    
    cursor.execute('''
        SELECT COUNT(*) as count FROM monitor_data 
        WHERE status = "error" AND created_at > datetime("now", "-1 hour")
    ''')
    error_count = cursor.fetchone()['count']
    
    cursor.execute('SELECT * FROM monitor_targets WHERE enabled = 1 ORDER BY created_at DESC')
    targets = cursor.fetchall()
    
    # 获取每个目标的最新监控数据
    targets_with_data = []
    for target in targets:
        cursor.execute('''
            SELECT * FROM monitor_data 
            WHERE target_id = ? 
            ORDER BY created_at DESC 
            LIMIT 1
        ''', (target['id'],))
        latest_data = cursor.fetchone()
        
        target_dict = dict(target)
        target_dict['latest_data'] = dict(latest_data) if latest_data else None
        targets_with_data.append(target_dict)
    
    db.close()
    
    return render_template('dashboard.html', 
                         total_targets=total_targets,
                         error_count=error_count,
                         targets=targets_with_data)

@app.route('/targets')
def targets():
    """监控目标管理"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM monitor_targets ORDER BY created_at DESC')
    targets = cursor.fetchall()
    db.close()
    return render_template('targets.html', targets=targets)

@app.route('/monitor/<int:target_id>')
def monitor_detail(target_id):
    """监控详情页面"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM monitor_targets WHERE id = ?', (target_id,))
    target = cursor.fetchone()
    db.close()
    
    if not target:
        return "监控目标不存在", 404
    
    return render_template('monitor_detail.html', target=dict(target))

@app.route('/api/test-connection', methods=['POST'])
def api_test_connection():
    """测试连接"""
    data = request.json
    target_type = data.get('type')
    config = data.get('config', {})
    
    try:
        if target_type == 'server':
            # 测试服务器连接
            is_remote = config.get('is_remote', False)
            
            if is_remote:
                from remote_monitor import RemoteServerMonitor
                
                monitor = RemoteServerMonitor(
                    host=config.get('host'),
                    port=int(config.get('port', 22)),
                    username=config.get('username'),
                    password=config.get('password'),
                    key_file=config.get('key_file')
                )
                
                if not monitor.connect():
                    return jsonify({
                        'success': False,
                        'message': '无法连接到远程服务器，请检查地址、端口、用户名和密码/密钥'
                    })
                
                # 测试获取系统信息
                info = monitor.get_system_info()
                cpu = monitor.check_cpu()
                memory = monitor.check_memory()
                
                monitor.disconnect()
                
                return jsonify({
                    'success': True,
                    'message': '连接成功！',
                    'details': {
                        'hostname': info.get('hostname', 'N/A'),
                        'os': info.get('os', 'N/A'),
                        'cpu': f"{cpu:.2f}%" if cpu else 'N/A',
                        'memory': f"{memory:.2f}%" if memory else 'N/A'
                    }
                })
            else:
                # 本地服务器，直接测试
                import psutil
                cpu = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory().percent
                
                return jsonify({
                    'success': True,
                    'message': '本地服务器连接正常！',
                    'details': {
                        'cpu': f"{cpu:.2f}%",
                        'memory': f"{memory:.2f}%"
                    }
                })
        
        elif target_type == 'application':
            # 测试应用连接
            url = config.get('url')
            if not url:
                return jsonify({'success': False, 'message': 'URL 不能为空'})
            
            import requests
            response = requests.get(url, timeout=10)
            
            return jsonify({
                'success': True,
                'message': f'应用连接成功！状态码: {response.status_code}',
                'details': {
                    'status_code': response.status_code,
                    'response_time': f"{response.elapsed.total_seconds():.2f}秒"
                }
            })
        
        elif target_type == 'database':
            # 测试数据库连接
            import pymysql
            
            conn = pymysql.connect(
                host=config.get('host'),
                port=int(config.get('port', 3306)),
                user=config.get('user'),
                password=config.get('password'),
                database=config.get('database', ''),
                connect_timeout=10
            )
            
            cursor = conn.cursor()
            cursor.execute('SELECT VERSION()')
            version = cursor.fetchone()[0]
            conn.close()
            
            return jsonify({
                'success': True,
                'message': '数据库连接成功！',
                'details': {
                    'version': version
                }
            })
        
        elif target_type == 'storage':
            # 测试存储路径
            import os
            path = config.get('path', '/')
            
            if not os.path.exists(path):
                return jsonify({
                    'success': False,
                    'message': f'路径不存在: {path}'
                })
            
            import psutil
            disk = psutil.disk_usage(path)
            
            return jsonify({
                'success': True,
                'message': '存储路径有效！',
                'details': {
                    'total': f"{disk.total / (1024**3):.2f} GB",
                    'used': f"{disk.used / (1024**3):.2f} GB",
                    'free': f"{disk.free / (1024**3):.2f} GB",
                    'percent': f"{disk.percent}%"
                }
            })
        
        elif target_type == 'business':
            # 测试业务指标查询
            import pymysql
            
            conn = pymysql.connect(
                host=config.get('host'),
                port=int(config.get('port', 3306)),
                user=config.get('user'),
                password=config.get('password'),
                database=config.get('database'),
                connect_timeout=10
            )
            
            cursor = conn.cursor()
            cursor.execute(config.get('query'))
            result = cursor.fetchone()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'SQL 查询执行成功！',
                'details': {
                    'result': str(result[0]) if result else 'NULL'
                }
            })
        
        else:
            return jsonify({
                'success': False,
                'message': f'不支持的监控类型: {target_type}'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'测试失败: {str(e)}'
        })

@app.route('/api/targets', methods=['GET', 'POST'])
def api_targets():
    """监控目标API"""
    db = get_db()
    cursor = db.cursor()
    
    if request.method == 'POST':
        data = request.json
        cursor.execute(
            'INSERT INTO monitor_targets (name, type, config, enabled) VALUES (?, ?, ?, ?)',
            (data['name'], data['type'], json.dumps(data['config']), data.get('enabled', 1))
        )
        db.commit()
        target_id = cursor.lastrowid
        db.close()
        return jsonify({'success': True, 'id': target_id})
    
    cursor.execute('SELECT * FROM monitor_targets')
    targets = [dict(row) for row in cursor.fetchall()]
    db.close()
    return jsonify(targets)

@app.route('/api/targets/<int:target_id>', methods=['GET', 'PUT', 'DELETE'])
def api_target(target_id):
    """单个监控目标API"""
    db = get_db()
    cursor = db.cursor()
    
    if request.method == 'DELETE':
        cursor.execute('DELETE FROM monitor_targets WHERE id = ?', (target_id,))
        db.commit()
        db.close()
        return jsonify({'success': True})
    
    if request.method == 'PUT':
        data = request.json
        
        # 获取原有配置
        cursor.execute('SELECT config FROM monitor_targets WHERE id = ?', (target_id,))
        result = cursor.fetchone()
        if result:
            old_config = json.loads(result['config'])
            new_config = data['config']
            
            # 如果密码字段为空，保留原密码
            if 'password' in old_config and (not new_config.get('password') or new_config.get('password') == ''):
                new_config['password'] = old_config['password']
            
            # 更新数据
            cursor.execute(
                'UPDATE monitor_targets SET name = ?, type = ?, config = ?, enabled = ? WHERE id = ?',
                (data['name'], data['type'], json.dumps(new_config), data.get('enabled', 1), target_id)
            )
            db.commit()
            db.close()
            return jsonify({'success': True})
        else:
            db.close()
            return jsonify({'success': False, 'error': '监控目标不存在'})
    
    cursor.execute('SELECT * FROM monitor_targets WHERE id = ?', (target_id,))
    target = cursor.fetchone()
    db.close()
    return jsonify(dict(target) if target else {})

@app.route('/api/monitor-data/<int:target_id>')
def api_monitor_data(target_id):
    """获取监控数据"""
    db = get_db()
    cursor = db.cursor()
    
    # 获取最近的数据点数量
    limit = request.args.get('limit', 100, type=int)
    
    cursor.execute('''
        SELECT * FROM monitor_data 
        WHERE target_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
    ''', (target_id, limit))
    data = [dict(row) for row in cursor.fetchall()]
    db.close()
    
    # 转换时间为本地时区
    for item in data:
        if 'created_at' in item:
            item['created_at'] = utc_to_local(item['created_at'])
    
    # 反转顺序，使时间从旧到新
    data.reverse()
    return jsonify(data)

@app.route('/api/dashboard-stats')
def api_dashboard_stats():
    """获取仪表板统计数据"""
    db = get_db()
    cursor = db.cursor()
    
    # 获取所有启用的监控目标及其最新数据
    cursor.execute('SELECT * FROM monitor_targets WHERE enabled = 1')
    targets = cursor.fetchall()
    
    stats = {
        'servers': [],
        'applications': [],
        'databases': [],
        'business': [],
        'summary': {
            'total': len(targets),
            'online': 0,
            'offline': 0,
            'warning': 0
        }
    }
    
    for target in targets:
        cursor.execute('''
            SELECT * FROM monitor_data 
            WHERE target_id = ? 
            ORDER BY created_at DESC 
            LIMIT 1
        ''', (target['id'],))
        latest = cursor.fetchone()
        
        if latest:
            target_data = {
                'id': target['id'],
                'name': target['name'],
                'type': target['type'],
                'status': latest['status'],
                'data': latest['metric_value'],
                'time': utc_to_local(latest['created_at'])
            }
            
            if target['type'] == 'server':
                stats['servers'].append(target_data)
            elif target['type'] == 'application':
                stats['applications'].append(target_data)
            elif target['type'] == 'database':
                stats['databases'].append(target_data)
            elif target['type'] == 'business':
                stats['business'].append(target_data)
            
            # 统计状态
            if latest['status'] == 'normal':
                stats['summary']['online'] += 1
            elif latest['status'] == 'error':
                stats['summary']['offline'] += 1
            else:
                stats['summary']['warning'] += 1
    
    db.close()
    return jsonify(stats)

@app.route('/alerts')
def alerts():
    """告警记录"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT a.*, t.name as target_name 
        FROM alerts a 
        LEFT JOIN monitor_targets t ON a.target_id = t.id 
        ORDER BY a.created_at DESC 
        LIMIT 100
    ''')
    alerts = cursor.fetchall()
    db.close()
    return render_template('alerts.html', alerts=alerts)

@app.route('/config')
def config():
    """系统配置"""
    return render_template('config.html')

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """系统配置API"""
    db = get_db()
    cursor = db.cursor()
    
    if request.method == 'POST':
        data = request.json
        for key, value in data.items():
            cursor.execute(
                'INSERT OR REPLACE INTO system_config (key, value) VALUES (?, ?)',
                (key, value)
            )
        db.commit()
        db.close()
        return jsonify({'success': True})
    
    cursor.execute('SELECT * FROM system_config')
    config = {row['key']: row['value'] for row in cursor.fetchall()}
    db.close()
    return jsonify(config)

@app.route('/api/database-size')
def api_database_size():
    """获取数据库大小"""
    import os
    try:
        size_bytes = os.path.getsize(Config.DATABASE)
        
        # 转换为合适的单位
        if size_bytes < 1024:
            size_str = f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            size_str = f"{size_bytes / 1024:.2f} KB"
        else:
            size_str = f"{size_bytes / (1024 * 1024):.2f} MB"
        
        return jsonify({
            'size': size_str,
            'bytes': size_bytes
        })
    except Exception as e:
        return jsonify({
            'size': 'N/A',
            'error': str(e)
        })

@app.route('/api/clear-alerts', methods=['POST'])
def api_clear_alerts():
    """清除告警记录"""
    data = request.json
    range_type = data.get('range', 'all')
    clear_monitor_data = data.get('clear_monitor_data', False)
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        # 根据范围删除告警记录
        if range_type == 'all':
            cursor.execute('SELECT COUNT(*) as count FROM alerts')
            count_before = cursor.fetchone()['count']
            cursor.execute('DELETE FROM alerts')
        elif range_type == '7days':
            cursor.execute("SELECT COUNT(*) as count FROM alerts WHERE created_at < datetime('now', '-7 days')")
            count_before = cursor.fetchone()['count']
            cursor.execute("DELETE FROM alerts WHERE created_at < datetime('now', '-7 days')")
        elif range_type == '30days':
            cursor.execute("SELECT COUNT(*) as count FROM alerts WHERE created_at < datetime('now', '-30 days')")
            count_before = cursor.fetchone()['count']
            cursor.execute("DELETE FROM alerts WHERE created_at < datetime('now', '-30 days')")
        elif range_type == '90days':
            cursor.execute("SELECT COUNT(*) as count FROM alerts WHERE created_at < datetime('now', '-90 days')")
            count_before = cursor.fetchone()['count']
            cursor.execute("DELETE FROM alerts WHERE created_at < datetime('now', '-90 days')")
        elif range_type == 'resolved':
            cursor.execute("SELECT COUNT(*) as count FROM alerts WHERE status = 'resolved'")
            count_before = cursor.fetchone()['count']
            cursor.execute("DELETE FROM alerts WHERE status = 'resolved'")
        else:
            db.close()
            return jsonify({'success': False, 'error': '无效的清除范围'})
        
        deleted_alerts = count_before
        deleted_monitor_data = 0
        
        # 如果需要清除监控数据
        if clear_monitor_data:
            if range_type == 'all':
                cursor.execute('SELECT COUNT(*) as count FROM monitor_data')
                count_before = cursor.fetchone()['count']
                cursor.execute('DELETE FROM monitor_data')
                deleted_monitor_data = count_before
            elif range_type in ['7days', '30days', '90days']:
                days = int(range_type.replace('days', ''))
                cursor.execute(f"SELECT COUNT(*) as count FROM monitor_data WHERE created_at < datetime('now', '-{days} days')")
                count_before = cursor.fetchone()['count']
                cursor.execute(f"DELETE FROM monitor_data WHERE created_at < datetime('now', '-{days} days')")
                deleted_monitor_data = count_before
        
        db.commit()
        
        # 优化数据库（回收空间）
        cursor.execute('VACUUM')
        
        db.close()
        
        return jsonify({
            'success': True,
            'deleted_alerts': deleted_alerts,
            'deleted_monitor_data': deleted_monitor_data
        })
    
    except Exception as e:
        db.close()
        return jsonify({
            'success': False,
            'error': str(e)
        })

if __name__ == '__main__':
    init_db()
    start_scheduler()
    app.run(host='0.0.0.0', port=8080, debug=True)
