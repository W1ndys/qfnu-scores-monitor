import json
import hashlib
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
    """获取成绩页面并提取完整成绩信息"""
    url = "http://zhjw.qfnu.edu.cn/jsxsd/kscj/cjcx_list"

    try:
        response = session.get(url, timeout=10)

        if check_session_expired(response.text):
            return None, None, True

        # 计算页面哈希
        page_hash = hashlib.sha256(response.text.encode()).hexdigest()

        soup = BeautifulSoup(response.text, 'html.parser')
        scores = []

        table = soup.find('table', {'id': 'dataList'})
        if table:
            rows = table.find_all('tr')[1:]  # 跳过表头
            for idx, row in enumerate(rows, 1):
                cols = row.find_all('td')
                if len(cols) >= 16:  # 确保有足够的列
                    score_info = {
                        '序号': str(idx),
                        '开课学期': cols[1].text.strip(),
                        '课程编号': cols[2].text.strip(),
                        '课程名称': cols[3].text.strip(),
                        '分组名': cols[4].text.strip(),
                        '成绩': cols[5].text.strip(),
                        '成绩标识': cols[6].text.strip(),
                        '学分': cols[7].text.strip(),
                        '总学时': cols[8].text.strip(),
                        '绩点': cols[9].text.strip(),
                        '补重学期': cols[10].text.strip(),
                        '考核方式': cols[11].text.strip(),
                        '考试性质': cols[12].text.strip(),
                        '课程属性': cols[13].text.strip(),
                        '课程性质': cols[14].text.strip(),
                        '课程类别': cols[15].text.strip(),
                    }
                    scores.append(score_info)

        return page_hash, scores, False

    except Exception as e:
        raise Exception(f"获取成绩失败: {str(e)}")


def compare_scores(user_account, page_hash, scores):
    """对比成绩变化，使用页面哈希判断"""
    with DatabaseManager() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT page_hash FROM scores WHERE user_account = ? ORDER BY updated_at DESC LIMIT 1", (user_account,))
        row = cursor.fetchone()

        if row:
            old_page_hash = row['page_hash']
            # 如果页面哈希不同，说明有变化
            if old_page_hash != page_hash:
                # 更新页面哈希
                cursor.execute("INSERT INTO scores (user_account, page_hash) VALUES (?, ?)", (user_account, page_hash))
                # 返回所有成绩作为新成绩
                return scores
            else:
                # 页面哈希相同，无变化
                return []
        else:
            # 首次记录，保存页面哈希
            cursor.execute("INSERT INTO scores (user_account, page_hash) VALUES (?, ?)", (user_account, page_hash))
            # 首次不通知
            return []
