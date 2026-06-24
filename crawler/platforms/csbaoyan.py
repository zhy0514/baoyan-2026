# crawler/platforms/csbaoyan.py — GitHub CS-BAOYAN 仓库聚合

import requests
import json
import re
from datetime import datetime, timezone, timedelta
from base_scraper import ScrapedProgram
from utils import random_ua

CST = timezone(timedelta(hours=8))


class CSBaoyanScraper:
    """从 GitHub jsjby/CS-BAOYAN-2026 仓库获取数据"""

    def __init__(self):
        self.name = 'csbaoyan'
        self.api_base = 'https://api.github.com/repos/jsjby/CS-BAOYAN-2026'
        self.raw_base = 'https://raw.githubusercontent.com/jsjby/CS-BAOYAN-2026/main'

    def scrape(self) -> list:
        try:
            resp = requests.get(
                f'{self.api_base}/git/trees/main?recursive=1',
                headers={'User-Agent': random_ua(), 'Accept': 'application/vnd.github+json'},
                timeout=30
            )
            if resp.status_code != 200:
                return self._fallback()
            resp.raise_for_status()
            tree = resp.json()['tree']
            results = []

            for item in tree:
                path = item['path']
                if not path.endswith('.md') and not path.endswith('.json'):
                    continue
                if 'README' in path:
                    continue
                # Try to get file content
                try:
                    content = self._fetch_file(path)
                    parsed = self._parse_md(path, content)
                    if parsed:
                        results.append(parsed)
                except Exception:
                    continue

            return results
        except Exception as e:
            print(f"CS-BAOYAN scraper error: {e}")
            return []

    def _fetch_file(self, path: str) -> str:
        url = f'{self.raw_base}/{path}'
        resp = requests.get(url, headers={'User-Agent': random_ua()}, timeout=20)
        return resp.text

    def _fallback(self) -> list:
        """Fallback: 从原始目录列表获取"""
        return []

    def _parse_md(self, path: str, content: str) -> ScrapedProgram:
        """解析 Markdown 文件内容"""
        if len(content) < 50:
            return None

        # Extract university name from path
        parts = path.split('/')
        uni = parts[0] if len(parts) > 0 else ''

        # Map repo folder names to full names
        UNI_MAP = {
            'Peking-U': '北京大学', 'Tsinghua-U': '清华大学',
            'Fudan-U': '复旦大学', 'SJTU': '上海交通大学',
            'ZJU': '浙江大学', 'NJU': '南京大学', 'USTC': '中国科学技术大学',
        }
        full_name = UNI_MAP.get(uni, uni.replace('-', ' '))

        # Extract title (first heading)
        title_match = re.search(r'^#\s+(.+)', content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else path

        # Determine type
        if '夏令营' in title or '暑期学校' in content:
            ptype = '夏令营'
        elif '预推免' in title or '推免' in content:
            ptype = '预推免'
        else:
            ptype = '未知'

        # Extract date information
        deadline = ''
        date_patterns = [
            r'报名截止.*?(\d{4})[年\-\/](\d{1,2})[月\-\/](\d{1,2})',
            r'截止时间.*?(\d{4})[年\-\/](\d{1,2})[月\-\/](\d{1,2})',
        ]
        for pat in date_patterns:
            m = re.search(pat, content)
            if m:
                g = m.groups()
                deadline = f"{int(g[0]):04d}-{int(g[1]):02d}-{int(g[2]):02d}"
                break

        # Extract majors
        majors = []
        major_kw = {
            '计算机': '计算机科学与技术', 'AI': '人工智能', '人工智能': '人工智能',
            '软件': '软件工程', '统计': '统计学', '数学': '数学',
            '网络': '网络空间安全', '数据': '数据科学',
        }
        for kw, mj in major_kw.items():
            if kw in content and mj not in majors:
                majors.append(mj)

        # Extract links
        links = re.findall(r'https?://[^\s\)]+', content)

        return ScrapedProgram(
            university=full_name,
            college='',
            program_name=title[:100],
            program_type=ptype,
            raw_majors=','.join(majors),
            application_start='',
            application_deadline=deadline,
            activity_start='',
            activity_end='',
            details_url=links[0] if links else '',
            application_url=links[1] if len(links) > 1 else '',
            raw_description=content[:500],
            source_url=f'https://github.com/jsjby/CS-BAOYAN-2026/blob/main/{path}',
            crawled_at=datetime.now(CST).isoformat(),
            contact_info={},
            requirements_text='',
            location='',
        )
