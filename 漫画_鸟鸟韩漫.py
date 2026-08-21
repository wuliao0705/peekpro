# -*- coding: utf-8 -*-
# 鸟鸟韩漫 - 精简版（仅保留“全部”分类）

import sys
import re
import json
import urllib.parse
from base.spider import Spider
from bs4 import BeautifulSoup
import requests


class Spider(Spider):
    def getName(self):
        return "鸟鸟韩漫"

    def init(self, extend=""):
        self.host = "https://nnhanman9.com"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.host + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        self.class_map = {
            "all": "全部", "正妹": "正妹", "恋爱": "恋爱", "出版漫画": "出版漫画",
            "肉慾": "肉慾", "浪漫": "浪漫", "大尺度": "大尺度", "巨乳": "巨乳",
            "有夫之婦": "有夫之婦", "女大生": "女大生", "狗血劇": "狗血劇",
            "同居": "同居", "好友": "好友", "調教": "調教", "动作": "动作",
            "後宮": "後宮", "不倫": "不倫", "3D": "3D", "校園": "校園",
            "耽美": "耽美", "日漫": "日漫",
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

    def _parse_extend(self, extend):
        if isinstance(extend, dict):
            return extend
        if isinstance(extend, str):
            try:
                return json.loads(extend)
            except:
                params = {}
                for part in extend.split('&'):
                    if '=' in part:
                        k, v = part.split('=', 1)
                        params[k] = v
                return params
        return {}

    def homeContent(self, filter=False):
        # 仅保留“全部”分类
        classes = [
            {"type_id": "category_group", "type_name": "全部"},
        ]
        filters = {}
        type_options = [{"n": name, "v": tid} for tid, name in self.class_map.items()]
        filters["category_group"] = [
            {"key": "sub", "name": "类型", "value": type_options},
            {"key": "st", "name": "进度", "value": [{"n": "全部", "v": "all"}, {"n": "已完结", "v": "completed"}, {"n": "连载中", "v": "serialized"}]},
            {"key": "ob", "name": "排序", "value": [{"n": "按时间", "v": "time"}, {"n": "按热度", "v": "hits"}]},
        ]
        return {"class": classes, "filters": filters}

    def homeVideoContent(self):
        try:
            html = self._fetch(self.host)
            if not html:
                return {"list": []}
            return {"list": self._extract_comics_from_list(html)[:30]}
        except Exception as e:
            print(f"首页异常: {e}")
            return {"list": []}

    # ---- 解析分类列表（.col_3_1 li） ----
    def _extract_comics_from_list(self, html):
        soup = BeautifulSoup(html, "html.parser")
        comics = []
        seen = set()
        for li in soup.select(".col_3_1 li"):
            a_tag = li.find("a", href=True)
            if not a_tag:
                continue
            href = a_tag.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)
            if not re.search(r"/comic/[^.]+\.html", href):
                continue
            id_match = re.search(r"/comic/([^.]+)\.html", href)
            comic_id = id_match.group(1) if id_match else ""
            title_tag = li.select_one(".txtA")
            title = title_tag.get_text(strip=True) if title_tag else ""
            img = li.select_one(".ImgA img, .ImgA picture source")
            pic = ""
            if img:
                pic = img.get("src", "") or img.get("data-src", "") or img.get("srcset", "")
                if pic and not pic.startswith("http"):
                    pic = self._fix_url(pic)
            info_tag = li.select_one(".info")
            remarks = info_tag.get_text(strip=True) if info_tag else ""
            if comic_id:
                comics.append({"vod_id": comic_id, "vod_name": title, "vod_pic": pic, "vod_remarks": remarks})
        return comics

    # ---- 提取最大页码 ----
    def _extract_pagecount(self, html):
        soup = BeautifulSoup(html, "html.parser")
        max_page = 1
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            m = re.search(r"/page/(\d+)", href)
            if m:
                try:
                    num = int(m.group(1))
                    if num > max_page:
                        max_page = num
                except:
                    pass
        return max_page

    def categoryContent(self, tid, pg, filter=False, extend=None):
        pg = int(pg) if pg else 1
        params = self._parse_extend(extend)

        # ---- 全部（原分类组） ----
        if tid == "category_group":
            sub = params.get("sub", "all")
            st = params.get("st", "all")
            ob = params.get("ob", "time")
            url = f"{self.host}/comics/{sub}/ob/{ob}/st/{st}/page/{pg}"
            html = self._fetch(url)
            if not html:
                return {"list": [], "page": pg, "pagecount": 1}
            comics = self._extract_comics_from_list(html)
            pagecount = self._extract_pagecount(html)
            if pagecount < pg:
                pagecount = pg
            return {"list": comics, "page": pg, "pagecount": pagecount, "limit": 20, "total": pagecount * 20}

        return {"list": [], "page": pg, "pagecount": 1}

    # ---- 详情 ----
    def detailContent(self, ids):
        comic_id = ids[0]
        url = f"{self.host}/comic/{comic_id}.html"
        html = self._fetch(url)
        if not html:
            return {"list": []}
        soup = BeautifulSoup(html, "html.parser")
        title = soup.select_one("h1").get_text(strip=True) if soup.select_one("h1") else ""
        pic = ""
        img_tag = soup.select_one(".ImgA img, .imgBox img")
        if img_tag:
            pic = img_tag.get("src", "") or img_tag.get("data-src", "")
            if pic and not pic.startswith("http"):
                pic = self._fix_url(pic)
        author = ""
        cate = ""
        txt_items = soup.select(".txtItme")
        if len(txt_items) >= 1:
            author = txt_items[0].get_text(strip=True)
        if len(txt_items) >= 2:
            cate = txt_items[1].get_text(strip=True)
        intro = soup.select_one(".txtDesc").get_text(strip=True) if soup.select_one(".txtDesc") else ""
        chapters = []
        for li in soup.select(".Drama li"):
            a_tag = li.find("a", href=True)
            if a_tag:
                href = a_tag.get("href", "")
                name = a_tag.get_text(strip=True)
                if href:
                    if href.startswith("/"):
                        href = self._fix_url(href)
                    chapters.append(f"{name}${href}")
        if not chapters:
            for li in soup.select("#mh-chapter-list-ol-0 li"):
                a_tag = li.find("a", href=True)
                if a_tag:
                    href = a_tag.get("href", "")
                    name = a_tag.get_text(strip=True)
                    if href:
                        if href.startswith("/"):
                            href = self._fix_url(href)
                        chapters.append(f"{name}${href}")
        if not chapters:
            for a in soup.select("a[href*='/comic/']"):
                href = a.get("href", "")
                name = a.get_text(strip=True)
                if href == f"/comic/{comic_id}.html":
                    continue
                if href and "/comic/" in href and ".html" in href and re.search(r"/comic/[^/]+/chapter-\d+\.html", href):
                    if href.startswith("/"):
                        href = self._fix_url(href)
                    chapters.append(f"{name}${href}")
        seen = set()
        unique = []
        for ch in chapters:
            if ch not in seen:
                seen.add(ch)
                unique.append(ch)
        unique.reverse()
        play_url = "#".join(unique)
        return {
            "list": [{
                "vod_id": comic_id,
                "vod_name": title or f"漫画{comic_id}",
                "vod_pic": pic,
                "vod_content": intro,
                "vod_author": author,
                "vod_remarks": cate,
                "vod_play_from": "鸟鸟韩漫",
                "vod_play_url": play_url,
            }]
        }

    # ---- 播放（图片） ----
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
            tbody = soup.select_one("tbody")
            if tbody:
                for img in tbody.select("img"):
                    src = img.get("src", "") or img.get("data-src", "")
                    if src:
                        if src.startswith("//"):
                            src = "https:" + src
                        elif src.startswith("/"):
                            src = self._fix_url(src)
                        images.append(src)
            if not images:
                for img in soup.select(".imgBox img, .content img"):
                    src = img.get("src", "") or img.get("data-src", "")
                    if src:
                        if src.startswith("//"):
                            src = "https:" + src
                        elif src.startswith("/"):
                            src = self._fix_url(src)
                        images.append(src)
            if not images:
                for img in soup.select("img"):
                    src = img.get("src", "") or img.get("data-src", "")
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
                "header": {"User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36", "Referer": self.host + "/"},
                "vod_player": "画",
            }
        except Exception as e:
            print(f"playerContent error: {e}")
            return self._error_result(f"获取图片异常: {str(e)}")

    def _error_result(self, msg):
        result_data = {"title": "加载失败", "content": msg}
        return {"parse": 0, "playUrl": "", "url": f"novel://{json.dumps(result_data, ensure_ascii=False)}", "header": ""}

    # ---- 搜索 ----
    def searchContent(self, key, quick=False, pg="1"):
        pg = int(pg) if pg else 1
        enc_key = urllib.parse.quote(key)
        url = f"{self.host}/search/{enc_key}/page/{pg}"
        html = self._fetch(url)
        if not html:
            return {"list": [], "page": pg, "pagecount": 1}
        comics = self._extract_comics_from_list(html)
        pagecount = self._extract_pagecount(html)
        if pagecount < pg:
            pagecount = pg
        return {"list": comics, "page": pg, "pagecount": pagecount, "limit": 20, "total": pagecount * 20}

    # ---- 其他必需方法 ----
    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def destroy(self):
        if self.session:
            self.session.close()

    def localProxy(self, param):
        return None