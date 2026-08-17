# -*- coding: utf-8 -*-
"""白嫖者/搜剧AI Spider，适配 WebHomeTV、OK影视、PeekPro。"""
import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from urllib.parse import urlencode, quote

try:
    import requests
except Exception:
    requests = None


class Spider:
    HOST = "https://baipiaozhe.com"
    SIGN_KEY = "f39d73aa7a6426203cdee1ef17b31d3b7ea8c23f4c59c62a3a8aa0f39ee5e79d"
    CLIENT = {
        "x-ai-movie-client-name": "movie-search-frontend",
        "x-ai-movie-client-version": "1.0.0",
        "x-ai-movie-build-version": "aimovie-v2026.08.17.4",
        "x-ai-movie-protocol-version": "2026-07-05.library-v2.playback-v1",
    }
    UA = "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36"

    def __init__(self):
        self.s = None
        self.session = None
        self.sess = None
        self.anonymous_id = "web_" + str(uuid.uuid4())
        self._anon_ready = False
        self._detail_cache = {}
        self._episode_cache = {}
        self._ticket_cache = {}

    def getDependence(self):
        return []

    def init(self, extend=""):
        self._parse_extend(extend)
        if requests:
            self.s = requests.Session()
            self.s.headers.update({"User-Agent": self.UA, "Referer": self.HOST + "/"})
            self.session = self.s
            self.sess = self.s
        return None

    def _parse_extend(self, extend):
        if isinstance(extend, str) and extend.strip():
            try:
                obj = json.loads(extend)
                if isinstance(obj, dict):
                    self.HOST = obj.get("host", self.HOST).rstrip("/")
            except Exception:
                if extend.startswith("http"):
                    self.HOST = extend.rstrip("/")

    def _sign_headers(self, method, path):
        ts = str(int(time.time() * 1000))
        nonce = os.urandom(16).hex()
        raw = "%s\n%s\n%s\n%s" % (method.upper(), path, ts, nonce)
        sig = hmac.new(self.SIGN_KEY.encode(), raw.encode(), hashlib.sha256).hexdigest()
        h = dict(self.CLIENT)
        h.update({"x-ai-movie-timestamp": ts, "x-ai-movie-nonce": nonce,
                  "x-ai-movie-signature": sig, "Accept": "application/json"})
        return h

    def _request(self, path, method="GET", body=None):
        if not path.startswith("/"):
            path = "/" + path
        headers = self._sign_headers(method, path)
        if body is not None:
            headers["Content-Type"] = "application/json"
        url = self.HOST + path
        if requests and self.s:
            r = self.s.request(method, url, headers=headers, json=body, timeout=15)
            if r.status_code >= 400:
                raise RuntimeError("HTTP %s" % r.status_code)
            return r.json()
        import urllib.request
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))

    def _ensure_anonymous(self):
        if self._anon_ready:
            return
        try:
            self._request("/v1/users/anonymous", "POST", {"anonymous_id": self.anonymous_id})
        except Exception:
            pass
        self._anon_ready = True

    def homeContent(self, filter=None):
        self._ensure_anonymous()
        try:
            data = self._request("/v1/feed/home?scope=public&mode=preview&sections=3&cards=10")
            cards = []
            for sec in data.get("sections", []):
                cards.extend(sec.get("cards", []))
            return {"class": self._classes(), "list": self._cards(cards)}
        except Exception:
            return {"class": self._classes(), "list": []}

    def homeVideoContent(self):
        return self.homeContent(None)

    def _classes(self):
        return [
            {"type_id": "movie", "type_name": "电影"},
            {"type_id": "series", "type_name": "电视剧"},
            {"type_id": "anime", "type_name": "动漫"},
            {"type_id": "variety", "type_name": "综艺"},
            {"type_id": "documentary", "type_name": "纪录片"},
        ]

    def _cards(self, cards):
        out = []
        seen = set()
        for x in cards or []:
            x = x if isinstance(x, dict) else {}
            vid = x.get("variant_id") or x.get("id")
            if not vid or vid in seen:
                continue
            seen.add(vid)
            out.append({"vod_id": vid, "vod_name": x.get("title", ""),
                        "vod_pic": x.get("poster_url", ""),
                        "vod_remarks": x.get("remarks", "") or x.get("subtitle", "")})
        return out

    def categoryContent(self, tid, pg=1, filter=None, extend=None):
        self._ensure_anonymous()
        page = int(str(pg or 1))
        params = {"kind": str(tid), "page": page, "limit": 20}
        if isinstance(extend, dict):
            params.update({k: v for k, v in extend.items() if v not in (None, "")})
        path = "/v1/browse/catalog?" + urlencode(params)
        try:
            data = self._request(path)
            p = data.get("pagination", {})
            return {"page": p.get("page", page), "pagecount": 9999,
                    "limit": p.get("limit", 20), "total": p.get("total", 0),
                    "list": self._cards(data.get("cards", []))}
        except Exception:
            return {"page": page, "pagecount": 0, "limit": 20, "total": 0, "list": []}

    def detailContent(self, ids):
        vid = self._one_id(ids)
        self._ensure_anonymous()
        try:
            d = self._detail(vid)
            eps = self._episodes(vid)
            # 站点每个剧集都返回多条线路；用第1集发现线路，再为所有集生成线路分组。
            first_token = (eps[0].get("token") or eps[0].get("id")) if eps else ""
            options = self._resolve_options(first_token) if first_token else []
            play_from, play_groups = [], []
            for opt in options:
                source_id = opt.get("playback_source_id") or opt.get("id") or opt.get("provider_id")
                label = self._line_label(opt)
                if not source_id:
                    continue
                group = []
                for idx, e in enumerate(eps):
                    token = e.get("token") or e.get("id")
                    if token:
                        title = e.get("title") or ("第%s集" % e.get("number", idx + 1))
                        # 稳定播放ID：剧集token@@线路source_id
                        group.append(title + "$" + token + "@@" + source_id)
                if group:
                    play_from.append(str(label))
                    play_groups.append("#".join(group))
            if not play_groups:
                group = []
                for idx, e in enumerate(eps):
                    token = e.get("token") or e.get("id")
                    if token:
                        group.append((e.get("title") or ("第%s集" % (idx + 1))) + "$" + token)
                play_from, play_groups = ["白嫖者"], ["#".join(group)]
            info = "/".join(d.get("genres", [])[:8])
            vod = {"vod_id": vid, "vod_name": d.get("title", ""),
                   "vod_pic": d.get("poster_url", ""), "vod_year": str(d.get("year", "")),
                   "vod_area": d.get("area", ""), "vod_actor": ",".join(d.get("actors", [])),
                   "vod_director": ",".join(d.get("directors", [])), "vod_remarks": d.get("remarks", ""),
                   "vod_content": d.get("description", ""), "vod_class": info,
                   "vod_play_from": "$$$".join(play_from), "vod_play_url": "$$$".join(play_groups)}
            return {"list": [vod]}
        except Exception:
            return {"list": []}

    def _detail(self, vid):
        if vid not in self._detail_cache:
            self._detail_cache[vid] = self._request("/v1/catalog/%s/detail" % quote(vid, safe=""))
        return self._detail_cache[vid]

    def _episodes(self, vid):
        if vid not in self._episode_cache:
            d = self._request("/v1/catalog/%s/episodes?limit=100&offset=0" % quote(vid, safe=""))
            self._episode_cache[vid] = d.get("episodes", [])
        return self._episode_cache[vid]

    def _line_label(self, opt):
        label = str(opt.get("display_label") or opt.get("label") or opt.get("provider_name") or opt.get("provider_id") or "线路")
        low = label.lower()
        # 站点接口不单独返回分辨率字段，官方线路的标签本身带质量信息。
        if "4k" in low or "2160" in low or "uhd" in low:
            quality = "4K"
        elif "1080" in low or "fhd" in low:
            quality = "1080P"
        elif "720" in low:
            quality = "720P"
        elif "hd" in low or "高清" in label:
            quality = "高清"
        elif "540" in low:
            quality = "540P"
        elif "360" in low:
            quality = "360P"
        elif label in ("爱奇艺", "红牛资源", "无水印资源", "极速资源", "魔都资源", "新浪资源", "豪华资源", "豆瓣资源", "西瓜资源", "暴风资源", "U酷资源", "如意资源", "iqiyi资源", "ikun资源", "金鹰资源", "索尼资源", "茅台资源", "速播资源", "电影天堂资源", "猫眼资源", "无尽资源", "最大资源", "牛牛资源", "非凡资源", "量子资源", "360资源"):
            quality = "未知"
        else:
            quality = "未知"
        return label if (quality == "未知" or quality.lower() in low) else "%s-%s" % (quality, label)

    def _resolve_options(self, token):
        try:
            data = self._request("/v1/playback/resolve/%s" % quote(token, safe=""))
            return data.get("line_options", [])
        except Exception:
            return []

    def searchContent(self, key, quick=False, pg="1"):
        # 站点的搜索结果由 AI 会话生成；使用公开片库 q 参数兼容普通影视壳搜索。
        self._ensure_anonymous()
        page = int(str(pg or 1))
        try:
            data = self._request("/v1/browse/catalog?" + urlencode({"q": key, "page": page, "limit": 20}))
            return {"page": page, "pagecount": 9999, "list": self._cards(data.get("cards", []))}
        except Exception:
            return {"page": page, "pagecount": 0, "list": []}

    def playerContent(self, flag, ids, vipFlags=None):
        self._ensure_anonymous()
        raw = self._one_id(ids)
        parts = raw.split("@@", 1)
        token = parts[0]
        source_id = parts[1] if len(parts) > 1 else ""
        try:
            resolved = self._request("/v1/playback/resolve/%s" % quote(token, safe=""))
            opts = resolved.get("line_options", [])
            selected = next((x for x in opts if source_id and (x.get("playback_source_id") == source_id or x.get("id") == source_id)), None)
            if not selected:
                selected = next((x for x in opts if x.get("selected")), None)
            if not selected and opts:
                selected = opts[0]
            if not selected:
                return {"parse": 0, "url": "", "header": {}}
            ticket = selected.get("url", "")
            if ticket.startswith("resolve://"):
                line = self._request("/v1/playback/resolve-line", "POST", {"ticket": ticket})
                selected = line.get("line", selected)
            url = selected.get("url", "")
            return {"parse": 0, "url": url, "header": {"User-Agent": self.UA, "Referer": self.HOST + "/"},
                    "format": "application/x-mpegURL" if ".m3u8" in url else ""}
        except Exception:
            return {"parse": 0, "url": "", "header": {}}

    def localProxy(self, param):
        return [404, "text/plain", b"", {}]

    def action(self, action):
        return {}

    def manualVideoCheck(self):
        return False

    def isVideoFormat(self, url):
        return ".m3u8" in str(url).lower() or ".mp4" in str(url).lower()

    def destroy(self):
        return None

    def _one_id(self, ids):
        if isinstance(ids, str):
            try:
                ids = json.loads(ids)
            except Exception:
                return ids
        if isinstance(ids, (list, tuple)):
            return str(ids[0]) if ids else ""
        if isinstance(ids, dict):
            return str(ids.get("id") or ids.get("vod_id") or "")
        return str(ids or "")
