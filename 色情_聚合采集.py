# -*- coding: utf-8 -*-
# 聚合资源采集站 - TVBox 爬虫（精简版）
# 仅保留6个可用站点：桃花、鲨鱼、滴滴、乐播、番号、91麻豆

import re
import json
import requests
from urllib.parse import quote, urljoin
from base.spider import Spider


# ============ 站点列表（仅保留可用站点） ============
SITES = [
    ["桃花资源", "http://thzy1.me"],
    ["鲨鱼视频", "https://shayuapi.com"],
    ["滴滴资源", "https://didizy.com"],
    ["乐播资源", "https://lbapi9.com"],
    ["番号资源", "http://fhapi9.com"],
    ["91麻豆网", "https://91md.me"],
]


class Spider(Spider):
    def getName(self):
        return "聚合资源采集"

    def init(self, extend=""):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": "",
        })
        # 默认使用第一个站点（桃花资源）
        self.current_index = 0
        self._load_site(0)

    def _load_site(self, index):
        """加载指定索引的站点"""
        if index < 0 or index >= len(SITES):
            index = 0
        self.current_index = index
        self.site_name, self.site_url = SITES[index]
        self.api_base = self.site_url.rstrip("/") + "/api.php/provide/vod/"
        self.session.headers.update({"Referer": self.site_url + "/"})
        self._categories = None
        print(f"[{self.getName()}] 切换到: {self.site_name} ({self.site_url})")

    def _api_request(self, params, timeout=15):
        """请求API接口"""
        try:
            resp = self.session.get(self.api_base, params=params, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception as e:
            print(f"[{self.getName()}] API请求失败: {e}")
            return None

    def _fetch_categories(self):
        """获取分类列表"""
        if self._categories is not None:
            return self._categories
        data = self._api_request({})
        if data and data.get("code") == 1 and data.get("class"):
            self._categories = data["class"]
            return self._categories
        # 兜底分类
        self._categories = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "电视剧"},
            {"type_id": "3", "type_name": "综艺"},
            {"type_id": "4", "type_name": "动漫"},
            {"type_id": "5", "type_name": "伦理"},
            {"type_id": "6", "type_name": "短剧"},
        ]
        return self._categories

    # ==================== 首页分类 ====================

    def homeContent(self, filter=False):
        try:
            classes = self._fetch_categories()
            class_list = [{"type_id": "__switch__", "type_name": "🔄切换站点"}]
            for c in classes:
                class_list.append({"type_id": str(c["type_id"]), "type_name": c["type_name"]})
            return {"class": class_list}
        except Exception as e:
            print(f"[{self.getName()}] homeContent 异常: {e}")
            return {"class": []}

    # ==================== 首页推荐 ====================

    def homeVideoContent(self):
        try:
            data = self._api_request({"ac": "list", "pg": 1, "pagesize": 30})
            if not data or data.get("code") != 1:
                return {"list": []}
            items = self._parse_list(data.get("list", []))
            return {"list": items}
        except Exception as e:
            print(f"[{self.getName()}] homeVideoContent 异常: {e}")
            return {"list": []}

    def _parse_list(self, items):
        """解析视频列表"""
        videos = []
        for item in items:
            vod_id = str(item.get("vod_id", ""))
            if not vod_id:
                continue
            pic = item.get("vod_pic", "")
            if pic and not pic.startswith("http"):
                pic = self.site_url + pic
            videos.append({
                "vod_id": vod_id,
                "vod_name": item.get("vod_name", ""),
                "vod_pic": pic,
                "vod_remarks": item.get("vod_remarks", ""),
            })
        return videos

    # ==================== 分类列表 ====================

    def categoryContent(self, tid, pg, filter=False, extend=None):
        try:
            pg = int(pg) if str(pg).isdigit() else 1

            if tid == "__switch__":
                items = []
                for i, (name, url) in enumerate(SITES):
                    items.append({
                        "vod_id": f"__site_{i}",
                        "vod_name": f"[{i}] {name}",
                        "vod_pic": "",
                        "vod_remarks": url,
                    })
                return {
                    "list": items,
                    "page": 1,
                    "pagecount": 1,
                    "limit": 50,
                    "total": len(items),
                }

            data = self._api_request({
                "ac": "list",
                "t": tid,
                "pg": pg,
                "pagesize": 24,
            })
            if not data or data.get("code") != 1:
                return {"list": [], "page": pg, "pagecount": 1, "limit": 24, "total": 0}

            videos = self._parse_list(data.get("list", []))
            pagecount = int(data.get("pagecount", 1))
            total = int(data.get("total", 0))

            return {
                "list": videos,
                "page": pg,
                "pagecount": pagecount if pagecount > 1 else pg + 1,
                "limit": int(data.get("limit", 24)),
                "total": total,
            }
        except Exception as e:
            print(f"[{self.getName()}] categoryContent 异常: {e}")
            return {"list": [], "page": pg, "pagecount": 1, "limit": 24, "total": 0}

    # ==================== 详情页 ====================

    def detailContent(self, ids):
        try:
            vod_id = ids[0]
            if isinstance(vod_id, str) and vod_id.startswith("__site_"):
                idx = int(vod_id.split("_")[-1])
                if 0 <= idx < len(SITES):
                    self._load_site(idx)
                    self._categories = None
                    return {
                        "list": [{
                            "vod_id": "__switch_done",
                            "vod_name": f"✅ 已切换到: {SITES[idx][0]}",
                            "vod_pic": "",
                            "vod_content": f"当前站点: {SITES[idx][0]}\n接口地址: {SITES[idx][1]}\n请返回首页刷新分类",
                            "vod_play_from": "切换完成",
                            "vod_play_url": "播放$#",
                        }]
                    }

            data = self._api_request({
                "ac": "detail",
                "ids": vod_id,
            })
            if not data or data.get("code") != 1:
                return {"list": []}

            vod_list = data.get("list", [])
            if not vod_list:
                return {"list": []}
            vod = vod_list[0]

            title = vod.get("vod_name", "")
            pic = vod.get("vod_pic", "")
            if pic and not pic.startswith("http"):
                pic = self.site_url + pic
            desc = vod.get("vod_content", "")

            raw_play_url = vod.get("vod_play_url", "")
            play_from = []
            play_urls = []

            if raw_play_url:
                lines = raw_play_url.split("$$$")
                for line in lines:
                    if not line:
                        continue
                    eps = line.split("#")
                    if eps:
                        first = eps[0]
                        if "$" in first:
                            parts = first.split("$", 1)
                            source_name = parts[0]
                            episode_list = []
                            for ep in eps:
                                if "$" in ep:
                                    ep_parts = ep.split("$", 1)
                                    ep_name = ep_parts[0] if ep_parts[0] else f"第{len(episode_list)+1}集"
                                    ep_url = ep_parts[1]
                                    if not ep_url.startswith("http"):
                                        ep_url = self.site_url + ep_url
                                    episode_list.append(f"{ep_name}${ep_url}")
                                else:
                                    episode_list.append(ep)
                            if episode_list:
                                play_from.append(source_name)
                                play_urls.append("#".join(episode_list))
                        else:
                            play_from.append("默认")
                            play_urls.append(line)

            if not play_urls:
                play_from = [vod.get("vod_play_from", "默认")]
                if raw_play_url and raw_play_url.startswith("http"):
                    play_urls = [f"播放${raw_play_url}"]
                else:
                    play_urls = [f"播放${self.site_url}/vod/play/id/{vod_id}.html"]

            return {
                "list": [{
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_content": desc,
                    "vod_play_from": "$$$".join(play_from),
                    "vod_play_url": "$$$".join(play_urls),
                }]
            }
        except Exception as e:
            print(f"[{self.getName()}] detailContent 异常: {e}")
            return {"list": []}

    # ==================== 播放 ====================

    def playerContent(self, flag, id, vipFlags=None):
        try:
            result = {"parse": 0, "playUrl": "", "url": "", "header": {}}
            if not id or id == "#":
                return result

            if id.startswith("http") and (".m3u8" in id or ".mp4" in id or ".ts" in id):
                result["url"] = id
                result["header"] = {
                    "Referer": self.site_url + "/",
                    "User-Agent": self.session.headers.get("User-Agent", "Mozilla/5.0"),
                }
                return result

            if "/vod/play/" in id:
                if not id.startswith("http"):
                    id = self.site_url + id
                try:
                    resp = self.session.get(id, timeout=15)
                    if resp.status_code == 200:
                        html = resp.text
                        m = re.search(r'player_aaaa\s*=\s*(\{[^}]*?\})', html, re.DOTALL)
                        if m:
                            try:
                                data = json.loads(m.group(1))
                                play_url = data.get("url", "")
                                if play_url:
                                    if not play_url.startswith("http"):
                                        play_url = self.site_url + play_url
                                    result["url"] = play_url
                                    result["header"] = {
                                        "Referer": self.site_url + "/",
                                        "User-Agent": self.session.headers.get("User-Agent", "Mozilla/5.0"),
                                    }
                                    return result
                            except:
                                pass
                        m = re.search(r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)', html)
                        if m:
                            result["url"] = m.group(1)
                            result["header"] = {
                                "Referer": self.site_url + "/",
                                "User-Agent": self.session.headers.get("User-Agent", "Mozilla/5.0"),
                            }
                            return result
                except Exception as e:
                    print(f"[{self.getName()}] 播放页请求失败: {e}")

            if id.startswith("/"):
                id = self.site_url + id
                result["url"] = id
                result["header"] = {
                    "Referer": self.site_url + "/",
                    "User-Agent": self.session.headers.get("User-Agent", "Mozilla/5.0"),
                }
                return result

            result["url"] = id
            result["header"] = {
                "Referer": self.site_url + "/",
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
            data = self._api_request({
                "ac": "list",
                "wd": key,
                "pg": pg,
                "pagesize": 24,
            })
            if not data or data.get("code") != 1:
                return {"list": [], "page": pg, "pagecount": 1, "limit": 24, "total": 0}

            videos = self._parse_list(data.get("list", []))
            pagecount = int(data.get("pagecount", 1))
            total = int(data.get("total", 0))

            return {
                "list": videos,
                "page": pg,
                "pagecount": pagecount if pagecount > 1 else pg + 1,
                "limit": int(data.get("limit", 24)),
                "total": total,
            }
        except Exception as e:
            print(f"[{self.getName()}] searchContent 异常: {e}")
            return {"list": [], "page": pg, "pagecount": 1, "limit": 24, "total": 0}

    def isVideoFormat(self, url):
        return url and (".m3u8" in url or ".mp4" in url or ".ts" in url)

    def manualVideoCheck(self):
        return False

    def destroy(self):
        if self.session:
            self.session.close()