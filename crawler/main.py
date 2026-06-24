# crawler/main.py — 入口：调度所有爬虫

import json
import os
import sys
import logging
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from normalizer import DataNormalizer
from dedup import DeduplicationEngine

# Import scrapers
from scrapers.peking import PekingScraper
from scrapers.tsinghua import TsinghuaScraper
from scrapers.fudan import FudanScraper
from scrapers.sjtu import SJTUScraper
from scrapers.zju import ZJUScraper
from platforms.csbaoyan import CSBaoyanScraper

CST = timezone(timedelta(hours=8))
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('main')


# Registry of all scrapers
SCRAPER_REGISTRY = [
    PekingScraper,
    TsinghuaScraper,
    FudanScraper,
    SJTUScraper,
    ZJUScraper,
]


def load_existing_programs() -> list:
    """加载已有数据"""
    path = os.path.join(DATA_DIR, 'programs.json')
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data.get('programs', [])
        except Exception as e:
            logger.warning(f"加载已有数据失败: {e}")
    return []


def generate_meta(programs: list) -> dict:
    """生成统计元数据"""
    by_type = {}
    by_status = {}
    by_major = {}
    univ_set = set()
    src_types = {}

    for p in programs:
        t = p.get('program_type', '未知')
        by_type[t] = by_type.get(t, 0) + 1
        s = p.get('status', '未知')
        by_status[s] = by_status.get(s, 0) + 1
        for m in p.get('majors', []):
            by_major[m] = by_major.get(m, 0) + 1
        univ_set.add(p.get('university', ''))
        src = p.get('source', {}).get('type', 'unknown')
        src_types[src] = src_types.get(src, 0) + 1

    return {
        'last_updated': datetime.now(CST).isoformat(),
        'total_programs': len(programs),
        'by_type': by_type,
        'by_status': by_status,
        'by_major': dict(sorted(by_major.items(), key=lambda x: x[1], reverse=True)),
        'universities_covered': len(univ_set),
        'sources': src_types,
    }


def save_data(programs: list):
    """保存数据文件"""
    os.makedirs(DATA_DIR, exist_ok=True)

    # programs.json
    output = {
        'version': '1.0',
        'last_updated': datetime.now(CST).isoformat(),
        'total_count': len(programs),
        'programs': programs,
    }
    with open(os.path.join(DATA_DIR, 'programs.json'), 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    logger.info(f"已保存 programs.json ({len(programs)} 条)")

    # meta.json
    meta = generate_meta(programs)
    with open(os.path.join(DATA_DIR, 'meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    logger.info(f"已保存 meta.json")


def main():
    logger.info("=" * 60)
    logger.info("2026 985高校夏令营/预推免信息聚合 — 爬虫启动")
    logger.info("=" * 60)

    normalizer = DataNormalizer()
    deduper = DeduplicationEngine()
    all_programs = []

    # Step 1: Run university scrapers
    for scraper_cls in SCRAPER_REGISTRY:
        try:
            scraper = scraper_cls()
            raw_results = scraper.scrape()
            normalized = [normalizer.normalise(r) for r in raw_results]
            all_programs.extend(normalized)
            logger.info(f"  ✓ {scraper.university_name}: {len(normalized)} 条")
        except Exception as e:
            logger.error(f"  ✗ {scraper_cls.__name__} 执行失败: {e}")

    # Step 2: Run platform scrapers
    try:
        csb = CSBaoyanScraper()
        raw_results = csb.scrape()
        normalized = [normalizer.normalise(r) for r in raw_results]
        all_programs.extend(normalized)
        logger.info(f"  ✓ CS-BAOYAN: {len(normalized)} 条")
    except Exception as e:
        logger.error(f"  ✗ CS-BAOYAN 执行失败: {e}")

    # Step 3: Deduplicate
    logger.info(f"去重前: {len(all_programs)} 条")
    all_programs = deduper.deduplicate(all_programs, strategy='merge')
    logger.info(f"去重后: {len(all_programs)} 条")

    # Step 4: Merge with existing data (incremental update)
    existing = load_existing_programs()
    if existing:
        # Build index of existing IDs
        existing_ids = {p['id'] for p in existing}
        existing_by_id = {p['id']: p for p in existing}
        new_count = 0
        updated_count = 0

        for prog in all_programs:
            if prog['id'] not in existing_ids:
                existing.append(prog)
                new_count += 1
            else:
                # Update existing entry if source is newer
                old = existing_by_id[prog['id']]
                if prog.get('source', {}).get('crawled_at', '') > old.get('source', {}).get('crawled_at', ''):
                    idx = existing.index(old)
                    existing[idx] = prog
                    updated_count += 1

        all_programs = existing
        logger.info(f"增量更新: 新增 {new_count} 条, 更新 {updated_count} 条")

    # Step 5: Save
    save_data(all_programs)

    meta = generate_meta(all_programs)
    logger.info("=" * 60)
    logger.info(f"完成！共 {meta['total_programs']} 条数据")
    logger.info(f"  覆盖 {meta['universities_covered']} 所高校")
    logger.info(f"  类型分布: {meta['by_type']}")
    logger.info(f"  状态分布: {meta['by_status']}")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
