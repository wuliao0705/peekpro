# -*- coding: utf-8 -*-
# 自制爬虫 - 紳士漫畫（完整修复版）
# 目标：https://www.wnacg.com/

import sys
import re
import json
import requests
from urllib.parse import urljoin, quote
from bs4 import BeautifulSoup
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def getName(self):
        return "绅士漫画"

    def init(self, extend=""):
        self.host = "https://www.wnacg.com"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": self.host + "/",
        })
        self.classes = [
            {"type_id": "index", "type_name": "推荐"},
            {"type_id": "albums", "type_name": "更新"},
            {"type_id": "ranking", "type_name": "排行"},
            {"type_id": "cate_5", "type_name": "同人志"},
            {"type_id": "cate_6", "type_name": "單行本"},
            {"type_id": "cate_7", "type_name": "雜誌·短篇"},
            {"type_id": "cate_19", "type_name": "韓漫"},
        ]

    def _fetch(self, url, headers=None):
        try:
            h = headers or self.session.headers
            resp = self.session.get(url, headers=h, timeout=15)
            resp.encoding = "utf-8"
            return resp.text
        except Exception as e:
            print(f"[请求] 失败: {e}")
            return ""

    def _fix_url(self, url):
        if not url:
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.host + url
        return url

    def _parse_comic_list(self, html):
        """解析列表页 - 兼容多种结构"""
        videos = []
        if not html:
            return videos
        soup = BeautifulSoup(html, "html.parser")

        # 策略1：查找 ul.col_3_2 中的 li（主要）
        items = []
        container = soup.select_one("ul.col_3_2")
        if container:
            items = container.select("li")
            print(f"[解析] 策略1 (ul.col_3_2): 找到 {len(items)} 个")
        else:
            # 策略2：直接查找页面中所有 li
            items = soup.select("li")
            print(f"[解析] 策略2 (所有li): 找到 {len(items)} 个")

        # 策略3：如果以上都没有，查找 .imgBox 下的 li
        if not items:
            imgbox = soup.select_one(".imgBox")
            if imgbox:
                items = imgbox.select("li")
                print(f"[解析] 策略3 (.imgBox li): 找到 {len(items)} 个")

        for li in items:
            try:
                # 提取链接
                a_img = li.find("a", class_="ImgA")
                if not a_img:
                    # 尝试任何 a 标签
                    a_img = li.find("a", href=re.compile(r"/photos-index-aid-\d+\.html"))
                if not a_img:
                    continue
                href = a_img.get("href")
                if not href or "photos-index-aid-" not in href:
                    continue

                # 封面
                img = a_img.find("img")
                pic = img.get("src") if img else ""
                pic = self._fix_url(pic)

                # 标题
                a_title = li.find("a", class_="txtA")
                if not a_title:
                    # 也可能是其他 class
                    a_title = li.find("a", href=re.compile(r"/photos-index-aid-\d+\.html"))
                    if a_title and a_title != a_img:
                        title = a_title.get_text(strip=True)
                    else:
                        title = ""
                else:
                    title = a_title.get_text(strip=True)

                if not title:
                    # 尝试从 img 的 alt 获取
                    if img:
                        title = img.get("alt", "")
                if not title:
                    title = href.split("/")[-1].replace(".html", "")

                # 信息（图片数量、日期等）
                info_span = li.find("span", class_="info")
                remark = info_span.get_text(strip=True) if info_span else ""

                videos.append({
                    "vod_id": href,  # 如 /photos-index-aid-376480.html
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remark,
                })
            except Exception as e:
                print(f"[解析] 卡片失败: {e}")

        print(f"[解析] 共解析到 {len(videos)} 个漫画")
        return videos

    def _get_pagination(self, html):
        """提取总页数"""
        soup = BeautifulSoup(html, "html.parser")
        max_page = 1
        for a in soup.select(".pagination a, .page a, .page-link"):
            href = a.get("href", "")
            m = re.search(r"page[_-]?(\d+)", href)
            if m:
                num = int(m.group(1))
                if num > max_page:
                    max_page = num
        if max_page == 1:
            next_btn = soup.select_one(".pagination .next, .page .next")
            if next_btn:
                max_page = 2
        return max_page

    def homeContent(self, filter=False):
        return {"class": self.classes}

    def homeVideoContent(self):
        """首页推荐"""
        html = self._fetch(self.host + "/")
        if not html:
            return {"list": []}
        return {"list": self._parse_comic_list(html)[:20]}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        """分类列表"""
        pg = int(pg) if pg else 1

        if tid == "index":
            url = self.host + "/"
        elif tid == "albums":
            url = self.host + "/albums.html"
        elif tid == "ranking":
            url = self.host + "/albums-favorite_ranking.html"
        elif tid.startswith("cate_"):
            cate_id = tid.replace("cate_", "")
            url = self.host + f"/albums-index-cate-{cate_id}.html"
        else:
            return {"list": [], "page": pg, "pagecount": 1, "limit": 0, "total": 0}

        if pg > 1:
            if "?" in url:
                url += f"&page={pg}"
            else:
                url += f"?page={pg}"

        print(f"[分类] {tid} -> {url}")
        html = self._fetch(url)
        if not html:
            return {"list": [], "page": pg, "pagecount": 1, "limit": 0, "total": 0}

        videos = self._parse_comic_list(html)
        pagecount = self._get_pagination(html) or (pg + 1 if len(videos) >= 20 else pg)

        return {
            "list": videos,
            "page": pg,
            "pagecount": pagecount,
            "limit": len(videos),
            "total": pagecount * 20,
        }

    def detailContent(self, ids):
        """详情页 - 提取所有图片 URL"""
        vid = ids[0] if isinstance(ids, list) else ids

        if not vid.startswith("http"):
            if not vid.startswith("/photos-index-aid-"):
                vid = f"/photos-index-aid-{vid}.html"
            url = self.host + vid
        else:
            url = vid

        print(f"[详情] 请求: {url}")
        html = self._fetch(url)
        if not html:
            return {"list": []}

        soup = BeautifulSoup(html, "html.parser")

        # 标题
        title = ""
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)
        if not title:
            og_title = soup.find("meta", property="og:title")
            if og_title:
                title = og_title.get("content", "")
        if not title:
            title = vid.split("/")[-1].replace(".html", "")

        # 封面
        pic = ""
        og_img = soup.find("meta", property="og:image")
        if og_img:
            pic = og_img.get("content", "")
        if pic:
            pic = self._fix_url(pic)

        # 提取所有图片 URL
        # 该网站使用 reader.m.js 加载图片，图片地址在 <img> 标签的 src 或 data-src 中
        img_urls = []
        # 方法1：从已渲染的 img 标签提取
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src") or ""
            if not src:
                continue
            # 排除非漫画图片
            if "logo" in src.lower() or "loading" in src.lower() or "icon" in src.lower():
                continue
            if "t4.qy0.ru/data/t/" in src or src.startswith("//t4.qy0.ru/data/t/"):
                img_urls.append(self._fix_url(src))

        # 方法2：从 <input id="aid" value="..."> 获取漫画ID，然后构造图片URL
        if not img_urls:
            aid_input = soup.find("input", {"id": "aid"})
            if aid_input:
                aid = aid_input.get("value", "")
                # 从 JS 中提取图片总数
                total_pages = 0
                for script in soup.find_all("script"):
                    content = script.string or ""
                    m = re.search(r"var\s+total\s*=\s*(\d+)", content)
                    if m:
                        total_pages = int(m.group(1))
                        break
                    m = re.search(r'"total_pages":\s*(\d+)', content)
                    if m:
                        total_pages = int(m.group(1))
                        break
                if aid and total_pages:
                    # 构造图片 URL（常见格式）
                    for i in range(1, total_pages + 1):
                        # 实际地址格式可能是 //t4.qy0.ru/data/t/{aid}/{i}.jpg
                        img_urls.append(f"https://t4.qy0.ru/data/t/{aid}/{i}.jpg")

        # 方法3：从 HTML 注释或 JSON 中提取
        if not img_urls:
            # 查找 JSON-LD 或 script 中的图片列表
            for script in soup.find_all("script"):
                content = script.string or ""
                if "images" in content:
                    m = re.search(r'"images"\s*:\s*\[([^\]]+)\]', content)
                    if m:
                        urls = re.findall(r'"([^"]+\.(?:jpg|png|webp))"', m.group(1))
                        for u in urls:
                            img_urls.append(self._fix_url(u))
                        break

        # 去重并过滤
        seen = set()
        unique_urls = []
        for u in img_urls:
            if u and u not in seen:
                seen.add(u)
                unique_urls.append(u)

        print(f"[详情] 提取到 {len(unique_urls)} 张图片")

        if unique_urls:
            play_url = "pics://" + "&&".join(unique_urls)
        else:
            # 如果没有图片，返回详情页 WebView
            play_url = url

        vod = {
            "vod_id": vid,
            "vod_name": title,
            "vod_pic": pic,
            "vod_content": "",
            "vod_play_from": "绅士漫画",
            "vod_play_url": f"全集${play_url}",
        }
        return {"list": [vod]}

    def playerContent(self, flag, id, vipFlags=None):
        """播放"""
        if id and id.startswith("pics://"):
            return {"parse": 0, "playUrl": "", "url": id, "header": ""}
        if id and re.search(r"\.(jpg|png|webp)", id, re.I):
            return {"parse": 0, "playUrl": "", "url": f"pics://{id}", "header": ""}
        return {"parse": 1, "url": id, "header": {"Referer": self.host + "/"}}

    def searchContent(self, key, quick=False, pg="1"):
        pg = int(pg) if pg else 1
        enc_key = quote(key)
        url = self.host + f"/q/?q={enc_key}&page={pg}"
        html = self._fetch(url)
        if not html:
            return {"list": [], "page": pg, "pagecount": 1, "limit": 0, "total": 0}
        videos = self._parse_comic_list(html)
        pagecount = self._get_pagination(html) or (pg + 1 if len(videos) >= 20 else pg)
        return {
            "list": videos,
            "page": pg,
            "pagecount": pagecount,
            "limit": len(videos),
            "total": pagecount * 20,
        }

    def isVideoFormat(self, url):
        return url and (url.startswith("pics://") or re.search(r"\.(jpg|png|webp)", url, re.I))

    def manualVideoCheck(self):
        return False

    def destroy(self):
        if self.session:
            self.session.close()

    def localProxy(self, param):
        return None