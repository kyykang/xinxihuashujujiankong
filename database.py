import sqlite3
from config import Config

def init_db():
    conn = sqlite3.connect(Config.DATABASE)
    cursor = conn.cursor()
    
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
    
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    return conn
