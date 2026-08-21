# -*- coding: utf-8 -*-
# 漫小肆韓漫 - TVBox 漫画爬虫（完整修复版）
# 目标: https://www.mxshm.top/

import sys
import re
import json
import urllib.parse
from base.spider import Spider
from bs4 import BeautifulSoup
import requests


class Spider(Spider):
    def getName(self):
        return "漫小肆韓漫"

    def init(self, extend=""):
        self.host = "https://www.mxshm.top"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Linux; Android 12; 22041211AC Build/SP1A.210812.016) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.104 Mobile Safari/537.36",
            "Referer": self.host + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })

        self.class_map = {
            "性感": "性感",
            "巨乳": "巨乳",
            "连载": "连载",
            "完结": "完结",
        }

    def _fix_url(self, url):
        if not url:
            return ""
        if url.startswith("http"):
            return url
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.host + url
        return self.host + "/" + url

    def _fetch(self, url, timeout=15):
        try:
            resp = self.session.get(url, timeout=timeout)
            resp.encoding = "utf-8"
            return resp.text
        except Exception as e:
            print(f"[Fetch Error] {url} -> {e}")
            return ""

    def homeContent(self, filter=False):
        classes = []
        for tid, name in self.class_map.items():
            classes.append({"type_id": tid, "type_name": name})
        return {"class": classes}

    def homeVideoContent(self):
        try:
            html = self._fetch(self.host)
            if not html:
                return {"list": []}
            comics = self._extract_comics_from_home(html)
            return {"list": comics[:30]}
        except Exception as e:
            print(f"首页异常: {e}")
            return {"list": []}

    def _extract_comics_from_home(self, html):
        soup = BeautifulSoup(html, "html.parser")
        comics = []
        seen = set()

        for li in soup.select(".manga-list-2 li"):
            a_tag = li.find("a", href=True)
            if not a_tag:
                continue
            href = a_tag.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)

            id_match = re.search(r"/book/(\d+)", href)
            comic_id = id_match.group(1) if id_match else ""

            title_tag = li.select_one(".manga-list-2-title a")
            title = title_tag.get_text(strip=True) if title_tag else ""

            img = li.select_one(".manga-list-2-cover-img")
            pic = ""
            if img:
                pic = img.get("data-original", "") or img.get("src", "")
                if pic and not pic.startswith("http"):
                    pic = self._fix_url(pic)

            tip_tag = li.select_one(".manga-list-2-tip")
            tip = tip_tag.get_text(strip=True)[:30] if tip_tag else ""

            if comic_id:
                comics.append({
                    "vod_id": comic_id,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": tip
                })

        for li in soup.select(".rank-list li"):
            a_tag = li.find("a", href=True)
            if not a_tag:
                continue
            href = a_tag.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)

            id_match = re.search(r"/book/(\d+)", href)
            comic_id = id_match.group(1) if id_match else ""

            title_tag = li.select_one(".rank-list-info-right-title")
            title = title_tag.get_text(strip=True) if title_tag else ""

            img = li.select_one(".rank-list-cover-img")
            pic = ""
            if img:
                pic = img.get("data-original", "") or img.get("src", "")
                if pic and not pic.startswith("http"):
                    pic = self._fix_url(pic)

            if comic_id and title:
                comics.append({
                    "vod_id": comic_id,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": "排行"
                })

        return comics

    def categoryContent(self, tid, pg, filter=False, extend=None):
        pg = int(pg) if pg else 1

        tag_map = {
            "性感": "性感",
            "巨乳": "巨乳",
            "连载": "",
            "完结": "全部",
        }

        tag = tag_map.get(tid, "")
        end = "1" if tid == "完结" else "0" if tid == "连载" else ""

        url = f"{self.host}/booklist/"
        params = {"page": pg}
        if tag:
            params["tag"] = tag
        if end:
            params["end"] = end

        html = self._fetch(url + "?" + urllib.parse.urlencode(params))

        if not html:
            return {"list": [], "page": pg, "pagecount": 1}

        comics = self._extract_comics_from_list(html)
        pagecount = self._extract_pagecount(html)

        return {
            "list": comics,
            "page": pg,
            "pagecount": pagecount if pagecount > pg else pg + 1,
            "limit": 20,
            "total": pagecount * 20
        }

    def _extract_comics_from_list(self, html):
        soup = BeautifulSoup(html, "html.parser")
        comics = []
        seen = set()

        for li in soup.select("ul li"):
            a_tag = li.find("a", href=True)
            if not a_tag:
                continue
            href = a_tag.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)

            if not re.search(r"/book/\d+", href):
                continue

            id_match = re.search(r"/book/(\d+)", href)
            comic_id = id_match.group(1) if id_match else ""

            title_tag = li.select_one(".manga-list-2-title a") or li.select_one(".book-list-info-title")
            title = title_tag.get_text(strip=True) if title_tag else ""

            img = li.select_one(".manga-list-2-cover-img") or li.select_one("img")
            pic = ""
            if img:
                pic = img.get("data-original", "") or img.get("src", "")
                if pic and not pic.startswith("http"):
                    pic = self._fix_url(pic)

            tip = ""
            tip_tag = li.select_one(".manga-list-2-tip") or li.select_one(".book-list-info-desc")
            if tip_tag:
                tip = tip_tag.get_text(strip=True)[:30]

            if comic_id:
                comics.append({
                    "vod_id": comic_id,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": tip
                })

        return comics

    def _extract_pagecount(self, html):
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.select(".pagination a, .page a"):
            href = a.get("href", "")
            m = re.search(r"page=(\d+)", href)
            if m:
                try:
                    num = int(m.group(1))
                    if num > 1:
                        return num + 1
                except:
                    pass
        return 1

    def detailContent(self, ids):
        """获取漫画详情 + 章节列表（正序）"""
        comic_id = ids[0]
        url = f"{self.host}/book/{comic_id}"
        html = self._fetch(url)

        if not html:
            return {"list": []}

        soup = BeautifulSoup(html, "html.parser")

        # 标题
        title = ""
        title_tag = soup.select_one(".detail-main-info-title")
        if title_tag:
            title = title_tag.get_text(strip=True)

        # 封面
        pic = ""
        pic_tag = soup.select_one(".detail-main-cover img")
        if pic_tag:
            pic = pic_tag.get("data-original", "") or pic_tag.get("src", "")
            if pic and not pic.startswith("http"):
                pic = self._fix_url(pic)

        # 简介
        intro = ""
        intro_tag = soup.select_one(".detail-desc")
        if intro_tag:
            intro = intro_tag.get_text(strip=True)

        # 分类
        cate = ""
        cate_tag = soup.select_one(".detail-main-info-class")
        if cate_tag:
            cate = cate_tag.get_text(strip=True)

        # 提取章节（正序，不反转）
        chapters = []
        seen_urls = set()

        # 方式1: 使用 id="detail-list-select" 的选择器
        for a in soup.select("#detail-list-select li a"):
            href = a.get("href", "")
            name = a.get_text(strip=True)
            if not name:
                name = a.get("title", "") or f"第{len(chapters)+1}话"

            if href and href not in seen_urls:
                seen_urls.add(href)
                if href.startswith("/"):
                    href = self._fix_url(href)
                chapters.append(f"{name}${href}")

        # 方式2: 如果没找到，用 .detail-list-1 选择器
        if not chapters:
            for a in soup.select(".detail-list-1 li a"):
                href = a.get("href", "")
                name = a.get_text(strip=True)
                if not name:
                    name = a.get("title", "") or f"第{len(chapters)+1}话"

                if href and href not in seen_urls:
                    seen_urls.add(href)
                    if href.startswith("/"):
                        href = self._fix_url(href)
                    chapters.append(f"{name}${href}")

        # 方式3: 兜底 - 所有 /chapter/ 链接
        if not chapters:
            for a in soup.select("a[href^='/chapter/']"):
                href = a.get("href", "")
                name = a.get_text(strip=True)
                if not name:
                    name = a.get("title", "") or f"第{len(chapters)+1}话"

                if href and href not in seen_urls:
                    seen_urls.add(href)
                    if href.startswith("/"):
                        href = self._fix_url(href)
                    chapters.append(f"{name}${href}")

        # 不反转，保持网站原始顺序（从第1话开始）
        play_url = "#".join(chapters) if chapters else ""

        print(f"[漫小肆] 提取到 {len(chapters)} 个章节")

        return {
            "list": [{
                "vod_id": comic_id,
                "vod_name": title or f"漫画{comic_id}",
                "vod_pic": pic,
                "vod_content": intro,
                "vod_remarks": cate,
                "vod_play_from": "漫小肆韓漫",
                "vod_play_url": play_url
            }]
        }

    def playerContent(self, flag, id, vipFlags=None):
        try:
            chapter_url = id if id.startswith("http") else self._fix_url(id)
            if not chapter_url:
                return self._error_result("无效的章节URL")

            html = self._fetch(chapter_url)
            if not html:
                return self._error_result("获取章节页面失败")

            soup = BeautifulSoup(html, "html.parser")

            images = []

            # 从 .view-main-1 中提取所有图片
            view_main = soup.select_one(".view-main-1")
            if view_main:
                for img in view_main.select("img"):
                    src = img.get("data-original", "") or img.get("src", "")
                    if src:
                        if src.startswith("//"):
                            src = "https:" + src
                        elif src.startswith("/"):
                            src = self._fix_url(src)
                        images.append(src)

            # 兜底：所有图片
            if not images:
                for img in soup.select("img.lazy, img[data-original]"):
                    src = img.get("data-original", "") or img.get("src", "")
                    if src and "logo" not in src.lower() and "icon" not in src.lower():
                        if src.startswith("//"):
                            src = "https:" + src
                        elif src.startswith("/"):
                            src = self._fix_url(src)
                        images.append(src)

            if not images:
                return self._error_result("未找到图片")

            pics_url = "pics://" + "&&".join(images)

            return {
                "parse": 0,
                "playUrl": "",
                "url": pics_url,
                "header": {
                    "User-Agent": "Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36",
                    "Referer": self.host + "/"
                },
                "vod_player": "画"
            }

        except Exception as e:
            print(f"playerContent error: {e}")
            return self._error_result(f"获取图片异常: {str(e)}")

    def _error_result(self, msg):
        result_data = {"title": "加载失败", "content": msg}
        return {
            "parse": 0,
            "playUrl": "",
            "url": f"novel://{json.dumps(result_data, ensure_ascii=False)}",
            "header": ""
        }

    def searchContent(self, key, quick=False, pg="1"):
        pg = int(pg) if pg else 1
        enc_key = urllib.parse.quote(key)

        url = f"{self.host}/search?keyword={enc_key}&page={pg}"
        html = self._fetch(url)

        if not html:
            return {"list": [], "page": pg, "pagecount": 1}

        comics = self._extract_search_results(html)
        pagecount = self._extract_pagecount(html)

        if pagecount <= 1 and len(comics) >= 20:
            pagecount = pg + 1
        if pagecount < pg:
            pagecount = pg

        return {
            "list": comics,
            "page": pg,
            "pagecount": pagecount,
            "limit": 20,
            "total": pagecount * 20
        }

    def _extract_search_results(self, html):
        soup = BeautifulSoup(html, "html.parser")
        comics = []
        seen = set()

        for li in soup.select("ul li"):
            a_tag = li.find("a", href=True)
            if not a_tag:
                continue
            href = a_tag.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)

            if not re.search(r"/book/\d+", href):
                continue

            id_match = re.search(r"/book/(\d+)", href)
            comic_id = id_match.group(1) if id_match else ""

            title_tag = li.select_one(".book-list-info-title") or li.select_one("a")
            title = title_tag.get_text(strip=True) if title_tag else ""

            img = li.select_one("img")
            pic = ""
            if img:
                pic = img.get("data-original", "") or img.get("src", "")
                if pic and not pic.startswith("http"):
                    pic = self._fix_url(pic)

            intro = ""
            intro_tag = li.select_one(".book-list-info-desc")
            if intro_tag:
                intro = intro_tag.get_text(strip=True)[:30]

            if comic_id:
                comics.append({
                    "vod_id": comic_id,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": intro
                })

        return comics

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def destroy(self):
        if self.session:
            self.session.close()

    def localProxy(self, param):
        return None