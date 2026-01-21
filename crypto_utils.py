"""
密码加密工具模块
使用AES加密算法对敏感信息进行加密存储
"""

from cryptography.fernet import Fernet
import os
import base64

class CryptoManager:
    """加密管理器"""
    
    def __init__(self, key_file='.secret_key'):
        """初始化加密管理器
        
        Args:
            key_file: 密钥文件路径
        """
        self.key_file = key_file
        self.cipher = None
        self._load_or_create_key()
    
    def _load_or_create_key(self):
        """加载或创建加密密钥"""
        if os.path.exists(self.key_file):
            # 加载现有密钥
            with open(self.key_file, 'rb') as f:
                key = f.read()
            self.cipher = Fernet(key)
            print(f"已加载加密密钥: {self.key_file}")
        else:
            # 生成新密钥
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            # 设置文件权限为只有所有者可读写
            os.chmod(self.key_file, 0o600)
            self.cipher = Fernet(key)
            print(f"已生成新的加密密钥: {self.key_file}")
            print("警告：请妥善保管密钥文件，丢失将无法解密已加密的数据！")
    
    def encrypt(self, plaintext):
        """加密文本
        
        Args:
            plaintext: 明文字符串
            
        Returns:
            str: 加密后的Base64编码字符串
        """
        if not plaintext:
            return ''
        
        try:
            # 将字符串转换为字节
            plaintext_bytes = plaintext.encode('utf-8')
            # 加密
            encrypted_bytes = self.cipher.encrypt(plaintext_bytes)
            # 转换为Base64字符串以便存储
            encrypted_str = base64.b64encode(encrypted_bytes).decode('utf-8')
            return encrypted_str
        except Exception as e:
            print(f"加密失败: {e}")
            return plaintext  # 加密失败时返回原文（向后兼容）
    
    def decrypt(self, encrypted_text):
        """解密文本
        
        Args:
            encrypted_text: 加密的Base64编码字符串
            
        Returns:
            str: 解密后的明文字符串
        """
        if not encrypted_text:
            return ''
        
        try:
            # 从Base64字符串转换为字节
            encrypted_bytes = base64.b64decode(encrypted_text.encode('utf-8'))
            # 解密
            decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
            # 转换为字符串
            decrypted_str = decrypted_bytes.decode('utf-8')
            return decrypted_str
        except Exception as e:
            # 解密失败，可能是未加密的旧数据
            print(f"解密失败（可能是未加密的数据）: {e}")
            return encrypted_text  # 返回原文（向后兼容）
    
    def is_encrypted(self, text):
        """检查文本是否已加密
        
        Args:
            text: 待检查的文本
            
        Returns:
            bool: 是否已加密
        """
        if not text:
            return False
        
        try:
            # 尝试Base64解码
            base64.b64decode(text.encode('utf-8'))
            # 尝试解密
            self.decrypt(text)
            return True
        except:
            return False


# 全局加密管理器实例
_crypto_manager = None

def get_crypto_manager():
    """获取全局加密管理器实例"""
    global _crypto_manager
    if _crypto_manager is None:
        _crypto_manager = CryptoManager()
    return _crypto_manager


def encrypt_password(password):
    """加密密码的便捷函数"""
    if not password:
        return ''
    manager = get_crypto_manager()
    return manager.encrypt(password)


def decrypt_password(encrypted_password):
    """解密密码的便捷函数"""
    if not encrypted_password:
        return ''
    manager = get_crypto_manager()
    return manager.decrypt(encrypted_password)


def encrypt_config(config):
    """加密配置中的敏感字段
    
    Args:
        config: 配置字典
        
    Returns:
        dict: 加密后的配置字典
    """
    if not isinstance(config, dict):
        return config
    
    # 需要加密的字段列表
    sensitive_fields = ['password', 'key_file']
    
    encrypted_config = config.copy()
    manager = get_crypto_manager()
    
    for field in sensitive_fields:
        if field in encrypted_config and encrypted_config[field]:
            # 检查是否已加密
            if not manager.is_encrypted(str(encrypted_config[field])):
                encrypted_config[field] = manager.encrypt(str(encrypted_config[field]))
    
    return encrypted_config


def decrypt_config(config):
    """解密配置中的敏感字段
    
    Args:
        config: 配置字典
        
    Returns:
        dict: 解密后的配置字典
    """
    if not isinstance(config, dict):
        return config
    
    # 需要解密的字段列表
    sensitive_fields = ['password', 'key_file']
    
    decrypted_config = config.copy()
    manager = get_crypto_manager()
    
    for field in sensitive_fields:
        if field in decrypted_config and decrypted_config[field]:
            decrypted_config[field] = manager.decrypt(str(decrypted_config[field]))
    
    return decrypted_config


if __name__ == '__main__':
    # 测试加密功能
    manager = CryptoManager()
    
    # 测试密码加密
    password = "MySecretPassword123!"
    print(f"\n原始密码: {password}")
    
    encrypted = manager.encrypt(password)
    print(f"加密后: {encrypted}")
    
    decrypted = manager.decrypt(encrypted)
    print(f"解密后: {decrypted}")
    
    print(f"\n加密解密是否一致: {password == decrypted}")
    
    # 测试配置加密
    config = {
        'host': '192.168.1.100',
        'username': 'admin',
        'password': 'secret123',
        'port': 22
    }
    
    print(f"\n原始配置: {config}")
    
    encrypted_config = encrypt_config(config)
    print(f"加密后配置: {encrypted_config}")
    
    decrypted_config = decrypt_config(encrypted_config)
    print(f"解密后配置: {decrypted_config}")
