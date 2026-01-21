import sqlite3
from config import Config

def init_db():
    conn = sqlite3.connect(Config.DATABASE)
    cursor = conn.cursor()
    
    # 用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    # 监控目标配置表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monitor_targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            config TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 监控数据表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monitor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_id INTEGER,
            metric_type TEXT,
            metric_value TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (target_id) REFERENCES monitor_targets(id)
        )
    ''')
    
    # 告警记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_id INTEGER,
            alert_type TEXT,
            message TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (target_id) REFERENCES monitor_targets(id)
        )
    ''')
    
    # 系统配置表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_config (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 检查是否有用户，如果没有则创建默认管理员
    cursor.execute('SELECT COUNT(*) as count FROM users')
    result = cursor.fetchone()
    user_count = result[0] if result else 0
    
    if user_count == 0:
        # 创建默认管理员账户
        # 用户名: admin, 密码: admin123
        from werkzeug.security import generate_password_hash
        default_password_hash = generate_password_hash('admin123', method='pbkdf2:sha256')
        
        cursor.execute('''
            INSERT INTO users (username, password_hash, email, is_admin)
            VALUES (?, ?, ?, ?)
        ''', ('admin', default_password_hash, 'admin@example.com', 1))
        
        print("=" * 60)
        print("已创建默认管理员账户：")
        print("  用户名: admin")
        print("  密码: admin123")
        print("  请立即登录并修改密码！")
        print("=" * 60)
    
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    return conn
