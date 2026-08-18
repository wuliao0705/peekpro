# -*- coding: utf-8 -*-
# 易听书网 (yitingshu.com) - TVBox 音频爬虫（修复版）

import re
import json
import requests
import time
import random
from urllib.parse import quote, urljoin
from base.spider import Spider
from bs4 import BeautifulSoup


class Spider(Spider):
    def getName(self):
        return "易听书网"

    def init(self, extend=""):
        self.host = "https://www.yitingshu.com"
        self.session = requests.Session()
        # 随机User-Agent池
        self.ua_list = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        self.session.headers.update({
            "User-Agent": random.choice(self.ua_list),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self.host + "/",
        })
        # 分类映射（从导航栏提取）
        self.class_map = {
            "言情": "1",
            "武侠": "2",
            "悬疑": "3",
            "历史": "4",
            "军事": "5",
            "评书": "6",
            "相声小品": "7",
            "商业财经": "9",
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

    def _fetch(self, url, timeout=15, retry=2):
        """带重试的请求"""
        for i in range(retry):
            try:
                # 每次请求随机UA
                self.session.headers.update({"User-Agent": random.choice(self.ua_list)})
                resp = self.session.get(url, timeout=timeout)
                if resp.status_code == 200:
                    resp.encoding = "utf-8"
                    return resp.text
                elif resp.status_code == 403:
                    print(f"[{self.getName()}] 403 Forbidden, 尝试更换UA")
                    continue
                return ""
            except Exception as e:
                print(f"[{self.getName()}] 请求失败 (尝试 {i+1}/{retry}): {e}")
                time.sleep(1)
        return ""

    # ==================== 首页分类 ====================

    def homeContent(self, filter=False):
        classes = [{"type_id": v, "type_name": k} for k, v in self.class_map.items()]
        return {"class": classes}

    # ==================== 首页推荐 ====================

    def homeVideoContent(self):
        try:
            html = self._fetch("/")
            if not html:
                return {"list": []}
            audios = self._extract_audios(html)
            return {"list": audios[:30]}
        except Exception as e:
            print(f"[{self.getName()}] homeVideoContent 异常: {e}")
            return {"list": []}

    # ==================== 音频提取（增强版） ====================

    def _extract_audios(self, html, is_search=False):
        """提取音频列表（首页、分类、搜索通用）- 增强选择器"""
        soup = BeautifulSoup(html, "html.parser")
        audios = []
        seen = set()

        # 方法1：标准列表项
        items = soup.select(".stui-vodlist li")
        if not items:
            # 方法2：查找任何带有stui-vodlist__box的父容器
            items = soup.select(".stui-vodlist__box")
            if not items:
                # 方法3：查找所有包含封面和标题的卡片
                items = soup.select(".stui-vodlist__thumb, .stui-vodlist__detail")

        # 如果仍然没有，尝试从页面中提取所有a标签（兜底）
        if not items:
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                if "/tingshu/" in href and a.find_parent("li"):
                    items.append(a.find_parent("li"))

        print(f"[{self.getName()}] 找到 {len(items)} 个列表项")

        for li in items:
            # 如果是直接选择的卡片，可能是a标签本身
            if li.name == "a" and li.get("href", "").startswith("/tingshu/"):
                a = li
                # 尝试找封面
                img = a.find("img")
                pic = img.get("data-original", "") if img else ""
                href = a.get("href", "")
                title = a.get("title", "")
                # 找详细信息的容器
                detail = a.find_next_sibling("div", class_="stui-vodlist__detail") or a.find("div", class_="stui-vodlist__detail")
                if detail:
                    title_a = detail.find("h4").find("a") if detail.find("h4") else None
                    if title_a:
                        title = title_a.get_text(strip=True)
            else:
                # 标准li处理
                thumb = li.find("a", class_="stui-vodlist__thumb")
                if thumb:
                    pic = thumb.get("data-original", "") or thumb.get("src", "")
                    href = thumb.get("href", "")
                    title = thumb.get("title", "")
                else:
                    # 无thumb，直接找a
                    a = li.find("a", href=True)
                    if not a:
                        continue
                    href = a.get("href", "")
                    title = a.get_text(strip=True) or a.get("title", "")
                    pic = ""
                    img = a.find("img")
                    if img:
                        pic = img.get("data-original", "") or img.get("src", "")

            if "/tingshu/" not in href:
                continue
            m = re.search(r"/tingshu/(\d+)\.html", href)
            vod_id = m.group(1) if m else ""
            if not vod_id or vod_id in seen:
                continue
            seen.add(vod_id)

            # 尝试从detail获取标题和作者
            detail = li.find("div", class_="stui-vodlist__detail") if li.name != "a" else li.find_next_sibling("div", class_="stui-vodlist__detail")
            if detail:
                title_a = detail.find("h4").find("a") if detail.find("h4") else None
                if title_a:
                    title = title_a.get_text(strip=True)
                author = detail.find("p", class_="text-muted")
                author_text = author.get_text(strip=True) if author else ""

            # 备注
            remarks = ""
            if thumb:
                pic_text = thumb.find("span", class_="pic-text")
                if pic_text:
                    remarks = pic_text.get_text(strip=True)
            if not remarks and detail:
                # 尝试从其他位置提取状态
                status = detail.find("span", class_="status")
                if status:
                    remarks = status.get_text(strip=True)

            if pic and not pic.startswith("http"):
                pic = self._fix_url(pic)

            audios.append({
                "vod_id": vod_id,
                "vod_name": title or f"音频{vod_id}",
                "vod_pic": pic,
                "vod_remarks": remarks or author_text if 'author_text' in locals() else "",
            })

        print(f"[{self.getName()}] 解析到 {len(audios)} 条数据")
        return audios

    def _extract_pagecount(self, html):
        """提取总页数"""
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.select(".page a, .pagination a"):
            if "尾页" in a.get_text() or "末页" in a.get_text():
                href = a.get("href", "")
                m = re.search(r"page[/=](\d+)", href)
                if m:
                    try:
                        return int(m.group(1))
                    except:
                        pass
        # 查找页码数字
        for a in soup.select(".page a, .pagination a"):
            text = a.get_text(strip=True)
            if text.isdigit() and int(text) > 10:
                try:
                    return int(text)
                except:
                    pass
        return 1

    # ==================== 分类列表 ====================

    def categoryContent(self, tid, pg, filter=False, extend=None):
        try:
            pg = int(pg) if str(pg).isdigit() else 1

            # 尝试多种URL格式
            urls = [
                f"{self.host}/yi/{tid}-{pg}.html",
                f"{self.host}/list/{tid}-{pg}.html",
                f"{self.host}/category/{tid}-{pg}.html",
                f"{self.host}/yi/{tid}.html?page={pg}",
            ]
            html = ""
            for url in urls:
                print(f"[{self.getName()}] 尝试请求: {url}")
                html = self._fetch(url)
                if html and len(html) > 500:
                    print(f"[{self.getName()}] 成功获取页面: {url}")
                    break

            if not html:
                return {"list": [], "page": pg, "pagecount": 1, "limit": 24, "total": 0}

            audios = self._extract_audios(html)
            pagecount = self._extract_pagecount(html)

            return {
                "list": audios,
                "page": pg,
                "pagecount": pagecount if pagecount > 1 else pg + 1,
                "limit": 24,
                "total": pagecount * 24 if pagecount > 1 else len(audios),
            }
        except Exception as e:
            print(f"[{self.getName()}] categoryContent 异常: {e}")
            import traceback
            traceback.print_exc()
            return {"list": [], "page": pg, "pagecount": 1, "limit": 24, "total": 0}

    # ==================== 详情页 ====================

    def detailContent(self, ids):
        try:
            vod_id = ids[0]
            if "/tingshu/" in vod_id:
                m = re.search(r"/tingshu/(\d+)\.html", vod_id)
                if m:
                    vod_id = m.group(1)

            url = f"{self.host}/tingshu/{vod_id}.html"
            html = self._fetch(url)
            if not html:
                return {"list": []}

            soup = BeautifulSoup(html, "html.parser")

            # 标题
            title = ""
            title_h1 = soup.select_one(".stui-content__detail h1.title")
            if title_h1:
                title = title_h1.get_text(strip=True)
            if not title:
                title_match = re.search(r"<title>(.*?)</title>", html)
                if title_match:
                    title = title_match.group(1).strip()

            # 封面
            pic = ""
            thumb = soup.select_one(".stui-content__thumb img")
            if thumb:
                pic = thumb.get("data-original", "") or thumb.get("src", "")
            pic = self._fix_url(pic)

            # 作者/主播
            author = ""
            detail = soup.select_one(".stui-content__detail")
            if detail:
                for p in detail.find_all("p", class_="data"):
                    text = p.get_text(strip=True)
                    if "作者" in text or "主播" in text:
                        author = text.replace("作者：", "").replace("主播：", "").strip()
                        break

            # 简介
            intro = ""
            desc_div = soup.find("div", id="desc")
            if desc_div:
                intro = desc_div.get_text(strip=True)

            # 提取章节列表（集数）
            chapters = []
            playlist = soup.select_one(".stui-content__playlist")
            if playlist:
                for li in playlist.find_all("li"):
                    a = li.find("a")
                    if a:
                        href = a.get("href", "")
                        name = a.get_text(strip=True)
                        if href:
                            chapters.append({
                                "name": name or f"第{len(chapters)+1}集",
                                "url": self._fix_url(href)
                            })

            # 构建播放地址
            if chapters:
                play_url = "#".join([f"{item['name']}${item['url']}" for item in chapters])
            else:
                play_url = f"第1集${url}"

            return {
                "list": [{
                    "vod_id": vod_id,
                    "vod_name": title or f"音频{vod_id}",
                    "vod_pic": pic,
                    "vod_content": f"作者/主播：{author}\n{intro}" if author else intro,
                    "vod_play_from": "音频集",
                    "vod_play_url": play_url,
                }]
            }
        except Exception as e:
            print(f"[{self.getName()}] detailContent 异常: {e}")
            return {"list": []}

    # ==================== 播放（提取音频地址） ====================

    def playerContent(self, flag, id, vipFlags=None):
        try:
            result = {"parse": 0, "playUrl": "", "url": "", "header": {}}
            if not id or id == "#":
                return result

            if id.startswith("http") and (".mp3" in id or ".m4a" in id or ".aac" in id or ".ogg" in id or ".m3u8" in id):
                result["url"] = id
                result["header"] = {
                    "Referer": self.host + "/",
                    "User-Agent": self.session.headers.get("User-Agent", "Mozilla/5.0"),
                }
                return result

            if "/tingshu/" in id or "/play/" in id:
                if not id.startswith("http"):
                    id = self._fix_url(id)
                html = self._fetch(id)
                if html:
                    audio_url = None
                    # 多种提取方式
                    patterns = [
                        r'var\s+now\s*=\s*["\']([^"\']+\.(?:mp3|m4a|aac|ogg|m3u8)[^"\']*)["\']',
                        r'var\s+url\s*=\s*["\']([^"\']+\.(?:mp3|m4a|aac|ogg|m3u8)[^"\']*)["\']',
                        r'var\s+src\s*=\s*["\']([^"\']+\.(?:mp3|m4a|aac|ogg|m3u8)[^"\']*)["\']',
                        r'var\s+mp3\s*=\s*["\']([^"\']+\.(?:mp3|m4a|aac|ogg|m3u8)[^"\']*)["\']',
                        r'var\s+link\s*=\s*["\']([^"\']+\.(?:mp3|m4a|aac|ogg|m3u8)[^"\']*)["\']',
                        r'<source[^>]+src=["\']([^"\']+\.(?:mp3|m4a|aac|ogg|m3u8)[^"\']*)["\']',
                        r'<audio[^>]+src=["\']([^"\']+\.(?:mp3|m4a|aac|ogg|m3u8)[^"\']*)["\']',
                        r'(https?://[^\s"\'<>]+\.(?:mp3|m4a|aac|ogg|m3u8)[^\s"\'<>]*)',
                    ]
                    for pat in patterns:
                        m = re.search(pat, html)
                        if m:
                            audio_url = m.group(1)
                            break

                    if audio_url:
                        if audio_url.startswith("//"):
                            audio_url = "https:" + audio_url
                        elif audio_url.startswith("/"):
                            audio_url = self._fix_url(audio_url)
                        elif not audio_url.startswith("http"):
                            audio_url = self._fix_url(audio_url)
                        result["url"] = audio_url
                        result["header"] = {
                            "Referer": self.host + "/",
                            "User-Agent": self.session.headers.get("User-Agent", "Mozilla/5.0"),
                        }
                        return result

            if id.startswith("/"):
                id = self._fix_url(id)
                result["url"] = id
                result["header"] = {
                    "Referer": self.host + "/",
                    "User-Agent": self.session.headers.get("User-Agent", "Mozilla/5.0"),
                }
                return result

            result["url"] = id
            result["header"] = {
                "Referer": self.host + "/",
                "User-Agent": self.session.headers.get("User-Agent", "Mozilla/5.0"),
            }
            return result
        except Exception as e:
            print(f"[{self.getName()}] playerContent 异常: {e}")
            return {"parse": 0, "playUrl": "", "url": id if id else "", "header": {}}

    # ==================== 搜索 ====================

    def searchContent(self, key, quick=False, pg="1"):
        try:
            pg = int(pg) if str(pg).isdigit() else 1
            enc_key = quote(key)
            url = f"{self.host}/search.php?searchword={enc_key}&page={pg}"
            html = self._fetch(url)
            if not html:
                return {"list": [], "page": pg, "pagecount": 1, "limit": 24, "total": 0}

            audios = self._extract_audios(html, is_search=True)
            pagecount = self._extract_pagecount(html)

            return {
                "list": audios,
                "page": pg,
                "pagecount": pagecount if pagecount > 1 else pg + 1,
                "limit": 24,
                "total": pagecount * 24 if pagecount > 1 else len(audios),
            }
        except Exception as e:
            print(f"[{self.getName()}] searchContent 异常: {e}")
            return {"list": [], "page": pg, "pagecount": 1, "limit": 24, "total": 0}

    def isVideoFormat(self, url):
        audio_formats = [".mp3", ".m4a", ".aac", ".ogg", ".m3u8"]
        return url and any(fmt in url for fmt in audio_formats)

    def manualVideoCheck(self):
        return False

    def destroy(self):
        if self.session:
            self.session.close()