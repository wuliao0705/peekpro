# -*- coding: utf-8 -*-
# 无聊自制 · 片源仓库 (分类页合并两页版)
# 每个分类页显示：当前页 + 下一页，合并后返回

import sys
import re
import json
import requests
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def getName(self):
        return "片源仓库"

    def init(self, extend=""):
        self.host = "https://xn--dxtu96arxc.kc3000eiy.sbs"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self.host + "/",
        })
        self.classes = [
            {"type_id": "124", "type_name": "国产视频"},
            {"type_id": "125", "type_name": "中文字幕"},
            {"type_id": "126", "type_name": "国产传媒"},
            {"type_id": "127", "type_name": "日本有码"},
            {"type_id": "128", "type_name": "日本无码"},
            {"type_id": "129", "type_name": "女优明星"},
            {"type_id": "130", "type_name": "强奸乱伦"},
            {"type_id": "131", "type_name": "成人动漫"},
            {"type_id": "132", "type_name": "欧美"},
            {"type_id": "133", "type_name": "其它"},
        ]

    def isVideoFormat(self, url):
        return ".m3u8" in url or ".mp4" in url

    def manualVideoCheck(self):
        return False

    def _fetch(self, url, timeout=12):
        try:
            r = self.session.get(url, timeout=timeout)
            r.encoding = "utf-8"
            return r.text
        except Exception as e:
            print(f"[片源仓库] 请求失败: {url} -> {e}")
            return ""

    def _abs_url(self, url):
        if not url:
            return ""
        if url.startswith(("http://", "https://")):
            return url
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.host + url
        return self.host + "/" + url

    def _clean(self, text):
        if not text:
            return ""
        return re.sub(r"\s+", " ", text.strip())

    # ---------- 分类 ----------
    def homeContent(self, filter=False):
        return {"class": self.classes}

    def homeVideoContent(self):
        html = self._fetch(self.host + "/")
        if not html:
            return {"list": []}
        videos = self._parse_video_cards(html)
        return {"list": videos[:24]}

    # ---------- 列表解析 ----------
    def _parse_video_cards(self, html):
        videos = []
        seen = set()
        pattern = r'<article\s+class="video-card">\s*<a\s+class="video-link"\s+href="([^"]+)"\s+title="([^"]*)"[\s\S]*?<img\s+src="([^"]+)"[\s\S]*?<em\s+class="duration">([^<]*)</em>[\s\S]*?<h3>([^<]*)</h3>[\s\S]*?<p><span>([^<]*)</span>'
        for m in re.finditer(pattern, html, re.S):
            href = m.group(1)
            title = self._clean(m.group(2) or m.group(5) or "")
            pic = m.group(3)
            duration = self._clean(m.group(4) or "")
            category = self._clean(m.group(6) or "")

            if not href or not title:
                continue

            vid_match = re.search(r'/id/(\d+)/', href)
            vod_id = vid_match.group(1) if vid_match else href

            if vod_id in seen:
                continue
            seen.add(vod_id)

            pic = self._abs_url(pic)

            videos.append({
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": f"{duration} | {category}" if duration else category,
            })

        return videos

    # ---------- 分类页：合并当前页 + 下一页 ----------
    def categoryContent(self, tid, pg, filter=False, extend=None):
        pg = int(pg) if pg else 1

        # 构建当前页和下一页的URL
        def build_url(page):
            if page == 1:
                return f"{self.host}/index.php/vod/type/id/{tid}.html"
            else:
                return f"{self.host}/index.php/vod/type/id/{tid}/page/{page}.html"

        urls = [build_url(pg)]
        # 如果 pg+1 存在，也请求（但有些网站最后一页可能没有，没关系）
        urls.append(build_url(pg + 1))

        # 并发请求两页
        all_videos = []
        seen = set()
        pagecount = pg

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_to_url = {executor.submit(self._fetch, url): url for url in urls}
            for future in as_completed(future_to_url):
                html = future.result()
                if html:
                    videos = self._parse_video_cards(html)
                    for v in videos:
                        vid = v.get("vod_id")
                        if vid and vid not in seen:
                            seen.add(vid)
                            all_videos.append(v)
                    # 从返回的HTML中提取总页数
                    page_links = re.findall(r'/page/(\d+)\.html', html)
                    if page_links:
                        try:
                            max_p = max([int(x) for x in page_links])
                            if max_p > pagecount:
                                pagecount = max_p
                        except:
                            pass

        # 如果合并后视频少于20条，说明下一页可能没有数据，只保留当前页
        # 但实际合并后通常会有40条左右
        if len(all_videos) < 20:
            # 只取当前页
            html = self._fetch(build_url(pg))
            if html:
                all_videos = self._parse_video_cards(html)
                page_links = re.findall(r'/page/(\d+)\.html', html)
                if page_links:
                    try:
                        pagecount = max([int(x) for x in page_links])
                    except:
                        pass
            if not all_videos:
                all_videos = []

        # 如果 pagecount 小于 pg+1，说明已经到了最后一页
        if pagecount < pg + 1:
            pagecount = pg

        return {
            "list": all_videos,
            "page": pg,
            "pagecount": max(pagecount, pg),
            "limit": len(all_videos),
            "total": max(pagecount, pg) * 20,
        }

    # ---------- 详情/播放 ----------
    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vod_id = ids[0]

        url = f"{self.host}/index.php/vod/play/id/{vod_id}/sid/1/nid/1.html"
        html = self._fetch(url)
        if not html:
            return {"list": []}

        title = ""
        title_match = re.search(r'<title>(.*?)</title>', html)
        if title_match:
            title = self._clean(title_match.group(1).split("-")[0])
        if not title:
            title_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
            if title_match:
                title = self._clean(title_match.group(1))

        pic = ""
        pic_match = re.search(r'<img[^>]+src="([^"]+)"[^>]+class="[^"]*thumb[^"]*"', html)
        if pic_match:
            pic = self._abs_url(pic_match.group(1))
        if not pic:
            pic_match = re.search(r'<div\s+class="thumb">\s*<img[^>]+src="([^"]+)"', html, re.S)
            if pic_match:
                pic = self._abs_url(pic_match.group(1))

        play_url = self._extract_play_url(html)

        vod = {
            "vod_id": vod_id,
            "vod_name": title or f"视频{vod_id}",
            "vod_pic": pic,
            "vod_content": "",
            "vod_play_from": "片源仓库",
            "vod_play_url": f"第1集${play_url}" if play_url else "",
        }

        return {"list": [vod]}

    def _extract_play_url(self, html):
        match = re.search(r'var\s+player_aaaa\s*=\s*(\{.*?\})\s*;', html, re.S)
        if match:
            try:
                data = json.loads(match.group(1))
                url = data.get("url", "")
                if url:
                    return "https:" + url if url.startswith("//") else url
            except:
                pass

        match = re.search(r'player_data\s*=\s*(\{.*?\})\s*;', html, re.S)
        if match:
            try:
                data = json.loads(match.group(1))
                url = data.get("url", "")
                if url:
                    return "https:" + url if url.startswith("//") else url
            except:
                pass

        match = re.search(r'<video[^>]+src="([^"]+)"', html)
        if match:
            url = match.group(1)
            return "https:" + url if url.startswith("//") else url

        match = re.search(r'<source[^>]+src="([^"]+)"', html)
        if match:
            url = match.group(1)
            return "https:" + url if url.startswith("//") else url

        match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html)
        if match:
            return match.group(1)

        match = re.search(r'<iframe[^>]+src="([^"]+)"', html)
        if match:
            iframe_url = match.group(1)
            if not iframe_url.startswith("http"):
                iframe_url = self._abs_url(iframe_url)
            iframe_html = self._fetch(iframe_url)
            if iframe_html:
                return self._extract_play_url(iframe_html)

        return ""

    def playerContent(self, flag, id, vipFlags=None):
        result = {"parse": 0, "playUrl": "", "url": "", "header": {}}

        if "/vod/play/" in id or "id=" in id:
            detail = self.detailContent([id])
            if detail.get("list"):
                vod = detail["list"][0]
                play_str = vod.get("vod_play_url", "")
                if play_str and "$" in play_str:
                    result["url"] = play_str.split("$", 1)[1]
                else:
                    result["url"] = play_str
            else:
                result["url"] = id
        else:
            result["url"] = id

        result["header"] = {
            "User-Agent": "Mozilla/5.0",
            "Referer": self.host + "/",
        }
        return result

    def searchContent(self, key, quick=False, pg="1"):
        pg = int(pg) if pg else 1
        enc_key = quote(key)
        url = f"{self.host}/index.php/vod/search.html?wd={enc_key}"
        if pg > 1:
            url += f"&page={pg}"

        html = self._fetch(url)
        if not html:
            return {"list": [], "page": pg, "pagecount": 1, "limit": 0, "total": 0}

        videos = self._parse_video_cards(html)

        pagecount = pg
        page_links = re.findall(r'/page/(\d+)\.html', html)
        if page_links:
            try:
                pagecount = max([int(x) for x in page_links])
            except:
                pass
        elif len(videos) >= 20:
            pagecount = pg + 1

        return {
            "list": videos,
            "page": pg,
            "pagecount": max(pagecount, pg),
            "limit": len(videos),
            "total": max(pagecount, pg) * 20,
        }

    def localProxy(self, param):
        pass
