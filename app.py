from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from database import init_db, get_db
from scheduler import start_scheduler
from config import Config
from utils import utc_to_local, format_relative_time, get_local_time
from crypto_utils import encrypt_config, decrypt_config
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
import json
from datetime import datetime, timedelta

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY  # 用于session加密

# 登录装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('请先登录', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# 管理员权限装饰器
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('请先登录', 'warning')
            return redirect(url_for('login'))
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT is_admin FROM users WHERE id = ?', (session['user_id'],))
        user = cursor.fetchone()
        db.close()
        
        if not user or not user['is_admin']:
            flash('需要管理员权限', 'danger')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function

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

@app.route('/favicon.ico')
def favicon():
    """返回favicon"""
    # 返回一个简单的透明图标，避免404错误
    return '', 204  # 204 No Content

@app.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        
        if not username or not password:
            flash('请输入用户名和密码', 'danger')
            return render_template('login.html')
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        
        if user and check_password_hash(user['password_hash'], password):
            # 登录成功
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            
            # 设置session过期时间
            if remember:
                session.permanent = True
                app.permanent_session_lifetime = timedelta(days=30)
            else:
                session.permanent = False
            
            # 更新最后登录时间
            cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user['id'],))
            db.commit()
            db.close()
            
            flash(f'欢迎回来，{username}！', 'success')
            
            # 重定向到之前访问的页面或首页
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('index'))
        else:
            db.close()
            flash('用户名或密码错误', 'danger')
            return render_template('login.html')
    
    # GET请求，显示登录页面
    return render_template('login.html')

@app.route('/logout')
def logout():
    """用户注销"""
    username = session.get('username', '用户')
    session.clear()
    flash(f'再见，{username}！', 'info')
    return redirect(url_for('login'))

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """修改密码"""
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not all([old_password, new_password, confirm_password]):
            flash('请填写所有字段', 'danger')
            return render_template('change_password.html')
        
        if new_password != confirm_password:
            flash('两次输入的新密码不一致', 'danger')
            return render_template('change_password.html')
        
        if len(new_password) < 6:
            flash('密码长度至少6位', 'danger')
            return render_template('change_password.html')
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT password_hash FROM users WHERE id = ?', (session['user_id'],))
        user = cursor.fetchone()
        
        if not user or not check_password_hash(user['password_hash'], old_password):
            db.close()
            flash('原密码错误', 'danger')
            return render_template('change_password.html')
        
        # 更新密码
        new_password_hash = generate_password_hash(new_password, method='pbkdf2:sha256')
        cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', 
                      (new_password_hash, session['user_id']))
        db.commit()
        db.close()
        
        flash('密码修改成功，请重新登录', 'success')
        return redirect(url_for('logout'))
    
    return render_template('change_password.html')

@app.route('/test-modal')
def test_modal():
    """模态框测试页面"""
    return render_template('test_modal.html')

@app.route('/test-refresh')
def test_refresh():
    """刷新功能测试页面"""
    return render_template('test_refresh.html')

@app.route('/')
@login_required
def index():
    """首页 - 监控概览"""
    return render_template('index.html')

@app.route('/dashboard')
@login_required
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
@login_required
def targets():
    """监控目标管理"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM monitor_targets ORDER BY created_at DESC')
    targets = cursor.fetchall()
    db.close()
    return render_template('targets.html', targets=targets)

@app.route('/monitor/<int:target_id>')
@login_required
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
@login_required
def api_test_connection():
    """测试连接"""
    data = request.json
    target_type = data.get('type')
    config = data.get('config', {})
    
    # 解密配置中的敏感信息
    config = decrypt_config(config)
    
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
            from monitors import DatabaseMonitor
            
            db_type = config.get('db_type', 'mysql').lower()
            
            if db_type == 'sqlserver':
                result = DatabaseMonitor.check_sqlserver(
                    host=config.get('host'),
                    port=int(config.get('port', 1433)),
                    user=config.get('user'),
                    password=config.get('password'),
                    database=config.get('database', '')
                )
            else:  # mysql
                result = DatabaseMonitor.check_mysql(
                    host=config.get('host'),
                    port=int(config.get('port', 3306)),
                    user=config.get('user'),
                    password=config.get('password'),
                    database=config.get('database', '')
                )
            
            if result['status'] == 'online':
                return jsonify({
                    'success': True,
                    'message': f'{db_type.upper()} 数据库连接成功！'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': f'连接失败: {result.get("error", "未知错误")}'
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
            from monitors import DatabaseMonitor
            
            db_type = config.get('db_type', 'mysql').lower()
            query = config.get('query')
            
            if not query:
                return jsonify({
                    'success': False,
                    'message': 'SQL 查询语句不能为空'
                })
            
            if db_type == 'sqlserver':
                result = DatabaseMonitor.query_sqlserver(
                    host=config.get('host'),
                    port=int(config.get('port', 1433)),
                    user=config.get('user'),
                    password=config.get('password'),
                    database=config.get('database'),
                    query=query
                )
            else:  # mysql
                result = DatabaseMonitor.query_mysql(
                    host=config.get('host'),
                    port=int(config.get('port', 3306)),
                    user=config.get('user'),
                    password=config.get('password'),
                    database=config.get('database'),
                    query=query
                )
            
            if result['status'] == 'success':
                data = result['data']
                return jsonify({
                    'success': True,
                    'message': 'SQL 查询执行成功！',
                    'details': {
                        'result': str(data[0][0]) if data and len(data) > 0 else 'NULL',
                        'rows': len(data) if data else 0
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'message': f'查询失败: {result.get("error", "未知错误")}'
                })
        
        elif target_type == 'backup':
            # 测试备份文件检查
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
            
            # 测试获取备份文件列表
            backup_path = config.get('backup_path', '/backup')
            file_pattern = config.get('file_pattern', '*')
            
            result = monitor.check_backup_files(backup_path, file_pattern)
            monitor.disconnect()
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'message': f'连接成功！找到 {result["total_count"]} 个备份文件',
                    'details': {
                        'file_count': result['total_count'],
                        'total_size': result.get('total_size_human', '0 B'),
                        'latest_file': result['files'][0]['name'] if result['files'] else '无',
                        'latest_time': result['files'][0]['mtime_str'] if result['files'] else '无'
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'message': f'获取备份文件失败: {result.get("error", "未知错误")}'
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
@login_required
def api_targets():
    """监控目标API"""
    db = get_db()
    cursor = db.cursor()
    
    if request.method == 'POST':
        # 只有管理员可以添加监控目标
        if not session.get('is_admin'):
            db.close()
            return jsonify({'success': False, 'error': '需要管理员权限'})
        
        data = request.json
        
        # 加密配置中的敏感信息
        encrypted_config = encrypt_config(data['config'])
        
        cursor.execute(
            'INSERT INTO monitor_targets (name, type, config, enabled) VALUES (?, ?, ?, ?)',
            (data['name'], data['type'], json.dumps(encrypted_config), data.get('enabled', 1))
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
@login_required
def api_target(target_id):
    """单个监控目标API"""
    db = get_db()
    cursor = db.cursor()
    
    if request.method == 'DELETE':
        # 只有管理员可以删除监控目标
        if not session.get('is_admin'):
            db.close()
            return jsonify({'success': False, 'error': '需要管理员权限'})
        
        cursor.execute('DELETE FROM monitor_targets WHERE id = ?', (target_id,))
        db.commit()
        db.close()
        return jsonify({'success': True})
    
    if request.method == 'PUT':
        # 只有管理员可以编辑监控目标
        if not session.get('is_admin'):
            db.close()
            return jsonify({'success': False, 'error': '需要管理员权限'})
        
        data = request.json
        
        # 获取原有配置
        cursor.execute('SELECT config FROM monitor_targets WHERE id = ?', (target_id,))
        result = cursor.fetchone()
        if result:
            old_config_str = result['config']
            old_config = json.loads(old_config_str)
            
            # 解密旧配置
            old_config = decrypt_config(old_config)
            
            new_config = data['config']
            
            # 如果密码字段为空，保留原密码
            if 'password' in old_config and (not new_config.get('password') or new_config.get('password') == ''):
                new_config['password'] = old_config['password']
            
            # 加密新配置
            encrypted_config = encrypt_config(new_config)
            
            # 更新数据
            cursor.execute(
                'UPDATE monitor_targets SET name = ?, type = ?, config = ?, enabled = ? WHERE id = ?',
                (data['name'], data['type'], json.dumps(encrypted_config), data.get('enabled', 1), target_id)
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
@login_required
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
@login_required
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
        'backups': [],
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
            elif target['type'] == 'backup':
                stats['backups'].append(target_data)
            
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
@login_required
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

@app.route('/users')
@admin_required
def users():
    """用户管理（仅管理员）"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT id, username, email, is_admin, created_at, last_login FROM users ORDER BY created_at DESC')
    users = cursor.fetchall()
    db.close()
    return render_template('users.html', users=users)

@app.route('/config')
@login_required
def config():
    """系统配置"""
    return render_template('config.html')

@app.route('/api/users', methods=['GET', 'POST'])
@admin_required
def api_users():
    """用户管理API（仅管理员）"""
    db = get_db()
    cursor = db.cursor()
    
    if request.method == 'POST':
        data = request.json
        username = data.get('username')
        password = data.get('password')
        email = data.get('email', '')
        is_admin = data.get('is_admin', 0)
        
        if not username or not password:
            db.close()
            return jsonify({'success': False, 'error': '用户名和密码不能为空'})
        
        if len(password) < 6:
            db.close()
            return jsonify({'success': False, 'error': '密码长度至少6位'})
        
        # 检查用户名是否已存在
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            db.close()
            return jsonify({'success': False, 'error': '用户名已存在'})
        
        # 创建用户
        password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        cursor.execute('''
            INSERT INTO users (username, password_hash, email, is_admin)
            VALUES (?, ?, ?, ?)
        ''', (username, password_hash, email, is_admin))
        db.commit()
        user_id = cursor.lastrowid
        db.close()
        
        return jsonify({'success': True, 'id': user_id})
    
    # GET请求
    cursor.execute('SELECT id, username, email, is_admin, created_at, last_login FROM users')
    users = [dict(row) for row in cursor.fetchall()]
    db.close()
    return jsonify(users)

@app.route('/api/users/<int:user_id>', methods=['GET', 'PUT', 'DELETE'])
@admin_required
def api_user(user_id):
    """单个用户管理API（仅管理员）"""
    db = get_db()
    cursor = db.cursor()
    
    if request.method == 'DELETE':
        # 不能删除自己
        if user_id == session['user_id']:
            db.close()
            return jsonify({'success': False, 'error': '不能删除当前登录的用户'})
        
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        db.commit()
        db.close()
        return jsonify({'success': True})
    
    if request.method == 'PUT':
        data = request.json
        username = data.get('username')
        email = data.get('email', '')
        is_admin = data.get('is_admin', 0)
        password = data.get('password', '')
        
        if not username:
            db.close()
            return jsonify({'success': False, 'error': '用户名不能为空'})
        
        # 检查用户名是否与其他用户冲突
        cursor.execute('SELECT id FROM users WHERE username = ? AND id != ?', (username, user_id))
        if cursor.fetchone():
            db.close()
            return jsonify({'success': False, 'error': '用户名已存在'})
        
        # 更新用户信息
        if password:
            if len(password) < 6:
                db.close()
                return jsonify({'success': False, 'error': '密码长度至少6位'})
            password_hash = generate_password_hash(password, method='pbkdf2:sha256')
            cursor.execute('''
                UPDATE users SET username = ?, email = ?, is_admin = ?, password_hash = ?
                WHERE id = ?
            ''', (username, email, is_admin, password_hash, user_id))
        else:
            cursor.execute('''
                UPDATE users SET username = ?, email = ?, is_admin = ?
                WHERE id = ?
            ''', (username, email, is_admin, user_id))
        
        db.commit()
        db.close()
        return jsonify({'success': True})
    
    # GET请求
    cursor.execute('SELECT id, username, email, is_admin, created_at, last_login FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    db.close()
    return jsonify(dict(user) if user else {})

@app.route('/api/config', methods=['GET', 'POST'])
@login_required
def api_config():
    """系统配置API"""
    db = get_db()
    cursor = db.cursor()
    
    if request.method == 'POST':
        # 只有管理员可以修改配置
        if not session.get('is_admin'):
            db.close()
            return jsonify({'success': False, 'error': '需要管理员权限'})
        
        data = request.json
        need_restart = False
        
        for key, value in data.items():
            cursor.execute(
                'INSERT OR REPLACE INTO system_config (key, value) VALUES (?, ?)',
                (key, value)
            )
            # 如果修改了检查间隔，需要重启系统
            if key == 'check_interval':
                need_restart = True
        
        db.commit()
        db.close()
        
        return jsonify({
            'success': True,
            'need_restart': need_restart,
            'message': '配置已保存' + ('，请重启系统使检查间隔生效' if need_restart else '')
        })
    
    cursor.execute('SELECT * FROM system_config')
    config = {row['key']: row['value'] for row in cursor.fetchall()}
    db.close()
    return jsonify(config)

@app.route('/api/database-size')
@login_required
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
@login_required
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
    import os
    init_db()
    
    # 只在主进程中启动调度器（避免debug模式下重复启动）
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        start_scheduler()
    
    app.run(host='0.0.0.0', port=8080, debug=True)
