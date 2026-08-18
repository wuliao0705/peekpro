# -*- coding: utf-8 -*-
# 红牛资源 API 版 (hongniuzy2.com) - TVBox 爬虫
# 基于苹果CMS标准采集API，稳定高效

import re
import json
import requests
from urllib.parse import quote
from base.spider import Spider


class Spider(Spider):
    def getName(self):
        return "红牛资源"

    def init(self, extend=""):
        self.host = "https://www.hongniuzy2.com"
        self.api_base = f"{self.host}/api.php/provide/vod/"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": self.host + "/",
        })
        # 分类缓存（首次请求时从API获取）
        self._categories = None

    def _api_request(self, params):
        """通用API请求"""
        try:
            resp = self.session.get(self.api_base, params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception as e:
            print(f"[{self.getName()}] API请求失败: {e}")
            return None

    def _fetch_categories(self):
        """从API获取分类列表"""
        if self._categories is not None:
            return self._categories
        data = self._api_request({})
        if data and data.get("code") == 1 and data.get("class"):
            self._categories = data["class"]
            return self._categories
        # 兜底分类
        self._categories = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "连续剧"},
            {"type_id": "3", "type_name": "综艺"},
            {"type_id": "4", "type_name": "动漫"},
            {"type_id": "5", "type_name": "纪录片"},
            {"type_id": "6", "type_name": "伦理片"},
            {"type_id": "7", "type_name": "体育赛事"},
            {"type_id": "8", "type_name": "短剧"},
        ]
        return self._categories

    # ==================== 首页分类 ====================

    def homeContent(self, filter=False):
        try:
            classes = self._fetch_categories()
            return {"class": [{"type_id": str(c["type_id"]), "type_name": c["type_name"]} for c in classes]}
        except Exception as e:
            print(f"[{self.getName()}] homeContent 异常: {e}")
            return {"class": []}

    # ==================== 首页推荐 ====================

    def homeVideoContent(self):
        try:
            data = self._api_request({"ac": "list", "pg": 1, "pagesize": 30})
            if not data or data.get("code") != 1:
                return {"list": []}
            videos = self._parse_video_list(data.get("list", []))
            return {"list": videos}
        except Exception as e:
            print(f"[{self.getName()}] homeVideoContent 异常: {e}")
            return {"list": []}

    def _parse_video_list(self, items):
        """解析API返回的视频列表"""
        videos = []
        for item in items:
            vod_id = str(item.get("vod_id", ""))
            if not vod_id:
                continue
            # 拼接封面地址（API可能不返回完整地址）
            pic = item.get("vod_pic", "")
            if pic and not pic.startswith("http"):
                pic = self.host + pic
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
            data = self._api_request({
                "ac": "list",
                "t": tid,
                "pg": pg,
                "pagesize": 24,
            })
            if not data or data.get("code") != 1:
                return {"list": [], "page": pg, "pagecount": 1, "limit": 24, "total": 0}

            videos = self._parse_video_list(data.get("list", []))
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

    # ==================== 详情页（核心：从API获取播放地址） ====================

    def detailContent(self, ids):
        try:
            vod_id = ids[0]
            # 如果传入的是URL，提取ID
            if "/vod/detail/" in vod_id:
                m = re.search(r"/id/([^.]+)\.html", vod_id)
                if m:
                    vod_id = m.group(1)
            if not vod_id:
                return {"list": []}

            # 调用API获取详情
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

            # 提取基本信息
            title = vod.get("vod_name", "")
            pic = vod.get("vod_pic", "")
            if pic and not pic.startswith("http"):
                pic = self.host + pic
            desc = vod.get("vod_content", "")

            # 解析播放地址
            # API返回的 vod_play_url 格式: "线路1$url1#线路2$url2"
            # 或者多线路用 $$$ 分隔: "线路1$url1#...$$$线路2$url3#..."
            play_from = []
            play_urls = []

            raw_play_url = vod.get("vod_play_url", "")
            if raw_play_url:
                # 先按 $$$ 拆分多线路
                lines = raw_play_url.split("$$$")
                for line in lines:
                    if not line:
                        continue
                    # 每条线路可能有多个剧集，用 # 分隔
                    eps = line.split("#")
                    # 第一个元素的格式是 "线路名$url"，后面的元素是 "集名$url"
                    if eps:
                        first = eps[0]
                        if "$" in first:
                            parts = first.split("$", 1)
                            source_name = parts[0]
                            # 构建该线路的所有剧集
                            episode_list = []
                            for ep in eps:
                                if "$" in ep:
                                    ep_parts = ep.split("$", 1)
                                    ep_name = ep_parts[0] if ep_parts[0] else f"第{len(episode_list)+1}集"
                                    ep_url = ep_parts[1]
                                    episode_list.append(f"{ep_name}${ep_url}")
                                else:
                                    # 没有 $ 的异常数据
                                    episode_list.append(ep)
                            if episode_list:
                                play_from.append(source_name)
                                play_urls.append("#".join(episode_list))
                        else:
                            # 没有线路名，作为默认线路
                            play_from.append("默认")
                            play_urls.append(line)

            # 如果没有解析到播放地址，尝试从 vod_play_from 字段推断
            if not play_urls:
                play_from = [vod.get("vod_play_from", "默认")]
                # 如果 vod_play_url 是单个地址
                if raw_play_url and raw_play_url.startswith("http"):
                    play_urls = [f"播放${raw_play_url}"]
                else:
                    play_urls = [f"播放${self.host}/vod/play/id/{vod_id}.html"]

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

    # ==================== 播放（从API获取的地址直接使用） ====================

    def playerContent(self, flag, id, vipFlags=None):
        try:
            result = {"parse": 0, "playUrl": "", "url": "", "header": {}}
            if not id or id == "#":
                return result

            # 如果是 m3u8/mp4 直链，直接返回
            if id.startswith("http") and (".m3u8" in id or ".mp4" in id or ".ts" in id):
                result["url"] = id
                result["header"] = {
                    "Referer": self.host + "/",
                    "User-Agent": self.session.headers.get("User-Agent", "Mozilla/5.0"),
                }
                return result

            # 如果 id 是播放页链接，尝试从API获取
            if "/vod/play/" in id:
                m = re.search(r"/id/(\d+)/", id)
                if m:
                    vod_id = m.group(1)
                    # 调用API获取详情，提取播放地址
                    data = self._api_request({
                        "ac": "detail",
                        "ids": vod_id,
                    })
                    if data and data.get("code") == 1:
                        vod = data.get("list", [{}])[0]
                        raw_play_url = vod.get("vod_play_url", "")
                        if raw_play_url:
                            # 尝试提取第一个可用的m3u8地址
                            m3u8_match = re.search(r"(https?://[^\s$#]+\.m3u8[^\s$#]*)", raw_play_url)
                            if m3u8_match:
                                result["url"] = m3u8_match.group(1)
                                result["header"] = {
                                    "Referer": self.host + "/",
                                    "User-Agent": self.session.headers.get("User-Agent", "Mozilla/5.0"),
                                }
                                return result

            # 如果是相对路径，补全
            if id.startswith("/"):
                id = self.host + id
                result["url"] = id
                result["header"] = {
                    "Referer": self.host + "/",
                    "User-Agent": self.session.headers.get("User-Agent", "Mozilla/5.0"),
                }
                return result

            # 兜底
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
            data = self._api_request({
                "ac": "list",
                "wd": key,
                "pg": pg,
                "pagesize": 24,
            })
            if not data or data.get("code") != 1:
                return {"list": [], "page": pg, "pagecount": 1, "limit": 24, "total": 0}

            videos = self._parse_video_list(data.get("list", []))
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