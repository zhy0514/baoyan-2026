# crawler/utils.py — 工具函数：UA轮换、请求重试、日期提取

import re
import random
import time
import logging

logger = logging.getLogger(__name__)

# ====== User-Agent 轮换池 ======
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Edg/125.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0',
]

COLLEGE_MAP = {
    'cs': '计算机学院',
    'computer': '计算机学院',
    'math': '数学科学学院',
    'stat': '统计学院',
    'ai': '人工智能研究院',
    'eecs': '电子信息与电气工程学院',
    'ee': '电子信息与电气工程学院',
    'eie': '电子信息与电气工程学院',
    'seiee': '电子信息与电气工程学院',
    'ece': '信息工程学院',
    'is': '信息科学技术学院',
    'se': '软件学院',
    'software': '软件学院',
    'ds': '大数据学院',
    'data': '大数据学院',
    'cyber': '网络空间安全学院',
    'iiis': '交叉信息研究院',
    'sist': '信息科学与技术学院',
    'sci': '计算机科学与技术学院',
    'csse': '计算机科学与技术学院',
}


def random_ua():
    return random.choice(USER_AGENTS)


def random_delay(min_s=1, max_s=3):
    time.sleep(random.uniform(min_s, max_s))


def retry_with_backoff(func, *args, max_attempts=3, **kwargs):
    """指数退避重试"""
    for attempt in range(max_attempts):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"第{attempt+1}次尝试失败: {e}")
            if attempt < max_attempts - 1:
                wait = 2 ** attempt * 5
                logger.info(f"等待 {wait}s 后重试...")
                time.sleep(wait)
            else:
                raise


# ====== 日期提取 ======
# 匹配中文日期模式的优先级列表
DATE_PATTERNS = [
    # 截止时间: 2026年6月16日上午8:00
    (r'截止.*?(\d{4})\s*[年\-\/]\s*(\d{1,2})\s*[月\-\/]\s*(\d{1,2})\s*[日号]', 3),
    # 报名截止日期：2026年6月16日
    (r'[报名|申请].*?截止.*?(\d{4})\s*[年\-\/]\s*(\d{1,2})\s*[月\-\/]\s*(\d{1,2})', 3),
    # 截止日期: 2026.06.16
    (r'截止.*?(\d{4})\.(\d{1,2})\.(\d{1,2})', 3),
    # 6月16日(含)前
    (r'(\d{1,2})[月\-\/](\d{1,2})[日号].*?[前止截]', 2),
    # 即日起至6月16日
    (r'[至到].*?(\d{1,2})[月\-\/](\d{1,2})[日号]', 2),
    # 2026-06-16
    (r'(\d{4})-(\d{1,2})-(\d{1,2})', 3),
]


def extract_deadline(text: str, year=2026) -> str:
    """从文本中提取截止日期，返回 ISO 日期字符串 YYYY-MM-DD"""
    if not text:
        return ''

    for pattern, group_count in DATE_PATTERNS:
        m = re.search(pattern, text)
        if m:
            groups = m.groups()
            try:
                if group_count == 3:
                    y, mo, d = groups[0], groups[1], groups[2]
                else:
                    y, mo, d = str(year), groups[0], groups[1]
                return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
            except (ValueError, IndexError):
                continue
    return ''


def extract_activity_dates(text: str, year=2026) -> dict:
    """提取活动日期范围 {'start': '', 'end': ''}"""
    result = {'start': '', 'end': ''}

    # 2026年7月4日-6日
    m = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*[—\-~至]\s*(\d{1,2})\s*日', text)
    if m:
        g = m.groups()
        result['start'] = f"{int(g[0]):04d}-{int(g[1]):02d}-{int(g[2]):02d}"
        result['end'] = f"{int(g[0]):04d}-{int(g[1]):02d}-{int(g[3]):02d}"
        return result

    # 7月4日至7月6日
    m = re.search(r'(\d{1,2})\s*月\s*(\d{1,2})\s*日\s*[—\-~至]\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', text)
    if m:
        g = m.groups()
        result['start'] = f"{year:04d}-{int(g[0]):02d}-{int(g[1]):02d}"
        result['end'] = f"{year:04d}-{int(g[2]):02d}-{int(g[3]):02d}"
        return result

    # 单个日期: 7月4日
    m = re.search(r'(\d{1,2})\s*月\s*(\d{1,2})\s*日', text)
    if m:
        d = f"{year:04d}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
        result['start'] = d
        result['end'] = d
        return result

    return result


def extract_email(text: str) -> str:
    m = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    return m.group(0) if m else ''


def extract_phone(text: str) -> str:
    m = re.search(r'(?:电话|咨询电话|联系电话|Tel|tel)[：:\s]*([\d\-]{8,15})', text)
    return m.group(1) if m else ''


def extract_application_url(text: str) -> str:
    """尝试从正文中提取报名系统URL"""
    patterns = [
        r'(https?://[^\s"\']*?(?:apply|admission|register|yzb|zs|baoming|xly|yanzhao|yz)[^\s"\']*)',
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return ''


def normalize_url(href: str, base_url: str) -> str:
    """URL规范化：拼接相对路径"""
    from urllib.parse import urljoin
    return urljoin(base_url, href.strip())


def is_relevant(text: str) -> bool:
    """判断文本是否与夏令营/预推免相关"""
    keywords = [
        '夏令营', '预推免', '推免', '免试', '推荐免试',
        '优秀大学生', '暑期学校', '开放日', '暑期夏令营',
        '研究生招生', '接收推免', '免试攻读',
    ]
    return any(kw in text for kw in keywords)


def infer_program_type(title: str, content: str = '') -> str:
    """推断项目类型"""
    combined = f"{title} {content[:300]}"
    if any(kw in combined for kw in ['预推免', '推免', '推荐免试', '接收推免']):
        return '预推免'
    if any(kw in combined for kw in ['夏令营', '暑期学校', '暑期夏令营', '开放日']):
        return '夏令营'
    return '未知'


def infer_majors(text: str) -> list:
    """从文本中推断专业"""
    MAJOR_KEYWORDS = {
        '计算机': '计算机科学与技术',
        '软件': '软件工程',
        '人工智能': '人工智能',
        'AI': '人工智能',
        '数据科学': '数据科学',
        '大数据': '数据科学',
        '网络空间安全': '网络空间安全',
        '网络安全': '网络空间安全',
        '网安': '网络空间安全',
        '数学': '数学',
        '统计': '统计学',
        '电子信息': '电子信息',
        '控制科学': '控制科学与工程',
    }
    found = []
    for kw, major in MAJOR_KEYWORDS.items():
        if kw in text and major not in found:
            found.append(major)
    return found


def infer_college_from_url(url: str) -> str:
    """从URL推断学院"""
    url_lower = url.lower()
    for key, name in COLLEGE_MAP.items():
        if key in url_lower:
            return name
    return ''


def strip_html(text: str) -> str:
    """去除HTML标签"""
    import re as _re
    return _re.sub(r'<[^>]+>', '', text or '')


def clean_text(text: str) -> str:
    """清理文本：去除多余空白、HTML标签"""
    text = strip_html(text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()
