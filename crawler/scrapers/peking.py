# crawler/scrapers/peking.py — 北京大学

import re
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from base_scraper import BaseScraper, ScrapedProgram
from utils import (
    normalize_url, is_relevant, extract_deadline,
    extract_activity_dates, extract_email, extract_phone,
    extract_application_url, infer_majors, infer_program_type,
    clean_text, random_delay,
)

CST = timezone(timedelta(hours=8))


class PekingScraper(BaseScraper):
    """北京大学 — 多学院爬虫"""

    def __init__(self):
        super().__init__()
        self.name = 'peking'
        self.university_name = '北京大学'
        self.university_short = '北大'

    def get_list_page_urls(self) -> list:
        return [
            # 计算机学院 通知公告
            'https://cs.pku.edu.cn/tzgg.htm',
            # 信息工程学院（深圳）
            'https://www.ece.pku.edu.cn/zsxx.htm',
            # 数学科学学院
            'https://www.math.pku.edu.cn/xwgg/tzgg.htm',
            # 研究生招生网
            'https://admission.pku.edu.cn/zsxx/sszs/index.htm',
            # 信息科学技术学院
            'https://eecs.pku.edu.cn/announcements.htm',
            # 智能学院
            'https://www.ai.pku.edu.cn/tzgg.htm',
            # 统计科学中心
            'https://www.stat-center.pku.edu.cn/xwgg/tzgg.htm',
            # 软件与微电子学院
            'https://www.ss.pku.edu.cn/index.php/admission/admnotice',
        ]

    def parse_list_page(self, html: str) -> list:
        soup = BeautifulSoup(html, 'lxml')
        urls = []

        for a in soup.select('a[href]'):
            text = a.get_text(strip=True)
            href = a.get('href', '')

            if not text or len(text) < 5:
                continue
            if not is_relevant(text):
                continue
            if href.startswith('#') or href.startswith('javascript'):
                continue

            # collect base domain for URL normalization
            full = normalize_url(href, "https://cs.pku.edu.cn")
            if full not in urls:
                urls.append(full)

        return urls

    def parse_detail_page(self, html: str, url: str) -> ScrapedProgram:
        soup = BeautifulSoup(html, 'lxml')

        # title
        title = ''
        for sel in ['h1', '.news-title', '.article-title', 'title', '.bt', '.tit', '.wzbt']:
            el = soup.select_one(sel)
            if el:
                title = clean_text(el.get_text())
                break

        # content block
        content_el = None
        for sel in ['.article-content', '.news-content', '.content', '#vsb_content',
                     '.v_news_content', '.main-content', 'article', '.TRS_Editor',
                     '.wznr', '.con']:
            content_el = soup.select_one(sel)
            if content_el:
                break
        if not content_el:
            content_el = soup.find('body')

        content = clean_text(content_el.get_text()) if content_el else ''

        deadline = extract_deadline(content)
        activity_dates = extract_activity_dates(content)
        email = extract_email(content)
        phone = extract_phone(content)
        apply_url = extract_application_url(content)

        # infer college from url
        college = self._infer_college(url, title)

        program_type = infer_program_type(title, content)
        majors = infer_majors(title + ' ' + content[:500])

        return ScrapedProgram(
            university=self.university_name,
            college=college,
            program_name=title,
            program_type=program_type,
            raw_majors=','.join(majors),
            application_deadline=deadline,
            activity_start=activity_dates.get('start', ''),
            activity_end=activity_dates.get('end', ''),
            details_url=url,
            application_url=apply_url,
            raw_description=content[:800],
            source_url=url,
            crawled_at=datetime.now(CST).isoformat(),
            contact_info={'email': email, 'phone': phone},
            requirements_text=self._extract_requirements(content),
            location='北京',
        )

    def _infer_college(self, url: str, title: str) -> str:
        url_lower = url.lower()
        if any(k in url_lower for k in ['cs.pku', 'cs/', 'computer']):
            return '计算机学院'
        if any(k in url_lower for k in ['math', '数学']):
            return '数学科学学院'
        if any(k in url_lower for k in ['ai.pku', '智能', 'ai/']):
            return '人工智能研究院'
        if any(k in url_lower for k in ['eecs', '信息科学']):
            return '信息科学技术学院'
        if any(k in url_lower for k in ['ece', '信息工程']):
            return '信息工程学院（深圳）'
        if any(k in url_lower for k in ['stat', '统计']):
            return '统计科学中心'
        if any(k in url_lower for k in ['ss.pku', '软件', '软微']):
            return '软件与微电子学院'
        if any(k in url_lower for k in ['admission', '招生']):
            return '研究生院'
        return '未知学院'

    def _extract_requirements(self, text: str) -> str:
        m = re.search(
            r'(?:申请条件|报名条件|招收对象|申请资格|基本条件)[：:\s]*\n?(.*?)(?:\n\n|\n[#一二三四五六七八九十（(])',
            text, re.DOTALL
        )
        return m.group(1).strip()[:400] if m else ''
