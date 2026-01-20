import requests
import json
from config import Config
from database import get_db

def send_wechat_alert(message):
    """发送企业微信告警"""
    # 从数据库读取企业微信Webhook配置
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT value FROM system_config WHERE key = 'wechat_webhook'")
    result = cursor.fetchone()
    db.close()
    
    webhook_url = result['value'] if result else Config.WECHAT_WEBHOOK
    
    if not webhook_url:
        print("企业微信Webhook未配置")
        return False
    
    try:
        data = {
            "msgtype": "text",
            "text": {
                "content": message
            }
        }
        response = requests.post(webhook_url, json=data, timeout=5)
        if response.status_code == 200:
            print(f"企业微信告警发送成功: {message[:50]}...")
            return True
        else:
            print(f"企业微信告警发送失败，状态码: {response.status_code}, 响应: {response.text}")
            return False
    except Exception as e:
        print(f"发送企业微信告警失败: {e}")
        return False

def send_alert(target_id, alert_type, message):
    """记录并发送告警"""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute(
        'INSERT INTO alerts (target_id, alert_type, message) VALUES (?, ?, ?)',
        (target_id, alert_type, message)
    )
    db.commit()
    
    send_wechat_alert(f"【监控告警】\n{message}")
    
    db.close()
