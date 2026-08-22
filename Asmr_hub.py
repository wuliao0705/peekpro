# -*- coding: utf-8 -*-
# ASMR Hub - TVBox 爬虫
# 目标: https://asmrhub.site/

import sys
import re
import json
import urllib.parse
from base.spider import Spider
import requests


class Spider(Spider):
    def getName(self):
        return "ASMR Hub"

    def init(self, extend=""):
        self.host = "https://asmrhub.site"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.host + "/",
            "Accept": "application/json, text/plain, */*",
        })

        # 分类列表（从导航菜单提取）
        self.categories = [
            {"type_id": "白噪声", "type_name": "白噪声"},
            {"type_id": "nsfw", "type_name": "nsfw"},
        ]
        # 默认每页数量
        self.page_size = 20

    def _fix_url(self, url):
        """补全相对路径"""
        if not url:
            return ""
        url = url.strip()
        if url.startswith("http"):
            return url
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.host + url
        return self.host + "/" + url

    def _fetch_api(self, page, category=""):
        """请求 API 获取列表"""
        url = f"{self.host}/api.php?type=index&size={self.page_size}&p={page}"
        if category:
            url += f"&category={category}"
        try:
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"[ASMR Hub] API请求失败: {e}")
        return None

    def homeContent(self, filter=False):
        """返回分类列表"""
        classes = []
        for cat in self.categories:
            classes.append({"type_id": cat["type_id"], "type_name": cat["type_name"]})
        return {"class": classes}

    def homeVideoContent(self):
        """首页推荐（默认加载第一页）"""
        return self.categoryContent("", "1")

    def categoryContent(self, tid, pg, filter=False, extend=None):
        """分类列表（支持分页）"""
        pg = int(pg) if pg else 1
        extend = extend or {}
        # 如果 tid 为空，则默认加载全部（无分类筛选）
        category = tid if tid else ""
        data = self._fetch_api(pg, category)
        if not data or "list" not in data:
            return {"list": [], "page": pg, "pagecount": 1, "limit": self.page_size, "total": 0}

        videos = []
        for item in data.get("list", []):
            # 音频文件 URL（可能为相对路径）
            audio_url = self._fix_url(item.get("path", ""))
            # 封面图
            poster = item.get("poster", "")
            if poster and not poster.startswith("http"):
                poster = self._fix_url(poster)
            # 时长（秒）转换为字符串
            duration = item.get("time", 0)
            if duration:
                duration_str = f"{duration//60:02d}:{duration%60:02d}"
            else:
                duration_str = ""

            videos.append({
                "vod_id": audio_url,          # 直接使用音频 URL 作为 ID
                "vod_name": item.get("title", "未知标题"),
                "vod_pic": poster,
                "vod_remarks": duration_str,
            })

        # 计算总页数（API 未返回总条数，根据当前列表长度估算）
        total = len(videos)
        pagecount = pg
        if total >= self.page_size:
            pagecount = pg + 1  # 假设还有下一页

        return {
            "list": videos,
            "page": pg,
            "pagecount": pagecount,
            "limit": self.page_size,
            "total": pagecount * self.page_size,
        }

    def detailContent(self, ids):
        """详情页（直接返回播放地址）"""
        if not ids:
            return {"list": []}
        audio_url = ids[0]  # vod_id 就是音频 URL
        if not audio_url.startswith("http"):
            audio_url = self._fix_url(audio_url)

        # 构造一个简单的 vod 对象，播放地址直接放在 vod_play_url 中
        return {
            "list": [{
                "vod_id": audio_url,
                "vod_name": "ASMR音频",
                "vod_pic": "",
                "vod_play_from": "直链",
                "vod_play_url": f"播放${audio_url}",
            }]
        }

    def playerContent(self, flag, id, vipFlags=None):
        """播放器（直接返回音频链接）"""
        # id 可能是完整的音频 URL
        if id.startswith("http"):
            return {"parse": 0, "url": id, "header": {"Referer": self.host + "/"}}
        # 如果不是完整 URL，尝试补全
        full_url = self._fix_url(id)
        return {"parse": 0, "url": full_url, "header": {"Referer": self.host + "/"}}

    def searchContent(self, key, quick=False, pg="1"):
        """搜索（网站暂无搜索接口，返回空）"""
        return {"list": [], "page": 1, "pagecount": 1, "limit": 20, "total": 0}

    def isVideoFormat(self, url):
        """判断是否为支持的音频格式"""
        return url and (".mp3" in url.lower() or ".m4a" in url.lower())

    def manualVideoCheck(self):
        return False

    def destroy(self):
        if self.session:
            self.session.close()

    def localProxy(self, param):
        return None