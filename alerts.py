import requests
import json
from config import Config
from database import get_db

def send_wechat_alert(message):
    """发送企业微信告警"""
    if not Config.WECHAT_WEBHOOK:
        print("企业微信Webhook未配置")
        return False
    
    try:
        data = {
            "msgtype": "text",
            "text": {
                "content": message
            }
        }
        response = requests.post(Config.WECHAT_WEBHOOK, json=data)
        return response.status_code == 200
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
