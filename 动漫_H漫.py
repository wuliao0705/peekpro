# -*- coding: utf-8 -*-
# 无聊自制 · 凑合用吧
# 官网: https://hanime1.me

import sys, re, json
from urllib.parse import quote
sys.path.append('..')

try:
    from base.spider import Spider as _Base
except ImportError:
    # 没基类就自己硬怼
    class _Base:
        def fetch(self, url, headers=None, **kw):
            import requests as rq
            kw.pop('timeout', None)
            r = rq.get(url, headers=headers, timeout=15, **kw)
            r.encoding = 'utf-8'
            return r

import requests as req

# 域名硬编码，懒得搞
BASE = "https://hanime1.me"
# 浏览器标识，防屏蔽
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


class Spider(_Base):
    def init(self, extend=""):
        self._s = req.Session()
        self._s.headers.update({
            "User-Agent": UA,
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": BASE,
        })
        self._debug = False   # 想看点日志就改成 True

    def getName(self):
        return "Hanime1"   # 名字随便取

    def isVideoFormat(self, url):
        return ".mp4" in url or ".m3u8" in url

    def manualVideoCheck(self):
        return False   # 懒得手动检查

    # 打印调试
    def _log(self, msg):
        if self._debug:
            print(f"[H1] {msg}")

    # 发请求，失败就返回空
    def _req(self, url, timeout=15):
        if not url.startswith("http"):
            url = BASE + url
        self._log(f"请求 -> {url}")
        try:
            r = self._s.get(url, timeout=timeout)
            r.raise_for_status()
            r.encoding = 'utf-8'
            return r.text
        except Exception as e:
            self._log(f"炸了: {e}")
            return ""

    # 从首页扒分类（全自动，省得手动写死）
    def _get_genres(self):
        html = self._req(BASE)
        if not html:
            # 万一首页都挂了，就给个默认列表
            return ["裏番", "泡麵番", "Motion Anime", "3DCG", "2.5D", "2D動畫", "AI生成", "MMD", "Cosplay"]
        # 匹配导航里的 ?genre=xxx
        genres = re.findall(r'href="[^"]*genre=([^&"]+)"', html)
        # 去重
        seen = set()
        return [x for x in genres if not (x in seen or seen.add(x))]

    # 解析视频卡片（纯正则，不求人）
    def _parse_cards(self, html):
        videos = []
        seen = set()
        # 匹配 <a href="/watch?v=数字"> ... 图片 ... 标题
        pat = re.compile(
            r'<a[^>]*href="(/watch\?v=\d+)"[^>]*>.*?'
            r'<img[^>]*src="([^"]+)"[^>]*>.*?'
            r'<div[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</div>',
            re.DOTALL | re.IGNORECASE
        )
        for href, pic, title in pat.findall(html):
            if href in seen:
                continue
            seen.add(href)
            m = re.search(r'v=(\d+)', href)
            if not m:
                continue
            # 补全图片地址
            if not pic.startswith("http"):
                pic = "https:" + pic if pic.startswith("//") else BASE + pic
            videos.append({
                "vod_id": m.group(1),
                "vod_name": title.strip(),
                "vod_pic": pic,
                "vod_remarks": "",
            })
        return videos

    # 首页分类列表
    def homeContent(self, filter=False):
        classes = [{"type_id": "__all__", "type_name": "全部影片"}]
        for g in self._get_genres():
            classes.append({"type_id": g, "type_name": g})
        return {"class": classes}

    # 首页随便推点
    def homeVideoContent(self):
        html = self._req(BASE)
        return {"list": self._parse_cards(html)}

    # 分类列表（关键：用 genre 而不是 tags[]）
    def categoryContent(self, tid, pg=1, filter=False, extend=None):
        try:
            pn = max(int(str(pg)), 1)
            if tid == "__all__":
                url = f"{BASE}/search?page={pn}"
            else:
                # 注意这里用的是 genre，原版是 tags[] 是错的
                url = f"{BASE}/search?genre={quote(tid)}&page={pn}"
            html = self._req(url)
            if not html:
                return {"list": [], "page": pn, "pagecount": 1}
            # 估算总页数
            pages = re.findall(r'page=(\d+)', html)
            pc = max(int(x) for x in pages) if pages else pn
            v = self._parse_cards(html)
            return {
                "list": v,
                "page": pn,
                "pagecount": pc,
                "limit": len(v),
                "total": pc * (len(v) or 20)
            }
        except Exception as e:
            self._log(f"分类列表炸了: {e}")
            return {"list": [], "page": pg, "pagecount": 1}

    # 详情（多清晰度）
    def detailContent(self, ids):
        vid = ids[0]
        if not vid.startswith("http"):
            url = f"{BASE}/watch?v={vid}"
        else:
            url = vid
        html = self._req(url)
        if not html:
            return {"list": []}

        # 标题
        title_match = re.search(r'<title>(.*?)</title>', html)
        title = title_match.group(1).split(" - ")[0].strip() if title_match else "未知"

        # 封面（先找 poster 属性，再找 img）
        poster = re.search(r'poster="([^"]+)"', html)
        pic = poster.group(1) if poster else ""
        if not pic:
            img = re.search(r'<img[^>]*class="[^"]*main-thumb[^"]*"[^>]*src="([^"]+)"', html)
            pic = img.group(1) if img else ""

        # 多分辨率 source
        sources = re.findall(r'<source src="([^"]+)"[^>]*size="([^"]+)"', html)
        play_from = []
        play_url = []
        for src, size in sources:
            if not src.startswith("http"):
                src = "https:" + src if src.startswith("//") else BASE + src
            play_from.append(f"{size}p")
            play_url.append(f"{size}p${src}")

        # 没 source 就抓直链
        if not play_url:
            urls = re.findall(r'(https?://[^\s"<>]+\.(?:mp4|m3u8)[^\s"<>]*)', html)
            for i, u in enumerate(urls):
                if not u.startswith("http"):
                    u = "https:" + u if u.startswith("//") else BASE + u
                play_from.append(f"线路{i+1}")
                play_url.append(f"线路{i+1}${u}")

        # 实在不行就 iframe
        if not play_url:
            iframe = re.search(r'<iframe[^>]+src="([^"]+)"', html)
            if iframe:
                u = iframe.group(1)
                if not u.startswith("http"):
                    u = "https:" + u if u.startswith("//") else BASE + u
                play_from.append("外链")
                play_url.append(f"外链${u}")

        return {
            "list": [{
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_content": "",
                "vod_play_from": "$$$".join(play_from) if play_from else "Hanime1",
                "vod_play_url": "$$$".join(play_url) if play_url else f"详情页${url}"
            }]
        }

    # 播放
    def playerContent(self, flag, id, vipFlags=None):
        if not id:
            return {"parse": 1, "url": "", "header": {}}
        # 如果是带 $ 的，取最后一段
        if "$" in id:
            id = id.split("$")[-1]
        # 直链直接返回
        if id.startswith("http") and re.search(r'\.(mp4|m3u8|webm|flv)', id, re.I):
            headers = {
                "User-Agent": UA,
                "Referer": BASE + "/",
            }
            return {"parse": 0, "url": id, "header": json.dumps(headers)}
        else:
            # 网页播放
            if not id.startswith("http"):
                id = BASE + id if id.startswith("/") else BASE + "/" + id
            return {"parse": 1, "url": id, "header": json.dumps({"User-Agent": UA})}

    # 搜索
    def searchContent(self, key, quick=False, pg=1):
        try:
            pn = max(int(str(pg)), 1)
            url = f"{BASE}/search?search={quote(key)}&page={pn}"
            html = self._req(url)
            if not html:
                return {"list": [], "page": 1, "pagecount": 1}
            videos = self._parse_cards(html)
            pages = re.findall(r'page=(\d+)', html)
            pc = max(int(x) for x in pages) if pages else pn
            return {
                "list": videos,
                "page": pn,
                "pagecount": pc,
                "limit": len(videos),
                "total": pc * (len(videos) or 20)
            }
        except Exception as e:
            self._log(f"搜索炸了: {e}")
            return {"list": [], "page": 1, "pagecount": 1}

    def localProxy(self, param):
        pass

    def destroy(self):
        if hasattr(self, '_s'):
            self._s.close()