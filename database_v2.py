import sqlite3
from config import Config

def upgrade_db():
    """升级数据库结构，支持一个主机多个监控项"""
    conn = sqlite3.connect(Config.DATABASE)
    cursor = conn.cursor()
    
    # 创建监控主机表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monitor_hosts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            host_type TEXT NOT NULL,
            connection_config TEXT,
            enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建监控项表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monitor_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            host_id INTEGER NOT NULL,
            item_type TEXT NOT NULL,
            item_name TEXT NOT NULL,
            item_config TEXT,
            enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (host_id) REFERENCES monitor_hosts(id) ON DELETE CASCADE
        )
    ''')
    
    # 创建监控数据表（关联到监控项）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monitor_data_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            metric_type TEXT,
            metric_value TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES monitor_items(id) ON DELETE CASCADE
        )
    ''')
    
    # 创建告警记录表（关联到监控项）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts_v2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            alert_type TEXT,
            message TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES monitor_items(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()
    print("数据库升级完成！")

if __name__ == '__main__':
    upgrade_db()
