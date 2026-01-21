import requests
import json
import time
import hmac
import hashlib
import base64
from urllib.parse import quote_plus


def generate_sign(secret):
    """生成钉钉签名"""
    timestamp = str(round(time.time() * 1000))
    secret_enc = secret.encode('utf-8')
    string_to_sign = '{}\n{}'.format(timestamp, secret)
    string_to_sign_enc = string_to_sign.encode('utf-8')
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = quote_plus(base64.b64encode(hmac_code))
    return timestamp, sign


def send_dingtalk_message(webhook_url, secret, message):
    """发送钉钉消息"""
    if not webhook_url or not secret:
        return False

    timestamp, sign = generate_sign(secret)
    url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"

    headers = {'Content-Type': 'application/json'}
    data = {
        "msgtype": "text",
        "text": {
            "content": message
        }
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"发送钉钉消息失败: {str(e)}")
        return False


def notify_new_scores(webhook_url, secret, new_courses):
    """通知新成绩"""
    message = f"【成绩通知】\n检测到新成绩！\n新增课程编号: {', '.join(new_courses)}"
    return send_dingtalk_message(webhook_url, secret, message)


def notify_session_expired(webhook_url, secret):
    """通知session过期"""
    message = "【登录过期提醒】\n您的教务系统登录已过期，请重新登录以继续监控成绩。"
    return send_dingtalk_message(webhook_url, secret, message)
