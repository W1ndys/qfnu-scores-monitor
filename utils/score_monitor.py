import json
import requests
from bs4 import BeautifulSoup
from utils.crypto import decrypt_session
from models import DatabaseManager


def restore_session(encrypted_session, encryption_key):
    """从加密数据恢复session"""
    session_data = decrypt_session(encrypted_session, encryption_key)
    session_dict = json.loads(session_data)

    session = requests.Session()
    session.cookies.update(session_dict['cookies'])
    session.headers.update(session_dict['headers'])
    return session


def serialize_session(session):
    """序列化session为JSON"""
    return json.dumps({
        'cookies': dict(session.cookies),
        'headers': dict(session.headers)
    })


def check_session_expired(response_text):
    """检测session是否过期"""
    return "请输入验证码" in response_text


def fetch_scores(session):
    """获取成绩页面并提取课程编号"""
    url = "http://zhjw.qfnu.edu.cn/jsxsd/kscj/cjcx_list"

    try:
        response = session.get(url, timeout=10)

        if check_session_expired(response.text):
            return None, True

        soup = BeautifulSoup(response.text, 'html.parser')
        course_ids = []

        table = soup.find('table', {'id': 'dataList'})
        if table:
            rows = table.find_all('tr')[1:]
            for row in rows:
                cols = row.find_all('td')
                if len(cols) > 0:
                    course_id = cols[0].text.strip()
                    if course_id:
                        course_ids.append(course_id)

        return course_ids, False

    except Exception as e:
        raise Exception(f"获取成绩失败: {str(e)}")


def compare_scores(user_hash, new_course_ids):
    """对比成绩变化"""
    with DatabaseManager() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT course_ids FROM scores WHERE user_hash = ? ORDER BY updated_at DESC LIMIT 1", (user_hash,))
        row = cursor.fetchone()

        if row:
            old_course_ids = json.loads(row['course_ids'])
            new_courses = list(set(new_course_ids) - set(old_course_ids))
        else:
            new_courses = new_course_ids

        if new_courses or not row:
            cursor.execute("INSERT INTO scores (user_hash, course_ids) VALUES (?, ?)",
                          (user_hash, json.dumps(new_course_ids)))

    return new_courses
