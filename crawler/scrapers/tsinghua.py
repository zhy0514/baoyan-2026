# crawler/scrapers/tsinghua.py — 清华大学

from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from base_scraper import BaseScraper, ScrapedProgram
from utils import (
    normalize_url, is_relevant, extract_deadline,
    extract_activity_dates, extract_email, extract_phone,
    extract_application_url, infer_majors, infer_program_type,
    clean_text,
)

CST = timezone(timedelta(hours=8))


class TsinghuaScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = 'tsinghua'
        self.university_name = '清华大学'
        self.university_short = '清华'

    def get_list_page_urls(self) -> list:
        return [
            # 交叉信息研究院
            'https://iiis.tsinghua.edu.cn/',
            # 计算机科学与技术系
            'https://www.cs.tsinghua.edu.cn/',
            # 人工智能学院
            'https://www.sz.tsinghua.edu.cn/',
            # 研究生招生网
            'https://yz.tsinghua.edu.cn/',
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
            full = normalize_url(href, 'https://www.tsinghua.edu.cn')
            if full not in urls:
                urls.append(full)
        return urls

    def parse_detail_page(self, html: str, url: str) -> ScrapedProgram:
        soup = BeautifulSoup(html, 'lxml')
        title = ''
        for sel in ['h1', '.news-title', '.article-title', 'title', '.bt']:
            el = soup.select_one(sel)
            if el:
                title = clean_text(el.get_text())
                break

        content_el = None
        for sel in ['.article-content', '.news-content', '.content', '#vsb_content',
                     '.v_news_content', 'article']:
            content_el = soup.select_one(sel)
            if content_el:
                break
        if not content_el:
            content_el = soup.find('body')
        content = clean_text(content_el.get_text()) if content_el else ''

        deadline = extract_deadline(content)
        activity_dates = extract_activity_dates(content)

        return ScrapedProgram(
            university=self.university_name,
            college=self._infer_college(url, title),
            program_name=title,
            program_type=infer_program_type(title, content),
            raw_majors=','.join(infer_majors(title + ' ' + content[:500])),
            application_deadline=deadline,
            activity_start=activity_dates.get('start', ''),
            activity_end=activity_dates.get('end', ''),
            details_url=url,
            application_url=extract_application_url(content),
            raw_description=content[:800],
            source_url=url,
            crawled_at=datetime.now(CST).isoformat(),
            contact_info={'email': extract_email(content), 'phone': extract_phone(content)},
            requirements_text='',
            location='北京',
        )

    def _infer_college(self, url: str, title: str) -> str:
        url_l = url.lower()
        if any(k in url_l for k in ['iiis', '交叉']):
            return '交叉信息研究院'
        if any(k in url_l for k in ['cs.', 'computer', '计算机系']):
            return '计算机科学与技术系'
        if any(k in url_l for k in ['ai', '人工智能']):
            return '人工智能学院'
        if any(k in url_l for k in ['sz.', '深圳']):
            return '深圳国际研究生院'
        if any(k in url_l for k in ['math', '数学']):
            return '数学科学系'
        if any(k in url_l for k in ['yz.', '招生']):
            return '研究生院'
        return '未知学院'
