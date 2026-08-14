# -*- coding: utf-8 -*-
# TVBox爬虫 - 蛋蛋ASMR音声（修复版）
# 站点: https://a.asmregg.top

import sys
import re
import json
import requests
from urllib.parse import urljoin, quote

sys.path.append('..')
from base.spider import Spider as BaseSpider


class Spider(BaseSpider):
    def init(self, extend=""):
        self.host = "https://a.asmregg.top"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": self.host + "/",
        })
        self.debug = True

        if extend:
            try:
                cfg = json.loads(extend) if isinstance(extend, str) else extend
                if isinstance(cfg, dict):
                    host = cfg.get("host")
                    if host:
                        self.host = host.rstrip("/")
                        self.session.headers["Referer"] = self.host + "/"
            except Exception:
                pass

    def _log(self, msg):
        if self.debug:
            print(f"[ASMR] {msg}")

    def _fetch(self, url):
        try:
            self._log(f"请求: {url}")
            resp = self.session.get(url, timeout=15)
            resp.encoding = 'utf-8'
            if resp.status_code == 200:
                return resp.text
            return None
        except Exception as e:
            self._log(f"请求失败: {e}")
            return None

    def _fix_url(self, url):
        if not url:
            return ""
        url = str(url).strip()
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return urljoin(self.host, url)
        if url.startswith("http"):
            return url
        return urljoin(self.host, "/" + url)

    def _clean_text(self, text):
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()

    # ========== 解析首页作者列表 ==========
    def _parse_authors(self, html):
        authors = []
        if not html:
            return authors

        # 匹配作者卡片
        pattern = r'<div class="p-2">.*?<a[^>]+href="([^"]+)"[^>]*>.*?<img[^>]+src="([^"]+)"[^>]*>.*?</a>.*?<div class="text-center font-semibold">.*?<a[^>]+href="[^"]+"[^>]*>([^<]+)</a>.*?</div>'
        matches = re.findall(pattern, html, re.S)

        for match in matches:
            try:
                href, pic, name = match
                vid = self._fix_url(href)
                pic = self._fix_url(pic)
                if "none.png" in pic:
                    pic = ""
                authors.append({
                    "vod_id": vid,
                    "vod_name": self._clean_text(name),
                    "vod_pic": pic,
                    "vod_remarks": "",
                })
            except Exception:
                continue

        self._log(f"解析到 {len(authors)} 个作者")
        return authors

    # ========== 解析作者页面的音频列表 ==========
    def _parse_audio_list(self, html):
        """从作者页面解析所有音频，返回列表"""
        audios = []
        if not html:
            return audios

        # 方法1：从 audios 数组提取（JS 变量）
        m = re.search(r'audios\s*=\s*(\[.*?\]);', html, re.S)
        if m:
            try:
                data = json.loads(m.group(1))
                for item in data:
                    name = item.get("name", "")
                    url = item.get("url", "")
                    if name and url:
                        audios.append({
                            "name": self._clean_text(name),
                            "url": self._fix_url(url)
                        })
                self._log(f"从 audios 数组提取到 {len(audios)} 个音频")
                return audios
            except Exception as e:
                self._log(f"解析 audios 数组失败: {e}")

        # 方法2：从 <ol> 下载链接列表提取（备用）
        # 结构: <ol class="text-gray-500"> <li><a href="...mp3" ...>名称</a></li> ... </ol>
        pattern = r'<ol[^>]*>.*?<li[^>]*>.*?<a[^>]+href="([^"]+\.mp3[^"]*)"[^>]*>([^<]+)</a>.*?</li>'
        matches = re.findall(pattern, html, re.S)
        if matches:
            for url, name in matches:
                audios.append({
                    "name": self._clean_text(name),
                    "url": self._fix_url(url)
                })
            self._log(f"从 <ol> 列表提取到 {len(audios)} 个音频")
            return audios

        return audios

    # ========== TVBox 接口 ==========

    def homeContent(self, filter=False):
        """首页分类：作者列表"""
        html = self._fetch(self.host + "/")
        if not html:
            return {"class": [{"type_id": "all", "type_name": "全部作品"}]}

        authors = self._parse_authors(html)
        classes = []
        for author in authors[:50]:
            vid = author["vod_id"]
            name = author["vod_name"]
            if vid and name:
                classes.append({"type_id": vid, "type_name": name})

        # 添加"全部"分类
        classes.insert(0, {"type_id": "all", "type_name": "全部作者"})
        return {"class": classes}

    def homeVideoContent(self):
        """首页推荐：显示前20个作者"""
        html = self._fetch(self.host + "/")
        authors = self._parse_authors(html)
        return {"list": authors[:20]}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        """分类内容：
           - 如果 tid == "all"，显示所有作者（首页分页）
           - 否则 tid 是作者页 URL，显示该作者的所有音频
        """
        try:
            pg = int(pg) if pg else 1

            # ---------- 全部作者 ----------
            if tid == "all":
                if pg == 1:
                    url = self.host + "/"
                else:
                    url = self.host + f"/page/{pg}/"
                html = self._fetch(url)
                if not html:
                    return {"list": [], "page": pg, "pagecount": 1}

                videos = self._parse_authors(html)

                # 提取总页数
                pagecount = pg
                last_match = re.search(r'<a[^>]+href="[^"]*/page/(\d+)/"[^>]*>.*?</a>', html)
                if last_match:
                    pagecount = int(last_match.group(1))
                else:
                    m = re.search(r'共\s*<span[^>]*>\s*(\d+)\s*</span>\s*页', html)
                    if m:
                        pagecount = int(m.group(1))
                    elif len(videos) >= 20:
                        pagecount = pg + 1

                return {
                    "list": videos,
                    "page": pg,
                    "pagecount": pagecount,
                    "limit": len(videos),
                    "total": pagecount * 20
                }

            # ---------- 单个作者 ----------
            # tid 是作者页 URL，如 https://a.asmregg.top/plays/柳柳/
            html = self._fetch(tid)
            if not html:
                return {"list": [], "page": pg, "pagecount": 1}

            audios = self._parse_audio_list(html)

            # 构造视频列表
            videos = []
            for audio in audios:
                videos.append({
                    "vod_id": audio["url"],          # 直接使用 MP3 URL
                    "vod_name": audio["name"],
                    "vod_pic": "",
                    "vod_remarks": "",
                })

            # 作者页通常没有分页，所有音频都在一页
            pagecount = pg
            if len(videos) >= 20:
                pagecount = pg + 1

            return {
                "list": videos,
                "page": pg,
                "pagecount": pagecount,
                "limit": len(videos),
                "total": len(videos)
            }
        except Exception as e:
            self._log(f"分类内容失败: {e}")
            import traceback
            traceback.print_exc()
            return {"list": [], "page": pg, "pagecount": 1}

    def detailContent(self, ids):
        """详情（对于音频，直接返回播放地址）"""
        try:
            vid = ids[0]
            # 如果 vid 是 MP3 URL，直接返回
            if vid.startswith("http") and (".mp3" in vid or ".m4a" in vid):
                return {
                    "list": [{
                        "vod_id": vid,
                        "vod_name": "音频",
                        "vod_pic": "",
                        "vod_play_from": "ASMR音声",
                        "vod_play_url": f"播放${vid}",
                    }]
                }

            # 否则当作页面 URL 重新提取
            html = self._fetch(vid)
            if not html:
                return {"list": []}

            # 尝试提取标题
            title = ""
            m = re.search(r'<title>([^<]+)</title>', html)
            if m:
                title = self._clean_text(m.group(1))

            # 提取音频列表
            audios = self._parse_audio_list(html)
            if not audios:
                return {"list": []}

            # 如果有多个音频，拼接播放地址
            play_url = "#".join([f"{a['name']}${a['url']}" for a in audios])

            vod = {
                "vod_id": vid,
                "vod_name": title or "未知音声",
                "vod_pic": "",
                "vod_content": "",
                "vod_play_from": "ASMR音声",
                "vod_play_url": play_url,
            }
            return {"list": [vod]}
        except Exception as e:
            self._log(f"详情失败: {e}")
            return {"list": []}

    def searchContent(self, key, quick=False, pg="1"):
        """搜索"""
        try:
            pg = int(pg) if pg else 1
            enc_key = quote(key)

            if pg == 1:
                url = f"{self.host}/search/?kw={enc_key}"
            else:
                url = f"{self.host}/search/?kw={enc_key}&page={pg}"

            html = self._fetch(url)
            if not html:
                return {"list": [], "page": pg, "pagecount": 1}

            # 搜索结果可能返回作者列表或音频列表
            videos = self._parse_authors(html)
            if not videos:
                # 尝试解析音频
                audios = self._parse_audio_list(html)
                for audio in audios:
                    videos.append({
                        "vod_id": audio["url"],
                        "vod_name": audio["name"],
                        "vod_pic": "",
                        "vod_remarks": "",
                    })

            pagecount = pg
            if len(videos) >= 20:
                pagecount = pg + 1

            return {
                "list": videos,
                "page": pg,
                "pagecount": pagecount,
                "limit": len(videos),
                "total": pagecount * 20
            }
        except Exception as e:
            self._log(f"搜索失败: {e}")
            return {"list": [], "page": pg, "pagecount": 1}

    def playerContent(self, flag, id, vipFlags=None):
        """播放 - 直接返回 MP3 URL"""
        try:
            if not id:
                return {"parse": 0, "url": "", "header": {}}

            # 如果是 MP3 直链，直接返回
            if id.startswith("http") and (".mp3" in id or ".m4a" in id):
                return {
                    "parse": 0,
                    "url": id,
                    "header": {}  # 空字典，避免 JSON 序列化错误
                }

            # 否则当作页面 URL，尝试提取音频
            html = self._fetch(id)
            if html:
                audios = self._parse_audio_list(html)
                if audios:
                    # 取第一个音频播放
                    mp3_url = audios[0].get("url")
                    if mp3_url:
                        return {
                            "parse": 0,
                            "url": mp3_url,
                            "header": {}
                        }

            # 最后尝试直接返回 id
            return {"parse": 1, "url": id, "header": {}}
        except Exception as e:
            self._log(f"播放失败: {e}")
            return {"parse": 1, "url": id, "header": {}}

    def localProxy(self, param):
        """本地代理（图片/音频）"""
        try:
            if not isinstance(param, dict):
                return None

            url = param.get("url") or param.get("pic") or ""
            if not url:
                return [404, "text/plain", b""]

            if url.startswith("/"):
                url = self.host + url
            elif url.startswith("//"):
                url = "https:" + url

            headers = {
                "User-Agent": self.session.headers["User-Agent"],
                "Referer": self.host + "/",
            }
            r = self.session.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                return [r.status_code, "text/plain", b""]

            content_type = r.headers.get("Content-Type", "")
            if "image" not in content_type:
                if ".jpg" in url or ".jpeg" in url or ".png" in url or ".webp" in url:
                    content_type = "image/jpeg"
                elif ".mp3" in url:
                    content_type = "audio/mpeg"
                else:
                    content_type = "application/octet-stream"
            return [200, content_type, r.content]
        except Exception as e:
            self._log(f"代理异常: {e}")
            return [500, "text/plain", str(e).encode()]

    def isVideoFormat(self, url):
        return any(x in url for x in [".mp3", ".m4a", ".m3u8"])

    def manualVideoCheck(self):
        return False

    def destroy(self):
        if self.session:
            self.session.close()