# crawler/normalizer.py — 数据规范化

import re
import hashlib
from datetime import datetime, timezone, timedelta
from base_scraper import ScrapedProgram
from utils import infer_program_type, infer_majors, infer_college_from_url, extract_deadline, extract_email, extract_phone

CST = timezone(timedelta(hours=8))

# 全称→简称映射
SHORT_NAMES = {
    '北京大学': '北大', '清华大学': '清华', '复旦大学': '复旦',
    '上海交通大学': '上海交大', '浙江大学': '浙大', '南京大学': '南大',
    '中国科学技术大学': '中科大', '哈尔滨工业大学': '哈工大',
    '西安交通大学': '西安交大', '武汉大学': '武大', '华中科技大学': '华科',
    '同济大学': '同济', '北京航空航天大学': '北航', '北京理工大学': '北理工',
    '中国人民大学': '人大', '北京师范大学': '北师大', '南开大学': '南开',
    '天津大学': '天大', '大连理工大学': '大工', '东北大学': '东大',
    '吉林大学': '吉大', '山东大学': '山大', '中国海洋大学': '中国海大',
    '厦门大学': '厦大', '东南大学': '东大', '华东师范大学': '华东师大',
    '中山大学': '中大', '华南理工大学': '华工', '四川大学': '川大',
    '电子科技大学': '成电', '重庆大学': '重大', '湖南大学': '湖大',
    '中南大学': '中南', '西北工业大学': '西工大',
    '西北农林科技大学': '西北农林', '兰州大学': '兰大',
    '国防科技大学': '国防科大', '中央民族大学': '民大', '中国农业大学': '农大',
}

# 专业标准化映射
MAJOR_MAP = {
    '计算机': '计算机科学与技术',
    '计算机科学与技术': '计算机科学与技术',
    'CS': '计算机科学与技术',
    '软件': '软件工程',
    '软件工程': '软件工程',
    '人工智能': '人工智能',
    '智能科学': '人工智能',
    '智能科学与技术': '人工智能',
    '统计学': '统计学',
    '统计': '统计学',
    '应用统计': '统计学',
    '数学': '数学',
    '应用数学': '数学',
    '计算数学': '数学',
    '基础数学': '数学',
    '网络空间安全': '网络空间安全',
    '网络安全': '网络空间安全',
    '网安': '网络空间安全',
    '数据科学': '数据科学',
    '大数据': '数据科学',
    '电子信息': '电子信息',
    '控制科学': '控制科学与工程',
    '电子与信息': '电子信息',
    '通信': '信息与通信工程',
}


class DataNormalizer:
    """将原始爬取数据转换为标准格式"""

    def __init__(self):
        self.counters = {}

    def _generate_id(self, program: ScrapedProgram) -> str:
        """生成唯一ID"""
        uni = self._short_name(program.university) or program.university
        key = f"{uni}-{program.college}-{program.program_name}-{program.program_type}"
        short = hashlib.md5(key.encode()).hexdigest()[:8]
        return f"{uni}-{program.program_type}-{short}"

    def _short_name(self, full_name: str) -> str:
        return SHORT_NAMES.get(full_name, full_name)

    def _normalize_majors(self, raw: str) -> list:
        """将原始专业字符串映射为标准名称列表"""
        if not raw:
            return []
        result = []
        for kw, standard in MAJOR_MAP.items():
            if kw in raw and standard not in result:
                result.append(standard)
        return result

    def _normalize_status(self, deadline_str: str) -> str:
        """根据截止日期推断状态"""
        if not deadline_str:
            return '待发布'
        try:
            deadline = datetime.strptime(deadline_str[:10], '%Y-%m-%d').date()
            today = datetime.now(CST).date()
            days = (deadline - today).days
            if days < 0:
                return '已截止'
            elif days <= 5:
                return '即将截止'
            else:
                return '报名中'
        except:
            return '报名中'

    def _normalize_degree_types(self, text: str) -> list:
        types = []
        if any(kw in str(text) for kw in ['硕士', '专硕', '专业学位']):
            if '专硕' in str(text) or '专业学位' in str(text):
                types.append('专硕')
            else:
                types.append('硕士')
        if any(kw in str(text) for kw in ['博士', '直博', '博士研究生', '硕博']):
            types.append('直博')
        if not types:
            types = ['硕士']  # default
        return types

    def _infer_location(self, program: ScrapedProgram) -> str:
        """根据大学推断城市/省份"""
        UNI_LOCATION = {
            '北京大学': ('北京', '北京'), '清华大学': ('北京', '北京'),
            '复旦大学': ('上海', '上海'), '上海交通大学': ('上海', '上海'),
            '浙江大学': ('杭州', '浙江'), '南京大学': ('南京', '江苏'),
            '中国科学技术大学': ('合肥', '安徽'),
            '哈尔滨工业大学': ('哈尔滨', '黑龙江'),
            '西安交通大学': ('西安', '陕西'),
            '武汉大学': ('武汉', '湖北'),
            '华中科技大学': ('武汉', '湖北'),
        }
        loc = UNI_LOCATION.get(program.university, ('', ''))
        return loc[0]

    def normalise(self, raw: ScrapedProgram) -> dict:
        """转换单个原始条目为标准格式"""
        majors = self._normalize_majors(raw.raw_majors)
        if not majors and raw.program_name:
            majors = infer_majors(raw.program_name + ' ' + (raw.raw_description or ''))

        program_type = raw.program_type or infer_program_type(raw.program_name, raw.raw_description or '')

        deadline = raw.application_deadline or extract_deadline(raw.raw_description or '')

        location = raw.location or self._infer_location(raw)
        province = location  # simplified

        degree_types = self._normalize_degree_types(
            (raw.raw_description or '') + (raw.program_name or '') + (raw.degree_types or '')
        )

        tags = list(set(majors + ([program_type] if program_type else [])))
        if self._short_name(raw.university) in ['北大', '清华']:
            tags.append('清北')
        if self._short_name(raw.university) in ['复旦', '上海交大', '浙大', '南大', '中科大']:
            tags.append('华五')

        return {
            'id': self._generate_id(raw),
            'university': raw.university,
            'university_short': self._short_name(raw.university),
            'university_type': '985',
            'college': raw.college or infer_college_from_url(raw.details_url),
            'program_name': raw.program_name or '',
            'program_type': program_type,
            'majors': majors,
            'degree_types': degree_types,
            'location': location,
            'province': province,
            'application_start': raw.application_start or '',
            'application_deadline': deadline,
            'activity_start': raw.activity_start or '',
            'activity_end': raw.activity_end or '',
            'activity_mode': self._infer_mode(raw.raw_description or ''),
            'details_url': raw.details_url or '',
            'application_url': raw.application_url or '',
            'contact_email': raw.contact_info.get('email', ''),
            'contact_phone': raw.contact_info.get('phone', ''),
            'requirements': {
                'english': self._extract_english(raw.raw_description or ''),
                'ranking': self._extract_ranking(raw.raw_description or ''),
                'notes': raw.requirements_text or '',
            },
            'description': (raw.raw_description or '')[:500],
            'source': {
                'type': 'official',
                'url': raw.source_url or raw.details_url,
                'crawled_at': raw.crawled_at or datetime.now(CST).isoformat(),
            },
            'status': self._normalize_status(deadline),
            'tags': tags,
            'is_verified': False,
        }

    def _infer_mode(self, text: str) -> str:
        online = any(kw in text for kw in ['线上', '网络', '远程', '在线', '腾讯会议', 'zoom'])
        offline = any(kw in text for kw in ['线下', '现场', '校内', '校园', '报到'])
        if online and offline:
            return '混合'
        if online:
            return '线上'
        if offline:
            return '线下'
        return ''

    def _extract_english(self, text: str) -> str:
        m = re.search(r'(?:CET[- ]?[46][：:\s]*[≥≥≧≧≥≥‌]\s*(\d{3}))', text)
        if m:
            return f"CET-{'4' if '4' in m.group(0) else '6'} ≥ {m.group(1)}"
        return ''

    def _extract_ranking(self, text: str) -> str:
        m = re.search(r'[排成]绩.*?(?:前|排名)(\d{1,2}%)', text)
        return m.group(0) if m else ''
