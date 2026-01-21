#!/usr/bin/env python3
"""
数据库迁移脚本：添加用户表并保留原有数据

此脚本用于将旧数据库迁移到新版本（添加用户认证功能）
"""

import sqlite3
import shutil
from werkzeug.security import generate_password_hash

def migrate_database():
    """迁移数据库"""
    
    print("=" * 60)
    print("数据库迁移工具 - 添加用户认证功能")
    print("=" * 60)
    
    old_db = 'monitoring.db.backup_before_auth'
    new_db = 'monitoring.db'
    
    # 备份当前新数据库
    print(f"\n1. 备份当前数据库...")
    try:
        shutil.copy(new_db, f'{new_db}.temp_backup')
        print(f"   已备份到: {new_db}.temp_backup")
    except:
        print("   无需备份（新数据库为空）")
    
    # 连接旧数据库
    print(f"\n2. 读取旧数据库: {old_db}")
    old_conn = sqlite3.connect(old_db)
    old_conn.row_factory = sqlite3.Row
    old_cursor = old_conn.cursor()
    
    # 连接新数据库
    new_conn = sqlite3.connect(new_db)
    new_cursor = new_conn.cursor()
    
    # 创建用户表（如果不存在）
    print("\n3. 创建用户表...")
    new_cursor.execute('''
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
    
    # 检查是否已有用户
    new_cursor.execute('SELECT COUNT(*) as count FROM users')
    user_count = new_cursor.fetchone()[0]
    
    if user_count == 0:
        # 创建默认管理员
        print("   创建默认管理员账户...")
        password_hash = generate_password_hash('admin123', method='pbkdf2:sha256')
        new_cursor.execute('''
            INSERT INTO users (username, password_hash, email, is_admin)
            VALUES (?, ?, ?, ?)
        ''', ('admin', password_hash, 'admin@example.com', 1))
        print("   ✓ 默认管理员账户已创建（admin/admin123）")
    else:
        print(f"   已存在 {user_count} 个用户，跳过创建")
    
    # 迁移监控目标
    print("\n4. 迁移监控目标...")
    old_cursor.execute('SELECT * FROM monitor_targets')
    targets = old_cursor.fetchall()
    
    migrated_count = 0
    for target in targets:
        try:
            new_cursor.execute('''
                INSERT INTO monitor_targets (id, name, type, config, enabled, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (target['id'], target['name'], target['type'], target['config'], 
                  target['enabled'], target['created_at']))
            migrated_count += 1
        except sqlite3.IntegrityError:
            # 如果ID已存在，跳过
            print(f"   跳过已存在的目标: {target['name']}")
    
    print(f"   ✓ 已迁移 {migrated_count} 个监控目标")
    
    # 迁移监控数据（最近1000条）
    print("\n5. 迁移监控数据（最近1000条）...")
    old_cursor.execute('''
        SELECT * FROM monitor_data 
        ORDER BY created_at DESC 
        LIMIT 1000
    ''')
    data_records = old_cursor.fetchall()
    
    data_count = 0
    for record in data_records:
        try:
            new_cursor.execute('''
                INSERT INTO monitor_data (target_id, metric_type, metric_value, status, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (record['target_id'], record['metric_type'], record['metric_value'],
                  record['status'], record['created_at']))
            data_count += 1
        except:
            pass
    
    print(f"   ✓ 已迁移 {data_count} 条监控数据")
    
    # 迁移告警记录（最近500条）
    print("\n6. 迁移告警记录（最近500条）...")
    old_cursor.execute('''
        SELECT * FROM alerts 
        ORDER BY created_at DESC 
        LIMIT 500
    ''')
    alerts = old_cursor.fetchall()
    
    alert_count = 0
    for alert in alerts:
        try:
            new_cursor.execute('''
                INSERT INTO alerts (target_id, alert_type, message, status, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (alert['target_id'], alert['alert_type'], alert['message'],
                  alert['status'], alert['created_at']))
            alert_count += 1
        except:
            pass
    
    print(f"   ✓ 已迁移 {alert_count} 条告警记录")
    
    # 迁移系统配置
    print("\n7. 迁移系统配置...")
    old_cursor.execute('SELECT * FROM system_config')
    configs = old_cursor.fetchall()
    
    config_count = 0
    for config in configs:
        try:
            new_cursor.execute('''
                INSERT OR REPLACE INTO system_config (key, value, updated_at)
                VALUES (?, ?, ?)
            ''', (config['key'], config['value'], config['updated_at']))
            config_count += 1
        except:
            pass
    
    print(f"   ✓ 已迁移 {config_count} 条系统配置")
    
    # 提交更改
    new_conn.commit()
    
    # 关闭连接
    old_conn.close()
    new_conn.close()
    
    print("\n" + "=" * 60)
    print("迁移完成！")
    print("=" * 60)
    print("\n数据迁移摘要：")
    print(f"  监控目标: {migrated_count} 个")
    print(f"  监控数据: {data_count} 条")
    print(f"  告警记录: {alert_count} 条")
    print(f"  系统配置: {config_count} 条")
    print("\n默认管理员账户：")
    print("  用户名: admin")
    print("  密码: admin123")
    print("\n请重启系统以使用新数据库！")
    print("=" * 60)


if __name__ == '__main__':
    try:
        migrate_database()
    except Exception as e:
        print(f"\n错误: {e}")
        print("\n迁移失败！请检查错误信息。")
