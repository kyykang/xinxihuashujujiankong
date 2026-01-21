#!/usr/bin/env python3
"""
数据库密码加密迁移脚本

此脚本用于将现有数据库中的明文密码加密存储
运行此脚本前请先备份数据库！

使用方法:
    python3 migrate_encrypt_passwords.py
"""

import sqlite3
import json
from crypto_utils import encrypt_config, decrypt_config, get_crypto_manager

def migrate_database(db_path='monitoring.db'):
    """迁移数据库，加密所有密码"""
    
    print("=" * 60)
    print("数据库密码加密迁移工具")
    print("=" * 60)
    print(f"\n数据库路径: {db_path}")
    print("\n警告：此操作将修改数据库中的所有密码字段！")
    print("请确保已备份数据库文件！\n")
    
    response = input("是否继续？(yes/no): ")
    if response.lower() != 'yes':
        print("操作已取消")
        return
    
    # 初始化加密管理器
    crypto_manager = get_crypto_manager()
    print(f"\n加密密钥已加载")
    
    # 连接数据库
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 获取所有监控目标
    cursor.execute('SELECT id, name, type, config FROM monitor_targets')
    targets = cursor.fetchall()
    
    print(f"\n找到 {len(targets)} 个监控目标")
    
    encrypted_count = 0
    skipped_count = 0
    error_count = 0
    
    for target in targets:
        target_id = target['id']
        target_name = target['name']
        target_type = target['type']
        config_str = target['config']
        
        try:
            # 解析配置
            config = json.loads(config_str)
            
            # 检查是否有需要加密的字段
            has_sensitive = False
            sensitive_fields = ['password', 'key_file']
            
            for field in sensitive_fields:
                if field in config and config[field]:
                    # 检查是否已加密
                    if not crypto_manager.is_encrypted(str(config[field])):
                        has_sensitive = True
                        break
            
            if not has_sensitive:
                print(f"  [{target_id}] {target_name} - 已加密或无敏感信息，跳过")
                skipped_count += 1
                continue
            
            # 加密配置
            encrypted_config = encrypt_config(config)
            
            # 更新数据库
            cursor.execute(
                'UPDATE monitor_targets SET config = ? WHERE id = ?',
                (json.dumps(encrypted_config), target_id)
            )
            
            print(f"  [{target_id}] {target_name} ({target_type}) - 已加密")
            encrypted_count += 1
            
        except Exception as e:
            print(f"  [{target_id}] {target_name} - 错误: {e}")
            error_count += 1
    
    # 提交更改
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 60)
    print("迁移完成！")
    print(f"  已加密: {encrypted_count} 个")
    print(f"  已跳过: {skipped_count} 个")
    print(f"  错误: {error_count} 个")
    print("=" * 60)
    
    if encrypted_count > 0:
        print("\n重要提示：")
        print("1. 密钥文件 .secret_key 已生成，请妥善保管")
        print("2. 丢失密钥文件将无法解密数据")
        print("3. 建议将密钥文件备份到安全位置")
        print("4. 不要将密钥文件提交到Git仓库")


def verify_encryption(db_path='monitoring.db'):
    """验证加密是否成功"""
    
    print("\n" + "=" * 60)
    print("验证加密结果")
    print("=" * 60)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, name, type, config FROM monitor_targets')
    targets = cursor.fetchall()
    
    crypto_manager = get_crypto_manager()
    
    for target in targets:
        target_id = target['id']
        target_name = target['name']
        config_str = target['config']
        
        try:
            config = json.loads(config_str)
            
            # 尝试解密
            decrypted_config = decrypt_config(config)
            
            # 检查是否有密码字段
            if 'password' in decrypted_config and decrypted_config['password']:
                is_encrypted = crypto_manager.is_encrypted(config.get('password', ''))
                status = "✓ 已加密" if is_encrypted else "✗ 未加密"
                print(f"  [{target_id}] {target_name} - {status}")
            else:
                print(f"  [{target_id}] {target_name} - 无密码字段")
                
        except Exception as e:
            print(f"  [{target_id}] {target_name} - 验证失败: {e}")
    
    conn.close()
    print("=" * 60)


if __name__ == '__main__':
    import sys
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == 'verify':
            verify_encryption()
        elif sys.argv[1] == 'help':
            print(__doc__)
        else:
            print(f"未知命令: {sys.argv[1]}")
            print("使用 'python3 migrate_encrypt_passwords.py help' 查看帮助")
    else:
        # 执行迁移
        migrate_database()
        
        # 验证结果
        print("\n")
        verify_encryption()
