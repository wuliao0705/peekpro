# -*- coding: utf-8 -*-
import re
import json
import requests
from base.spider import Spider


class Spider(Spider):
    def __init__(self):
        super().__init__()
        self.host = "https://baipiaozhe.com"
        self.name = "搜剧AI"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": self.host + "/",
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.verify = False

    def init(self, extend=""):
        pass

    def isVideoFormat(self, url):
        return url and (".m3u8" in url or ".mp4" in url or ".ts" in url)

    def manualVideoCheck(self):
        return False

    def _try_api(self, path):
        """尝试调用 API，返回 JSON 数据或 None"""
        url = self.host + path
        try:
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data and isinstance(data, dict):
                    return data
            return None
        except Exception as e:
            print(f"[{self.name}] API 请求失败: {e}")
            return None

    def _extract_videos_from_api(self, data):
        """从 API 响应中提取视频列表"""
        videos = []
        # 尝试多种可能的字段路径
        candidates = []
        if isinstance(data, dict):
            # 常见字段: list, data, results, items, movies, vod_list
            for key in ["list", "data", "results", "items", "movies", "vod_list", "videos"]:
                if key in data:
                    candidates.append(data[key])
            # 如果有 code=200 且 data 是列表
            if data.get("code") == 200 and isinstance(data.get("data"), list):
                candidates.append(data["data"])
        elif isinstance(data, list):
            candidates.append(data)

        for items in candidates:
            if isinstance(items, list) and len(items) > 0:
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    # 提取视频信息
                    vid = item.get("id") or item.get("vod_id") or item.get("video_id") or ""
                    name = item.get("title") or item.get("name") or item.get("vod_name") or "未知"
                    pic = item.get("cover") or item.get("pic") or item.get("vod_pic") or ""
                    url = item.get("url") or item.get("play_url") or item.get("vod_play_url") or ""
                    # 如果 url 是 m3u8 或 mp4，直接使用
                    if url and (".m3u8" in url or ".mp4" in url):
                        videos.append({
                            "vod_id": str(vid),
                            "vod_name": name,
                            "vod_pic": pic,
                            "vod_remarks": "",
                            "vod_play_from": "直链",
                            "vod_play_url": f"正片${url}"
                        })
                    # 如果只有 id，可能需要在详情页获取播放地址
                    elif vid:
                        videos.append({
                            "vod_id": str(vid),
                            "vod_name": name,
                            "vod_pic": pic,
                            "vod_remarks": "需详情页",
                            "vod_play_from": "直链",
                            "vod_play_url": f"正片${vid}"  # 占位
                        })
                return videos
        return videos

    def homeContent(self, filter):
        # 尝试从首页 API 获取分类
        data = self._try_api("/api/config") or self._try_api("/api/categories")
        if data and isinstance(data, dict):
            categories = data.get("categories") or data.get("class") or data.get("data")
            if isinstance(categories, list) and len(categories) > 0:
                class_list = []
                for c in categories:
                    if isinstance(c, dict):
                        class_list.append({
                            "type_id": str(c.get("id") or c.get("type_id") or ""),
                            "type_name": c.get("name") or c.get("type_name") or "未知"
                        })
                if class_list:
                    return {"class": class_list}
        # 保底分类
        return {"class": [
            {"type_id": "recommend", "type_name": "推荐"},
            {"type_id": "movie", "type_name": "电影"},
            {"type_id": "tv", "type_name": "电视剧"},
            {"type_id": "anime", "type_name": "动漫"},
        ]}

    def homeVideoContent(self):
        return self.categoryContent("recommend", "1", False, {})

    def categoryContent(self, tid, pg, filter, extend):
        try:
            pg = int(pg) if str(pg).isdigit() else 1
            result = {"list": [], "page": pg, "pagecount": 1, "limit": 20, "total": 0}

            # 尝试获取列表数据
            data = None
            if tid in ["recommend", "movie", "tv", "anime"]:
                data = self._try_api(f"/api/vod/list?type={tid}&page={pg}&limit=20")
            if not data:
                data = self._try_api(f"/api/list?type={tid}&page={pg}&limit=20")
            if not data:
                data = self._try_api(f"/api/search?type={tid}&page={pg}&limit=20")
            if not data:
                data = self._try_api(f"/api/movies?type={tid}&page={pg}&limit=20")
            if not data:
                # 如果 API 都失败，尝试从首页 HTML 提取（但 SPA 可能没有）
                print(f"[{self.name}] 所有 API 尝试失败，返回空列表")
                return result

            videos = self._extract_videos_from_api(data)
            result["list"] = videos
            if videos:
                result["pagecount"] = pg + 1  # 假设有下一页
            return result
        except Exception as e:
            print(f"[{self.name}] categoryContent error: {e}")
            return {"list": [], "page": pg, "pagecount": 1, "limit": 20, "total": 0}

    def detailContent(self, ids):
        try:
            vid = ids[0] if ids else ""
            if not vid:
                return {"list": []}
            # 如果 vid 是数字或字符串 ID，尝试获取详情
            data = self._try_api(f"/api/vod/detail?id={vid}")
            if not data:
                data = self._try_api(f"/api/detail?id={vid}")
            if not data:
                return {"list": []}
            # 提取详情
            if isinstance(data, dict):
                info = data.get("data") or data
                name = info.get("title") or info.get("name") or "未知"
                pic = info.get("cover") or info.get("pic") or ""
                play_url = info.get("url") or info.get("play_url") or info.get("vod_play_url") or ""
                if play_url and (".m3u8" in play_url or ".mp4" in play_url):
                    return {
                        "list": [{
                            "vod_id": vid,
                            "vod_name": name,
                            "vod_pic": pic,
                            "vod_play_from": "直链",
                            "vod_play_url": f"正片${play_url}"
                        }]
                    }
            return {"list": []}
        except Exception as e:
            print(f"[{self.name}] detailContent error: {e}")
            return {"list": []}

    def playerContent(self, flag, id, vipFlags=None):
        try:
            result = {"parse": 0, "playUrl": "", "url": "", "header": {}}
            if self.isVideoFormat(id):
                result["url"] = id
                result["header"] = {"Referer": self.host + "/"}
                return result
            # 如果 id 看起来像视频 ID，尝试获取播放地址
            if id and not id.startswith("http"):
                data = self._try_api(f"/api/vod/play?id={id}")
                if data:
                    url = data.get("url") or data.get("play_url") or ""
                    if url and self.isVideoFormat(url):
                        result["url"] = url
                        result["header"] = {"Referer": self.host + "/"}
                        return result
            result["url"] = id
            return result
        except Exception as e:
            print(f"[{self.name}] playerContent error: {e}")
            return {"parse": 0, "playUrl": "", "url": id, "header": {}}

    def searchContent(self, key, quick, pg="1"):
        try:
            pg = int(pg) if str(pg).isdigit() else 1
            result = {"list": [], "page": pg, "pagecount": 1, "limit": 20, "total": 0}
            data = self._try_api(f"/api/search?keyword={key}&page={pg}&limit=20")
            if not data:
                return result
            videos = self._extract_videos_from_api(data)
            result["list"] = videos
            return result
        except Exception as e:
            print(f"[{self.name}] searchContent error: {e}")
            return {"list": [], "page": pg, "pagecount": 1, "limit": 20, "total": 0}