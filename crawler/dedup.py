# crawler/dedup.py — 多源去重引擎

import re
from typing import List
from hashlib import md5


class DeduplicationEngine:
    """多源数据去重"""

    def __init__(self):
        self.seen_fingerprints = set()

    def fingerprint(self, program: dict) -> str:
        """为每个项目生成唯一指纹"""
        if program.get('details_url'):
            return md5(program['details_url'].encode()).hexdigest()

        text = f"{program.get('university','')}|{program.get('college','')}|{program.get('program_name','')}"
        return md5(text.encode()).hexdigest()

    def _normalize_title(self, title: str) -> str:
        """标题规范化"""
        noise = ['关于', '举办', '通知', '公告', '的', '拟']
        for w in noise:
            title = title.replace(w, '')
        title = re.sub(r'\s+', '', title)
        title = re.sub(r'[《》「」""''""【】\[\]（）()]', '', title)
        return title

    def is_duplicate(self, prog1: dict, prog2: dict) -> bool:
        # Same URL = duplicate
        if prog1.get('details_url') and prog2.get('details_url'):
            if prog1['details_url'] == prog2['details_url']:
                return True

        # Same university + college + similar title
        if (prog1.get('university') == prog2.get('university') and
            prog1.get('college') == prog2.get('college')):
            t1 = self._normalize_title(prog1.get('program_name', ''))
            t2 = self._normalize_title(prog2.get('program_name', ''))
            if t1 and t2 and t1 == t2:
                return True

        # Same deadline + overlapping majors
        dl1 = prog1.get('application_deadline', '')
        dl2 = prog2.get('application_deadline', '')
        if dl1 and dl2 and dl1 == dl2 and prog1.get('university') == prog2.get('university'):
            m1 = set(prog1.get('majors', []))
            m2 = set(prog2.get('majors', []))
            if m1 & m2:
                return True

        return False

    def deduplicate(self, programs: List[dict], strategy: str = 'merge') -> List[dict]:
        seen = []
        for prog in programs:
            dupe = False
            for i, existing in enumerate(seen):
                if self.is_duplicate(prog, existing):
                    dupe = True
                    if strategy == 'merge':
                        self._merge(existing, prog)
                    elif strategy == 'prefer_official':
                        if prog.get('source', {}).get('type') == 'official':
                            seen[i] = prog
                    break
            if not dupe:
                seen.append(prog)
        return seen

    def _merge(self, target: dict, source: dict):
        """合并重复项"""
        target['majors'] = list(set(target.get('majors', []) + source.get('majors', [])))
        target['tags'] = list(set(target.get('tags', []) + source.get('tags', [])))
        for key in ['application_url', 'contact_email', 'contact_phone', 'description', 'activity_mode']:
            if not target.get(key) and source.get(key):
                target[key] = source.get(key)
        target.setdefault('alternative_sources', []).append(source.get('source'))
        # Keep the earlier deadline
        if source.get('application_deadline') and (
            not target.get('application_deadline') or
            source['application_deadline'] < target['application_deadline']
        ):
            target['application_deadline'] = source['application_deadline']
