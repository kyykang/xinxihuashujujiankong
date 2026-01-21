#!/usr/bin/env python3
"""
快速添加用户脚本

使用方法：
    python3 add_user.py

或者直接指定参数：
    python3 add_user.py <用户名> <密码> [邮箱] [是否管理员:0/1]

示例：
    python3 add_user.py viewer viewer123           # 添加普通用户
    python3 add_user.py admin2 admin456 "" 1       # 添加管理员
"""

import sqlite3
import sys
from werkzeug.security import generate_password_hash

def add_user(username, password, email='', is_admin=0):
    """添加用户到数据库"""
    
    if len(password) < 6:
        print('错误: 密码长度至少6位')
        return False
    
    try:
        conn = sqlite3.connect('monitoring.db')
        cursor = conn.cursor()
        
        # 检查用户名是否已存在
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            print(f'错误: 用户名 "{username}" 已存在')
            conn.close()
            return False
        
        # 创建用户
        password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        cursor.execute('''
            INSERT INTO users (username, password_hash, email, is_admin)
            VALUES (?, ?, ?, ?)
        ''', (username, password_hash, email, is_admin))
        
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        
        print('=' * 60)
        print('用户添加成功！')
        print('=' * 60)
        print(f'用户ID: {user_id}')
        print(f'用户名: {username}')
        print(f'密码: {password}')
        print(f'邮箱: {email or "未设置"}')
        print(f'角色: {"管理员" if is_admin else "普通用户（只读）"}')
        print('=' * 60)
        
        if not is_admin:
            print('\n权限说明：')
            print('  ✓ 可以查看监控仪表板')
            print('  ✓ 可以查看监控目标')
            print('  ✓ 可以查看告警记录')
            print('  ✓ 可以查看系统配置')
            print('  ✓ 可以修改自己的密码')
            print('  ✗ 不能添加/编辑/删除监控目标')
            print('  ✗ 不能修改系统配置')
            print('  ✗ 不能管理用户')
        
        return True
        
    except Exception as e:
        print(f'错误: {e}')
        return False


def interactive_add_user():
    """交互式添加用户"""
    print('=' * 60)
    print('添加用户向导')
    print('=' * 60)
    
    username = input('\n请输入用户名: ').strip()
    if not username:
        print('错误: 用户名不能为空')
        return False
    
    password = input('请输入密码（至少6位）: ').strip()
    if not password:
        print('错误: 密码不能为空')
        return False
    
    email = input('请输入邮箱（可选，直接回车跳过）: ').strip()
    
    role = input('是否为管理员？(y/N): ').strip().lower()
    is_admin = 1 if role == 'y' else 0
    
    print('\n确认信息：')
    print(f'  用户名: {username}')
    print(f'  密码: {password}')
    print(f'  邮箱: {email or "未设置"}')
    print(f'  角色: {"管理员" if is_admin else "普通用户（只读）"}')
    
    confirm = input('\n确认添加？(Y/n): ').strip().lower()
    if confirm == 'n':
        print('已取消')
        return False
    
    return add_user(username, password, email, is_admin)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        # 命令行参数模式
        username = sys.argv[1]
        password = sys.argv[2] if len(sys.argv) > 2 else None
        email = sys.argv[3] if len(sys.argv) > 3 else ''
        is_admin = int(sys.argv[4]) if len(sys.argv) > 4 else 0
        
        if not password:
            print('错误: 请提供密码')
            print('使用方法: python3 add_user.py <用户名> <密码> [邮箱] [是否管理员:0/1]')
            sys.exit(1)
        
        success = add_user(username, password, email, is_admin)
        sys.exit(0 if success else 1)
    else:
        # 交互式模式
        success = interactive_add_user()
        sys.exit(0 if success else 1)
