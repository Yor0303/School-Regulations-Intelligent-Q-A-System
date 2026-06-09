# -*- encoding: utf-8 -*-
"""Web content loader — fetch URLs, extract clean text, and crawl seed pages."""
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class WebLoader:
    def __init__(
        self,
        user_agent: str = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        timeout: int = 15,
    ):
        self.user_agent = user_agent
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})

    # ------------------------------------------------------------------
    #  Single URL fetch
    # ------------------------------------------------------------------

    def fetch(self, url: str) -> Optional[str]:
        """Fetch a single URL and return clean text content."""
        import trafilatura

        try:
            resp = self.session.get(url.strip(), timeout=self.timeout)
            resp.raise_for_status()
        except Exception:
            return None

        text = trafilatura.extract(
            resp.text,
            include_links=False,
            include_images=False,
            include_tables=False,
        )
        return text.strip() if text and text.strip() else None

    # ------------------------------------------------------------------
    #  Seed crawl — page itself + all links on it (depth = 1)
    # ------------------------------------------------------------------

    def _discover_links(self, base_url: str, html: str) -> List[str]:
        """Extract and resolve content-relevant <a href> links from a page.

        Filters out:
          - Navigation/sidebar links (short repetitive text like 首页/联系我们/组织架构)
          - External domains, file downloads, anchors, javascript links
        """
        base_domain = urlparse(base_url).netloc
        base_path = urlparse(base_url).path
        soup = BeautifulSoup(html, "lxml")
        links = []
        seen: Set[str] = set()

        # Common navigation / boilerplate link texts to skip
        nav_texts = {
            "首页", "返回首页", "网站首页",
            "联系我们", "关于我们", "版权",
            "组织架构", "部门职责", "本科教学管理人员",
            "教学改革处", "教学建设处", "教学运行处",
            "实验实践处", "工程训练中心", "现代教育技术中心",
            "院长信箱", "站点地图", "友情链接",
            "English", "中文", "EN",
        }

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            link_text = a.get_text(strip=True)

            # Skip navigation boilerplate
            if link_text in nav_texts or len(link_text) < 3:
                continue
            # Skip javascript / anchor-only links
            if href.startswith(("javascript:", "#")):
                continue

            absolute = urljoin(base_url, href)
            parsed = urlparse(absolute)

            if parsed.scheme not in ("http", "https"):
                continue
            if parsed.netloc != base_domain:
                continue

            clean = parsed._replace(fragment="").geturl()

            # Skip file downloads
            path_lower = parsed.path.lower()
            if path_lower.endswith((".pdf", ".zip", ".rar", ".doc", ".docx",
                                     ".xls", ".xlsx", ".ppt", ".pptx",
                                     ".jpg", ".png", ".gif", ".mp4", ".avi")):
                continue

            # Skip the seed page itself
            if clean.rstrip("/") == base_url.rstrip("/"):
                continue

            if clean in seen:
                continue
            seen.add(clean)
            links.append(clean)

        return links

    def _fetch_and_extract(self, url: str) -> Optional[Dict]:
        """Fetch URL and return {source_url, page_title, text} or None."""
        import trafilatura

        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            # Auto-detect encoding (many Chinese uni sites use gbk/gb2312)
            if resp.apparent_encoding and resp.apparent_encoding != resp.encoding:
                resp.encoding = resp.apparent_encoding
        except Exception:
            return None

        html = resp.text
        if not html or len(html) < 100:
            return None

        # Title
        title = url
        try:
            soup = BeautifulSoup(html, "lxml")
            t = soup.find("title")
            if t and t.get_text(strip=True):
                title = t.get_text(strip=True)
        except Exception:
            pass

        # Try trafilatura first (best for article-like pages)
        text = trafilatura.extract(
            html,
            include_links=False,
            include_images=False,
            include_tables=False,
            output_format="txt",
        )

        # Fallback: strip tags and extract all visible body text
        if not text or len(text.strip()) < 50:
            try:
                soup = BeautifulSoup(html, "lxml")
                # Remove nav, script, style, footer
                for tag in soup.find_all(["nav", "script", "style", "footer", "header"]):
                    tag.decompose()
                body = soup.find("body")
                if body:
                    text = body.get_text(separator="\n", strip=True)
            except Exception:
                pass

        if not text or len(text.strip()) < 30:
            return None

        return {
            "text": text.strip(),
            "source_url": url,
            "page_title": title,
        }

    def crawl_seed(self, seed_url: str) -> List[Dict]:
        """Crawl a seed URL: extract the page itself, then all linked pages.

        Depth = 1: seed page + 1 level of outgoing links. No recursion.
        """
        all_pages: List[Dict] = []

        # Step 1 — extract seed page itself
        seed_data = self._fetch_and_extract(seed_url)
        if seed_data:
            all_pages.append(seed_data)

        # Step 2 — discover links on the seed page
        try:
            resp = self.session.get(seed_url, timeout=self.timeout)
            resp.raise_for_status()
            links = self._discover_links(seed_url, resp.text)
        except Exception:
            links = []

        # Step 3 — fetch each linked page
        for link in links:
            page_data = self._fetch_and_extract(link)
            if page_data:
                all_pages.append(page_data)

        return all_pages

    # ------------------------------------------------------------------
    #  Batch URL processing (existing, for admin paste)
    # ------------------------------------------------------------------

    def process_urls(self, urls: List[str]) -> List[Dict]:
        """Fetch multiple URLs and return chunk-ready records."""
        records = []
        for url in urls:
            page_data = self._fetch_and_extract(url)
            if page_data:
                records.append(page_data)
        return records
