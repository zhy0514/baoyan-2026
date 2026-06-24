# crawler/base_scraper.py — 爬虫基类（模板方法模式）

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import requests
import time
import random
import logging
import urllib3
from typing import List, Optional

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from utils import random_ua, random_delay


@dataclass
class ScrapedProgram:
    """爬取到的原始数据"""
    university: str = ''
    college: str = ''
    program_name: str = ''
    program_type: str = ''        # 夏令营 / 预推免
    raw_majors: str = ''          # 原始专业描述
    application_start: str = ''
    application_deadline: str = ''
    activity_start: str = ''
    activity_end: str = ''
    details_url: str = ''
    application_url: str = ''
    raw_description: str = ''
    source_url: str = ''
    crawled_at: str = ''
    contact_info: dict = field(default_factory=dict)
    requirements_text: str = ''
    location: str = ''
    degree_types: str = ''        # 硕士/直博/专硕


class BaseScraper(ABC):
    """爬虫基类 — 模板方法模式"""

    name: str = 'base'
    university_name: str = ''
    university_short: str = ''

    def __init__(self):
        self.logger = logging.getLogger(self.name)
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        s = requests.Session()
        s.headers.update({
            'User-Agent': random_ua(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        # Skip SSL verification for Chinese university sites with bad certs
        s.verify = False
        return s

    # ====== 模板方法：定义爬取流程骨架 ======
    def scrape(self) -> List[ScrapedProgram]:
        self.logger.info(f"开始爬取 {self.university_name} ...")
        results = []

        list_urls = self.get_list_page_urls()
        self.logger.info(f"  共 {len(list_urls)} 个列表页")

        for url in list_urls:
            try:
                self.logger.info(f"  → 列表页: {url}")
                html = self.fetch_page(url)

                if self.needs_js_rendering(html):
                    self.logger.info("    需要JS渲染")
                    html = self.render_with_js(url)

                detail_urls = self.parse_list_page(html)
                self.logger.info(f"    找到 {len(detail_urls)} 个详情链接")
                detail_urls = detail_urls[:self.max_detail_pages()]

                for detail_url in detail_urls:
                    try:
                        # Skip PDFs and non-HTML files
                        if detail_url.lower().endswith(('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.rar')):
                            continue
                        random_delay(*self.delay_range())
                        detail_html = self.fetch_page(detail_url)
                        program = self.parse_detail_page(detail_html, detail_url)
                        if program:
                            results.append(program)
                            self.logger.debug(f"      ✓ {program.program_name}")
                    except Exception as e:
                        self.logger.error(f"    详情页失败 {detail_url}: {e}")
                        continue

            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code in (404, 403, 410):
                    self.logger.debug(f"  列表页 {url} HTTP {e.response.status_code}，跳过")
                else:
                    self.logger.warning(f"  列表页失败 {url}: {e}")
                continue
            except Exception as e:
                self.logger.error(f"  列表页失败 {url}: {e}")
                continue

        self.logger.info(f"  {self.university_name} 完成，共 {len(results)} 条")
        return results

    # ====== 子类必须实现 ======
    @abstractmethod
    def get_list_page_urls(self) -> List[str]:
        pass

    @abstractmethod
    def parse_list_page(self, html: str) -> List[str]:
        pass

    @abstractmethod
    def parse_detail_page(self, html: str, url: str) -> Optional[ScrapedProgram]:
        pass

    # ====== 子类可选覆盖 ======
    def needs_js_rendering(self, html: str = '') -> bool:
        return False

    def max_detail_pages(self) -> int:
        return 30

    def delay_range(self) -> tuple:
        return (0.5, 1.5)

    # ====== 内置方法 ======
    def fetch_page(self, url: str) -> str:
        for attempt in range(3):
            try:
                resp = self.session.get(url, timeout=25, allow_redirects=True)
                resp.raise_for_status()
                # auto-detect encoding
                if resp.encoding is None or resp.encoding.lower() == 'iso-8859-1':
                    resp.encoding = resp.apparent_encoding or 'utf-8'
                return resp.text
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code in (404, 403, 410):
                    raise  # Don't retry 404/403/410
                self.logger.warning(f"请求失败 {url[:80]} HTTP {e.response.status_code if e.response else '?'} 第{attempt+1}次: {e}")
                if attempt < 2:
                    time.sleep(2 ** attempt * 3)
            except requests.exceptions.SSLError:
                raise  # Don't retry SSL errors either
            except Exception as e:
                self.logger.warning(f"请求失败 {url[:80]} 第{attempt+1}次: {e}")
                if attempt < 2:
                    time.sleep(2 ** attempt * 3)
        raise Exception(f"3次请求均失败: {url}")

    def render_with_js(self, url: str) -> str:
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options

            opts = Options()
            opts.add_argument('--headless=new')
            opts.add_argument('--no-sandbox')
            opts.add_argument('--disable-dev-shm-usage')
            opts.add_argument('--disable-blink-features=AutomationControlled')
            opts.add_argument(f'user-agent={random_ua()}')
            opts.add_argument('--disable-gpu')
            opts.add_argument('--window-size=1920,1080')

            driver = webdriver.Chrome(options=opts)
            driver.get(url)
            time.sleep(random.uniform(2, 4))
            html = driver.page_source
            driver.quit()
            return html
        except Exception as e:
            self.logger.error(f"Selenium渲染失败: {e}")
            raise
