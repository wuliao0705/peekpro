# -*- coding: utf-8 -*-
# 在线内容聚合.py - 精简版（仅在线功能 + 6个新增直播源）
# 包含：电视直播/网络电台/短视频/画廊/游戏大厅/网页浏览器

import sys
import re
import json
import os
import base64
import hashlib
import time
import urllib.parse
import random
from concurrent.futures import ThreadPoolExecutor
from base.spider import Spider
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import quote, unquote, urljoin, urlparse

# ==================== 电视直播封面 ====================
TV_COVER = "http://pic.rmb.bdstatic.com/bjh/240603/8e7bf2d9440058101b0fc89167eba9b44449.jpeg"

# ==================== 缓存路径 ====================
RADIO_COVER_CACHE_DIR = '/storage/emulated/0/tmp/radio_covers/'
RADIO_SCAN_RECORD_FILE = '/storage/emulated/0/tmp/radio_scan_record.json'
LIVE_PROGRAM_CACHE_DURATION = 300

# ==================== 在线直播源（原有7个 + 新增6个） ====================
ONLINE_LIVE_SOURCES = [
    # 原有7个（删除了咪咕/宫殿/游魂/日后/裤佬）
    {
        "id": "simple_live",
        "name": "💚简单直播",
        "url": "http://gh-proxy.org/raw.githubusercontent.com/Supprise0901/TVBox_live/main/live.txt",
        "cover": TV_COVER,
        "remarks": "💚简单直播",
        "type": "txt",
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    },
    {
        "id": "Kimentanm",
        "name": "💙Kimentanm",
        "url": "https://gh.llkk.cc/https://raw.githubusercontent.com/Kimentanm/aptv/master/m3u/iptv.m3u",
        "cover": TV_COVER,
        "remarks": "💙Kimentanm",
        "type": "m3u",
        "ua": "AptvPlayer-UA"
    },
    {
        "id": "易发TV",
        "name": "💛易发TV直播",
        "url": "https://gh-proxy.org/https://raw.githubusercontent.com/fafa002/yf2025/refs/heads/main/yiyifafa.txt",
        "cover": TV_COVER,
        "remarks": "易发直播",
        "type": "txt",
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    },
    {
        "id": "天下TV",
        "name": "🗺天下TV",
        "url": "https://ilook.epg.one/5CM5SY98BF24PL/2",
        "cover": TV_COVER,
        "remarks": "🗺天下直播",
        "type": "m3u",
        "ua": "User-Agent : com.android.chrome/5.1.6 (Linux;Android 15) AndroidXMedia3/1.10.0"
    },
    {
        "id": "香雨直播",
        "name": "☔香雨TV直播",
        "url": "https://wget.la/https://raw.githubusercontent.com/ajqubbs/zhiboyuan/main/%E9%A6%99%E9%9B%A8%E7%9B%B4%E6%92%AD.txt",
        "cover": TV_COVER,
        "remarks": "☔香雨直播",
        "type": "txt",
        "ua": "User-Agent : com.android.chrome/5.1.6 (Linux;Android 15) AndroidXMedia3/1.10.0"
    },
    {
        "id": "三线直播",
        "name": "❤️三线TV",
        "url": "https://raw.githubusercontent.com/mzky/checklist/refs/heads/master/itvlist.m3u",
        "cover": TV_COVER,
        "remarks": "❤️三线直播",
        "type": "m3u",
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    },
    {
        "id": "suxuang",
        "name": "💚suxuang",
        "url": "https://gh-proxy.org/https://raw.githubusercontent.com/suxuang/myIPTV/main/ipv4.m3u",
        "cover": TV_COVER,
        "remarks": "suxuang",
        "type": "m3u",
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    },
    # ===== 新增6个：抖音/快手/B站/虎牙/斗鱼/YY =====
    {
        "id": "douyin_live",
        "name": "📱 抖音直播",
        "url": "https://gh-proxy.org/https://raw.githubusercontent.com/pan8664716/MultiLive/main/output/douyin_live.m3u",
        "cover": TV_COVER,
        "remarks": "📱 抖音直播",
        "type": "m3u",
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    },
    {
        "id": "kuaishou_live",
        "name": "📱 快手直播",
        "url": "https://gh-proxy.org/https://raw.githubusercontent.com/pan8664716/MultiLive/main/output/kuaishou_live.m3u",
        "cover": TV_COVER,
        "remarks": "📱 快手直播",
        "type": "m3u",
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    },
    {
        "id": "bilibili_live",
        "name": "📺 B站直播",
        "url": "https://gh-proxy.org/https://raw.githubusercontent.com/pan8664716/MultiLive/main/output/bilibili_live.m3u",
        "cover": TV_COVER,
        "remarks": "📺 B站直播",
        "type": "m3u",
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    },
    {
        "id": "huya_live",
        "name": "🐯 虎牙直播",
        "url": "https://gh-proxy.org/https://raw.githubusercontent.com/pan8664716/MultiLive/main/output/huya_live.m3u",
        "cover": TV_COVER,
        "remarks": "🐯 虎牙直播",
        "type": "m3u",
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    },
    {
        "id": "douyu_live",
        "name": "🐟 斗鱼直播",
        "url": "https://gh-proxy.org/https://raw.githubusercontent.com/pan8664716/MultiLive/main/output/douyu_live.m3u",
        "cover": TV_COVER,
        "remarks": "🐟 斗鱼直播",
        "type": "m3u",
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    },
    {
        "id": "yy_live",
        "name": "🎤 YY直播",
        "url": "https://gh-proxy.org/https://raw.githubusercontent.com/pan8664716/MultiLive/main/output/yy_live.m3u",
        "cover": TV_COVER,
        "remarks": "🎤 YY直播",
        "type": "m3u",
        "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    },
]

LIVE_CATEGORY_ID = "online_live"
LIVE_CATEGORY_NAME = "📺 电视直播"
LIVE_CACHE_DURATION = 600

COMMON_HEADERS_LIST = [
    {
        "name": "Chrome浏览器",
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive"
        }
    },
    {
        "name": "Firefox浏览器",
        "headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
            "Connection": "keep-alive"
        }
    },
    {
        "name": "okhttp/3",
        "headers": {
            "User-Agent": "okhttp/3.12.11",
            "Accept": "*/*",
            "Connection": "Keep-Alive"
        }
    },
    {
        "name": "手机浏览器",
        "headers": {
            "User-Agent": "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive"
        }
    }
]
DOMAIN_SPECIFIC_HEADERS = {}

# ==================== 快捷网址（浏览器） ====================
QUICK_URLS = [
    {"name": "🌐 百度", "url": "https://www.baidu.com"},
    {"name": "🌐 谷歌", "url": "https://www.google.com"},
    {"name": "🌐 必应", "url": "https://www.bing.com"},
    {"name": "📱 抖音", "url": "https://www.douyin.com"},
    {"name": "📺 B站", "url": "https://www.bilibili.com"},
    {"name": "💬 微博", "url": "https://www.weibo.com"},
    {"name": "📖 知乎", "url": "https://www.zhihu.com"},
    {"name": "💻 GitHub", "url": "https://github.com"},
]


# ==================== 电台节目获取 ====================
class RadioProgramFetcher:
    _cache = {}
    _cache_time = {}
    
    @classmethod
    def get_current_program(cls, radio_id):
        cache_key = f"program_{radio_id}"
        current_time = time.time()
        if cache_key in cls._cache and current_time - cls._cache_time.get(cache_key, 0) < LIVE_PROGRAM_CACHE_DURATION:
            return cls._cache[cache_key]
        try:
            url = f"http://www.qingting.fm/radios/{radio_id}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "http://www.qingting.fm/",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = 'utf-8'
            html = response.text
            program_info = cls._parse_current_program(html, radio_id)
            if program_info:
                cls._cache[cache_key] = program_info
                cls._cache_time[cache_key] = current_time
                return program_info
            return None
        except Exception as e:
            return None
    
    @classmethod
    def _parse_current_program(cls, html, radio_id):
        program = {'current': '正在播出', 'next': '即将播出', 'current_time': '', 'next_time': ''}
        try:
            for pattern in [
                r'正在播放[：:]\s*<[^>]*>([^<]+)</',
                r'current-program[^>]*>.*?<span[^>]*>([^<]+)</span>',
                r'节目[：:]\s*([^<>\n]+)',
                r'"programName"\s*:\s*"([^"]+)"',
                r'<div class="program-name"[^>]*>([^<]+)</div>'
            ]:
                match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
                if match:
                    program['current'] = match.group(1).strip()
                    break
            for pattern in [
                r'(\d{1,2}:\d{2})\s*[-~]\s*(\d{1,2}:\d{2})',
                r'(\d{1,2}:\d{2})\s*至\s*(\d{1,2}:\d{2})'
            ]:
                match = re.search(pattern, html)
                if match:
                    program['current_time'] = f"{match.group(1)}-{match.group(2)}"
                    break
            for pattern in [
                r'即将播放[：:]\s*<[^>]*>([^<]+)</',
                r'next-program[^>]*>.*?<span[^>]*>([^<]+)</span>',
                r'下一节目[：:]\s*([^<>\n]+)'
            ]:
                match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
                if match:
                    program['next'] = match.group(1).strip()
                    break
            for key in ['current', 'next']:
                program[key] = re.sub(r'<[^>]+>', '', program[key])
                program[key] = re.sub(r'\s+', ' ', program[key]).strip()
                if len(program[key]) > 50:
                    program[key] = program[key][:47] + '...'
            if program['current'] == '正在播出' or len(program['current']) < 2:
                program['current'] = cls._get_time_based_program(radio_id)
            return program
        except Exception:
            return None
    
    @classmethod
    def _get_time_based_program(cls, radio_id):
        hour = time.localtime().tm_hour
        if 6 <= hour < 9:
            return "早安时段"
        elif 9 <= hour < 12:
            return "上午时段"
        elif 12 <= hour < 14:
            return "午间时段"
        elif 14 <= hour < 18:
            return "下午时段"
        elif 18 <= hour < 20:
            return "晚间时段"
        elif 20 <= hour < 23:
            return "黄金时段"
        else:
            return "深夜时段"


class RadioCoverRecord:
    @staticmethod
    def load_record():
        try:
            if os.path.exists(RADIO_SCAN_RECORD_FILE):
                with open(RADIO_SCAN_RECORD_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except:
            return {}
    
    @staticmethod
    def save_record(record):
        try:
            os.makedirs(os.path.dirname(RADIO_SCAN_RECORD_FILE), exist_ok=True)
            with open(RADIO_SCAN_RECORD_FILE, 'w', encoding='utf-8') as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    @staticmethod
    def is_cached(radio_id):
        record = RadioCoverRecord.load_record()
        return str(radio_id) in record
    
    @staticmethod
    def mark_cached(radio_id):
        record = RadioCoverRecord.load_record()
        record[str(radio_id)] = {'id': radio_id, 'time': time.time()}
        RadioCoverRecord.save_record(record)
    
    @staticmethod
    def clear_record():
        try:
            if os.path.exists(RADIO_SCAN_RECORD_FILE):
                os.remove(RADIO_SCAN_RECORD_FILE)
            return True
        except:
            return False


# ==================== 游戏大厅（含推荐游戏） ====================
class GameHall:
    def __init__(self):
        self.host = "https://www.yikm.net"
        self.default_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    def get_game_list(self):
        return [
            {"name": "原神启动！", "url": "https://ys.mihoyo.com/cloud/m/", "pic": "http://bkimg.cdn.bcebos.com/pic/b3fb43166d224f4a20a4a07a33a287529822720e7b06"},
            {"name": "星穹铁道", "url": "https://sr.mihoyo.com/cloud/m/#/", "pic": "https://i0.hdslb.com/bfs/archive/797c2063ea2ff6d4da0eb2d0fc2e6af84823fe1c.jpg"},
            {"name": "cs1.6", "url": "https://cs.yikm.net/", "pic": "http://i0.hdslb.com/bfs/archive/5215e07057f2cb16ae1d0ee3152574e8a5ce86df.jpg"},
            {"name": "好游快爆", "url": "https://m.3839.com/wap.html", "pic": "https://img2.baidu.com/it/u=3047577263,831634823&fm=253&fmt=auto&app=120&f=JPEG?w=800&h=800"},
            {"name": "TapTap", "url": "https://www.taptap.cn/", "pic": "https://i-1.win1img.com/2023/7/19/5521a1a6-26a7-4925-ba25-9f1d9322e9b4.png"},
            {"name": "网易云游戏", "url": "https://cg.163.com/#/game/recommend", "pic": "https://f7.baidu.com/it/u=1780904728,147993274&fm=222&app=106&f=PNG"},
            {"name": "抖音", "url": "https://www.douyin.com/?is_from_mobile_home=1", "pic": "https://img.izhida.com/img/68639897f9e2b45.jpg"},
            {"name": "永劫无间", "url": "https://cloudgame.ds.163.com/yjwj", "pic": "https://img2.baidu.com/it/u=3935699145,3148359625&fm=253&fmt=auto&app=138&f=JPEG?w=800&h=800"},
            {"name": "梦幻西游", "url": "https://xyh5.163.com/game/", "pic": "https://olimg.3dmgame.com/uploads/images/raiders/20211115/1636967876_896503.jpg"},
            {"name": "赛尔号", "url": "https://s.61.com/", "pic": "https://miaobi-lite.cdn.bcebos.com/miaobi/5mao/b%27LV8xNzM2MzYwNzQ5LjYyNTExNzg%3D%27/0.png"},
            {"name": "4399小游戏", "url": "https://h.4399.com/", "pic": "https://bkimg.cdn.bcebos.com/pic/2fdda3cc7cd98d1001e9211b6874af0e7bec54e73acc"},
            {"name": "一千个小游戏", "url": "https://fuun.fun/", "pic": "https://gips1.baidu.com/it/u=880356554,2373818629&fm=3074&app=3074&f=JPEG?w=1080&h=1410&type=normal&func="},
            {"name": "小霸王游戏机", "url": "https://www.yikm.net", "pic": "https://i0.hdslb.com/bfs/archive/5b87d08955493c3cfa64d09198dfc096af296da3.jpg"},
            {"name": "X的世界", "url": "https://bloxd.io", "pic": "https://img0.baidu.com/it/u=421321986,2018594644&fm=253&fmt=auto&app=138&f=JPEG?w=359&h=500"},
            {"name": "红色警戒2", "url": "https://ra2web.com/", "pic": "https://q5.itc.cn/images01/20250302/69c16a5e881f426e99108d7d729dc077.jpeg"},
            {"name": "贪吃蛇", "url": "http://slither.io/", "pic": "https://miaobi-lite.bj.bcebos.com/miaobi/5mao/b%276LSq5ZCD6JuH5ri45oiPXzE3MzI5MDM5NTEuODkzOTE4Mw%3D%3D%27/0.png"},
            {"name": "斗地主(人机)", "url": "https://www.haiwaiqipai.com/games/doudizhus/index.html", "pic": "https://i-1-333ttt.upimgt.com/2025/10/17/6bfe96a4-cf6b-4d24-a983-b21d5920825b.png"},
            {"name": "五子棋", "url": "https://wuziqi.hongton.com", "pic": "https://img2.baidu.com/it/u=170858330,816048848&fm=253&fmt=auto&app=138&f=JPG?w=500&h=500"},
            {"name": "中国象棋", "url": "https://game.haiyong.site/xiangqi/", "pic": "http://img1.baidu.com/it/u=2872582931,481942876&fm=253&fmt=auto&app=138&f=JPEG?w=800&h=1067"},
            {"name": "俄罗斯方块", "url": "https://v2fy.com/game/tetris/", "pic": "https://wx4.sinaimg.cn/mw690/80f256c3gy1hqfguyrc8lj20m814rafc.jpg"},
        ]
    
    def _build_game_action_item(self, name, url, pic=''):
        config = {'actionId': 'OPEN_URL', 'type': 'browser', 'title': name, 'url': url}
        if not pic:
            pic = f"https://picsum.photos/200/300?random={random.randint(1, 999)}"
        return {
            'vod_id': json.dumps(config, ensure_ascii=False),
            'vod_name': name,
            'vod_pic': pic,
            'vod_remarks': '点击开始游戏',
            'vod_tag': 'action',
            'style': {'type': 'grid', 'ratio': 0.75}
        }
    
    def _request(self, url, headers=None, timeout=10):
        import urllib.request
        if headers is None:
            headers = self.default_headers
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode('utf-8', errors='ignore')
        except Exception as e:
            return ''
    
    def _parse_game_list(self, html, pg):
        pattern = r'<div class="card-blog">.*?<img[^>]*src="([^"]+)".*?<h4><a href="([^"]+)"[^>]*>([^<]+)</a>'
        matches = re.findall(pattern, html, re.DOTALL)
        videos = []
        for pic, path, name in matches:
            game_url = path if path.startswith('http') else self.host + path
            videos.append(self._build_game_action_item(name.strip(), game_url, pic))
        if not videos:
            pattern2 = r'href="([^"]+)"[^>]*>([^<]+)</a>.*?src="([^"]+)"'
            matches2 = re.findall(pattern2, html, re.DOTALL)
            for path, name, pic in matches2:
                if '/nes' in path or '/play' in path:
                    game_url = path if path.startswith('http') else self.host + path
                    videos.append(self._build_game_action_item(name.strip(), game_url, pic))
        has_next_page = len(videos) >= 20
        return {
            'list': videos,
            'page': pg,
            'pagecount': pg + 1 if has_next_page else pg,
            'limit': len(videos),
            'total': len(videos)
        }
    
    def get_category_content(self, tid, pg, extend):
        pg = int(pg) if pg else 1
        if tid != 'game_hall':
            return None
        platform = 'custom'
        if extend and isinstance(extend, dict):
            platform = extend.get('platform', 'custom')
        if platform == 'custom':
            if pg != 1:
                return {'list': [], 'page': pg, 'pagecount': 1}
            videos = []
            for it in self.get_game_list():
                videos.append(self._build_game_action_item(it['name'], it['url'], it['pic']))
            total = len(videos)
            return {
                'list': videos,
                'page': pg,
                'pagecount': 1,
                'limit': total,
                'total': total
            }
        url_map = {
            'JAVA': 'net/nes?e=8&tag=',
            'fc': '/nes?tag=0&e=0&page=',
            'sfc': '/nes?tag=&e=5&page=',
            'arcade': '/nes?tag=9&e=&page=',
            'gba': '/nes?tag=&e=2&page=',
            'nds': '/nes?tag=&e=7&page=',
            'md': '/nes?tag=&e=3&page=',
            'dos': '/nes?tag=&e=6&page=',
        }
        if platform in url_map:
            target_url = self.host + url_map[platform] + str(pg)
            html = self._request(target_url, headers=self.default_headers)
            if html:
                return self._parse_game_list(html, pg)
        return {'list': [], 'page': pg, 'pagecount': 1}


# ==================== 主爬虫类 ====================
class Spider(Spider):
    def getName(self):
        return "在线内容聚合"

    def init(self, extend=""):
        super().init(extend)

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }

        self.online_live_sources = ONLINE_LIVE_SOURCES
        self.live_category_id = LIVE_CATEGORY_ID
        self.live_category_name = LIVE_CATEGORY_NAME
        self.live_cache = {}
        self.live_cache_time = {}
        self.live_cache_duration = LIVE_CACHE_DURATION

        self.radio_cache = {}
        self.radio_cache_time = {}

        self.common_headers_list = COMMON_HEADERS_LIST
        self.domain_specific_headers = DOMAIN_SPECIFIC_HEADERS

        self.video_cache = {}
        self.video_cache_time = {}
        self.video_cover_apis = [
            "https://api.71xk.com/api/picture/v1",
            "https://api.6045833.xyz/wsmeinv",
            "https://api.eyabc.cn/api/picture/beauty",
            "http://api.lbbb.cc/api/baisi",
            "http://api.lbbb.cc/api/heisi",
        ]

        self.short_video_apis = [
            {"name": "🎬 小姐姐1", "url": "http://av.npcq.cn/pc.php"},
            {"name": "🎬 小姐姐2", "url": "https://diskgirl.com/get/get2.php"},
            {"name": "🎬 小姐姐3", "url": "https://www.xiaolufx.net/suiji/video.php?_t="},
            {"name": "🎬 小姐姐4", "url": "https://www.cunshao.com/666666/api/web.php"},
            {"name": "🎬 小姐姐5", "url": "http://api.yujn.cn/api/zzxjj.php"},
            {"name": "🎬 小姐姐6", "url": "https://www.cunshao.com/666666/api/pc.php"},
            {"name": "🎬 小姐姐7", "url": "https://v.api.aa1.cn/api/api-dy-girl/index.php?aa1=ajdu987hrjfw"},
            {"name": "小姐姐8", "url": "https://api.ksse.cn/API/sp/sjxjj2.php"},
            {"name": "小姐姐9", "url": "https://api.ksse.cn/API/sp/bs.php"},
            {"name": "随机慢摇视频", "url": "https://api.bi71t5.cn/api/my.php"},
            {"name": "🎬 少妇视频", "url": "http://v.nrzj.vip/video.php?_t=0.9"},
            {"name": "🎬 高质量小姐姐", "url": "http://api.tinise.cn/api/xjjsp"},
            {"name": "🎬 抖音小姐姐", "url": "http://api.qemao.com/api/douyin/"},
            {"name": "🎬 完美身材", "url": "http://api.yujn.cn/api/wmsc.php?type=video"},
            {"name": "🎬 快手变装", "url": "http://api.yujn.cn/api/ksbianzhuang.php?type=video"},
            {"name": "🎬 抖音变装", "url": "http://api.yujn.cn/api/bianzhuang.php?"},
            {"name": "🤍 白丝视频", "url": "http://api.yujn.cn/api/baisis.php?type=video"},
            {"name": "👗 美女穿搭", "url": "http://api.yujn.cn/api/chuanda.php?type=video"},
            {"name": "🎲 随机小姐姐", "url": "http://api.yujn.cn/api/xjj.php?type=video"},
            {"name": "🖤 黑丝视频", "url": "http://api.yujn.cn/api/heisis.php?type=video"},
            {"name": "🎓 女大学生", "url": "https://api.yujn.cn/api/nvda.php?type=video"},
            {"name": "👁️ 抖音瞳瞳", "url": "https://api.yujn.cn/api/tongtong.php?type=video"},
            {"name": "💃 丝滑舞蹈", "url": "http://api.yujn.cn/api/shwd.php?type=video"},
            {"name": "🏮 古风类", "url": "http://api.yujn.cn/api/hanfu.php?type=video"},
            {"name": "🎧 慢摇系列", "url": "http://api.yujn.cn/api/manyao.php?type=video"},
            {"name": "👙 吊带系列", "url": "http://api.yujn.cn/api/diaodai.php?type=video"},
            {"name": "🌸 清纯系列", "url": "http://api.yujn.cn/api/qingchun.php?type=video"},
            {"name": "🎮 COS系列", "url": "http://api.yujn.cn/api/COS.php?type=video"},
            {"name": "🎀 萝莉系列", "url": "http://api.yujn.cn/api/luoli.php?type=video"},
            {"name": "🍬 甜妹系列", "url": "http://api.yujn.cn/api/tianmei.php?type=video"},
        ]

        self.gallery_apis = [
            {"name": "🎨 图源C", "url": "https://api.bi71t5.cn/api/hs.php", "type": "random"},
            {"name": "🎨 图源D", "url": "http://api.iappht.vip/api/suijixiaojiejietupian", "type": "random"},
            {"name": "🎨 图源E", "url": "https://sucyan.top/api/tupian/jk.php", "type": "random"},
            {"name": "🎨 图源F", "url": "https://a.aa.cab/mn2.api", "type": "random"},
            {"name": "🎨 图源G", "url": "https://a.aa.cab/mn.api", "type": "random"},
            {"name": "🎨 图源H", "url": "https://a.aa.cab/cos.api", "type": "random"},
            {"name": "🎨 图源J", "url": "https://api.6045833.xyz/wsbizhi", "type": "random"},
            {"name": "🎨 图源l", "url": "https://pic.ltywl.top/mn/pe.php?r={time}", "type": "random"},
            {"name": "🎨 图源m", "url": "https://api.6045833.xyz/meinv?r={time}", "type": "random"},
            {"name": "👗 丝袜美女", "url": "https://api.6045833.xyz/wsmeinv", "type": "random"},
            {"name": "🎀美女图片", "url": "http://ryapi.sbs/API/beauty.php", "type": "random"},
            {"name": "🌸 唯美图片", "url": "https://api-v2.cenguigui.cn/api/meizi/", "type": "random"},
            {"name": "🎊二次元", "url": "https://api.suyanw.cn/api/comic3.php", "type": "random"},
            {"name": "🦺东篱随机壁纸", "url": "https://tu.ltyuanfang.cn/api/fengjing.php", "type": "random"},
            {"name": "🌁多多壁纸", "url": "https://yydsys.top/bg.php", "type": "random"},
        ]

        self.game_hall = GameHall()

        self.session = requests.Session()
        retries = Retry(total=2, backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

        self.cached_radio_ids = set()
        self._load_cached_radio_ids()
        self.preload_executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="CoverPreload")

        self.TRANSPARENT_GIF = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'

    def _load_cached_radio_ids(self):
        try:
            if os.path.exists(RADIO_COVER_CACHE_DIR):
                for filename in os.listdir(RADIO_COVER_CACHE_DIR):
                    if filename.endswith('.jpg') and filename != '.nomedia':
                        radio_id = filename.replace('.', '').replace('jpg', '')
                        if radio_id and radio_id.isdigit():
                            self.cached_radio_ids.add(radio_id)
        except:
            pass

    def b64u_encode(self, data):
        if isinstance(data, str):
            data = data.encode('utf-8')
        encoded = base64.b64encode(data).decode('ascii')
        return encoded.replace('+', '-').replace('/', '_').rstrip('=')

    def b64u_decode(self, data):
        data = data.replace('-', '+').replace('_', '/')
        pad = len(data) % 4
        if pad:
            data += '=' * (4 - pad)
        try:
            return base64.b64decode(data).decode('utf-8')
        except:
            return ''

    def e64(self, text):
        return base64.b64encode(text.encode("utf-8")).decode("utf-8")

    def d64(self, text):
        return base64.b64decode(text.encode("utf-8")).decode("utf-8")

    def _cache_radio_cover(self, radio_id, image_url):
        if not image_url:
            return None
        try:
            cache_file = f"{RADIO_COVER_CACHE_DIR}.{radio_id}.jpg"
            if os.path.exists(cache_file):
                self.cached_radio_ids.add(str(radio_id))
                return cache_file
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "http://www.qingting.fm/"
            }
            response = self.session.get(image_url, headers=headers, timeout=15)
            if response.status_code == 200:
                img_data = response.content
                with open(cache_file, 'wb') as f:
                    f.write(img_data)
                self.cached_radio_ids.add(str(radio_id))
                RadioCoverRecord.mark_cached(radio_id)
                return cache_file
            return None
        except:
            return None

    def _get_radio_cached_cover_path(self, radio_id):
        cache_file1 = f"{RADIO_COVER_CACHE_DIR}.{radio_id}.jpg"
        cache_file2 = f"{RADIO_COVER_CACHE_DIR}{radio_id}.jpg"
        if os.path.exists(cache_file1):
            return cache_file1
        if os.path.exists(cache_file2):
            return cache_file2
        return None

    def _generate_colored_icon(self, color, text):
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
            <rect width="200" height="200" rx="40" ry="40" fill="{color}"/>
            <circle cx="100" cy="100" r="70" fill="white" opacity="0.3"/>
            <text x="100" y="140" font-size="100" text-anchor="middle" fill="white" font-family="Arial" font-weight="bold">{text}</text>
        </svg>'''
        return f"data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}"

    def _make_random_url(self, api_url):
        if '?' in api_url:
            return f"{api_url}&_r={random.randint(1, 999999)}&_t={int(time.time())}"
        else:
            return f"{api_url}?_r={random.randint(1, 999999)}&_t={int(time.time())}"

    def _get_video_cover(self, api_name):
        cover_apis = self.video_cover_apis
        idx = hash(api_name) % len(cover_apis)
        cover_api = cover_apis[idx]
        return self._make_random_url(cover_api)

    def _get_real_video_url(self, api_url):
        cache_key = f"real_url_{api_url}"
        if cache_key in self.video_cache:
            cache_time = self.video_cache_time.get(cache_key, 0)
            if time.time() - cache_time < 300:
                return self.video_cache[cache_key]
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Referer": "https://www.douyin.com/"
            }
            resp = self.session.get(api_url, headers=headers, timeout=15, allow_redirects=True)
            final_url = resp.url
            if any(ext in final_url.lower() for ext in ['.mp4', '.m3u8', '.flv', '.mov']):
                self.video_cache[cache_key] = final_url
                self.video_cache_time[cache_key] = time.time()
                return final_url
            content_type = resp.headers.get('Content-Type', '')
            if 'video' in content_type:
                self.video_cache[cache_key] = api_url
                self.video_cache_time[cache_key] = time.time()
                return api_url
            if resp.text:
                patterns = [
                    r'(https?://[^\s"\']+\.mp4[^\s"\']*)',
                    r'(https?://[^\s"\']+\.m3u8[^\s"\']*)',
                    r'(https?://[^\s"\']+\.flv[^\s"\']*)',
                    r'"url"\s*:\s*"([^"]+)"',
                    r'"video_url"\s*:\s*"([^"]+)"',
                    r'"play_url"\s*:\s*"([^"]+)"',
                ]
                for pattern in patterns:
                    match = re.search(pattern, resp.text, re.IGNORECASE)
                    if match:
                        video_url = match.group(1).replace('\\/', '/')
                        self.video_cache[cache_key] = video_url
                        self.video_cache_time[cache_key] = time.time()
                        return video_url
            self.video_cache[cache_key] = api_url
            self.video_cache_time[cache_key] = time.time()
            return api_url
        except:
            return api_url

    def _get_video_list(self, api_url, count=30):
        videos = []
        for i in range(count):
            videos.append(self._make_random_url(api_url))
        return videos

    def _get_domain_from_url(self, url):
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            return domain.split(':')[0] if ':' in domain else domain
        except:
            return ""

    def _fetch_with_auto_headers(self, url, source=None):
        domain = self._get_domain_from_url(url)
        if source:
            custom_headers = {}
            if source.get('ua'):
                custom_headers['User-Agent'] = source['ua']
            if source.get('referer'):
                custom_headers['Referer'] = source['referer']
            if source.get('origin'):
                custom_headers['Origin'] = source['origin']
            if custom_headers:
                custom_headers['Accept'] = '*/*'
                custom_headers['Accept-Language'] = 'zh-CN,zh;q=0.9,en;q=0.8'
                custom_headers['Connection'] = 'keep-alive'
                custom_headers['Accept-Encoding'] = 'gzip, deflate'
                try:
                    resp = self.session.get(url, headers=custom_headers, timeout=15)
                    if resp.status_code == 200:
                        return resp.text
                except Exception:
                    pass
        if domain in self.domain_specific_headers:
            for headers_info in self.domain_specific_headers[domain]:
                try:
                    resp = self.session.get(url, headers=headers_info['headers'], timeout=15)
                    if resp.status_code == 200:
                        return resp.text
                except:
                    continue
        for headers_info in self.common_headers_list:
            try:
                resp = self.session.get(url, headers=headers_info['headers'], timeout=10)
                if resp.status_code == 200:
                    return resp.text
            except:
                continue
        try:
            resp = self.session.get(url, headers=self.headers, timeout=15)
            if resp.status_code == 200:
                return resp.text
        except:
            pass
        return None

    def _get_live_programs(self, source):
        source_id = source['id']
        current_time = time.time()
        if source_id in self.live_cache and current_time - self.live_cache_time.get(source_id, 0) < self.live_cache_duration:
            return self.live_cache[source_id]
        content = self._fetch_with_auto_headers(source['url'], source)
        if not content:
            return []
        programs = self._parse_live_content(content, source)
        if programs:
            self.live_cache[source_id] = programs
            self.live_cache_time[source_id] = current_time
        return programs

    def _parse_live_content(self, content, source):
        if source.get('type') == 'txt' or ',#genre#' in content:
            return self._parse_txt_live(content)
        elif content.strip().startswith(('{', '[')):
            return self._parse_json_live(content)
        else:
            return self._parse_m3u_live(content)

    def _parse_m3u_live(self, content):
        programs = []
        lines = content.split('\n')
        current_name = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith('#EXTINF:'):
                name_match = re.search(r',(.+)$', line) or re.search(r'tvg-name="([^"]+)"', line)
                current_name = name_match.group(1).strip() if name_match else None
            elif line and not line.startswith('#') and current_name:
                if self.is_playable_url(line):
                    programs.append({'name': current_name, 'url': line})
                current_name = None
        return programs

    def _parse_txt_live(self, content):
        programs = []
        lines = content.split('\n')
        current_cat = None
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if ',#genre#' in line:
                current_cat = line.split(',')[0].strip()
                continue
            if ',' in line:
                parts = line.split(',', 1)
                name = parts[0].strip()
                url = parts[1].strip()
                if self.is_playable_url(url):
                    display_name = f"[{current_cat}] {name}" if current_cat else name
                    programs.append({'name': display_name, 'url': url})
        return programs

    def _parse_json_live(self, content):
        programs = []
        try:
            data = json.loads(content)
            items = []
            if isinstance(data, dict):
                for key in ['list', 'data', 'items', 'videos']:
                    if key in data and isinstance(data[key], list):
                        items = data[key]
                        break
                if not items:
                    items = [data]
            else:
                items = data
            for item in items:
                if isinstance(item, dict):
                    name = item.get('name') or item.get('title')
                    url = item.get('url') or item.get('play_url')
                    if name and url and self.is_playable_url(url):
                        programs.append({'name': name, 'url': url})
        except:
            pass
        return programs

    def is_playable_url(self, url):
        u = str(url).lower().strip()
        if not u:
            return False
        protocols = [
            'http://', 'https://', 'rtmp://', 'rtsp://', 'udp://', 'rtp://',
            'file://', 'pics://', 'mp3://', 'magnet:', 'ed2k://', 'thunder://', 'ftp://',
            'vod://', 'bilibili://', 'youtube://', 'rtmps://', 'rtmpt://', 'hls://',
            'http-live://', 'https-live://', 'tvbus://', 'tvbox://', 'live://', 'novel://', 'text://'
        ]
        if any(u.startswith(p) for p in protocols):
            return True
        exts = [
            '.mp4', '.mkv', '.avi', '.rmvb', '.mov', '.wmv', '.flv',
            '.m3u8', '.ts', '.mp3', '.m4a', '.aac', '.flac', '.wav',
            '.webm', '.ogg', '.m4v', '.f4v', '.3gp', '.mpg', '.mpeg',
            '.m3u', '.pls', '.asf', '.asx', '.wmx'
        ]
        if any(ext in u for ext in exts):
            return True
        patterns = [
            'youtu.be/', 'youtube.com/', 'bilibili.com/', 'iqiyi.com/',
            'v.qq.com/', 'youku.com/', 'tudou.com/', 'mgtv.com/',
            'sohu.com/', 'acfun.cn/', 'douyin.com/', 'kuaishou.com/',
            'huya.com/', 'douyu.com/', 'twitch.tv/', 'live.'
        ]
        return any(p in u for p in patterns)

    def _get_radios_by_category(self, category_id):
        cache_key = f"radio_category_{category_id}"
        current_time = time.time()
        if cache_key in self.radio_cache and current_time - self.radio_cache_time.get(cache_key, 0) < 1800:
            return self.radio_cache[cache_key]
        file_cache_path = f"/storage/emulated/0/tmp/radio_list_{category_id}.json"
        if os.path.exists(file_cache_path):
            try:
                mtime = os.path.getmtime(file_cache_path)
                if current_time - mtime < 86400:
                    with open(file_cache_path, 'r', encoding='utf-8') as f:
                        all_radios = json.load(f)
                    self.radio_cache[cache_key] = all_radios
                    self.radio_cache_time[cache_key] = current_time
                    return all_radios
            except:
                pass
        all_radios = []
        page = 1
        while True:
            url = f"http://www.qingting.fm/radiopage/{category_id}/{page}"
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "http://www.qingting.fm/",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                }
                response = self.session.get(url, headers=headers, timeout=15)
                response.encoding = 'utf-8'
                html = response.text
                if '<div class="radio' not in html and 'class="radio-item"' not in html:
                    break
                radios = self._parse_radio_page(html)
                if not radios:
                    break
                existing_ids = {r['id'] for r in all_radios}
                for radio in radios:
                    if radio['id'] not in existing_ids:
                        all_radios.append(radio)
                        existing_ids.add(radio['id'])
                if len(radios) < 12:
                    break
                page += 1
                time.sleep(0.3)
            except:
                break
        try:
            with open(file_cache_path, 'w', encoding='utf-8') as f:
                json.dump(all_radios, f, ensure_ascii=False, indent=2)
        except:
            pass
        self.radio_cache[cache_key] = all_radios
        self.radio_cache_time[cache_key] = current_time
        return all_radios

    def _parse_radio_page(self, html):
        radios = []
        try:
            from pyquery import PyQuery as pq
            doc = pq(html)
            items = doc(".contentSec .radio, .radio-list .radio-item")
            for li in items.items():
                a = li("a").eq(0)
                href = a.attr("href") or ""
                radio_id_match = re.search(r'/radios/(\d+)', href)
                if not radio_id_match:
                    continue
                radio_id = radio_id_match.group(1)
                name = li("span").text() or a.attr("title") or a.text() or li(".name").text()
                if not name:
                    continue
                name = name.strip()
                pic = li("img").attr("src") or ""
                if pic:
                    if pic.startswith('//'):
                        pic = 'http:' + pic
                    elif not pic.startswith('http'):
                        pic = 'http://www.qingting.fm' + pic
                    pic = pic.replace('/160/', '/300/').replace('/120/', '/300/')
                    pic = pic.replace('//', '/').replace('http:/', 'http://')
                desc = li(".descRadio, .desc, .radio-desc").text() or "直播中"
                desc = desc.strip()
                radios.append({'id': radio_id, 'name': name, 'pic': pic, 'desc': desc})
        except ImportError:
            pattern = r'<a[^>]*href="/radios/(\d+)"[^>]*>.*?<img[^>]*src="([^"]+)"[^>]*>.*?<span[^>]*>([^<]+)</span>'
            matches = re.findall(pattern, html, re.DOTALL)
            for radio_id, pic, name in matches:
                name = name.strip()
                if name and len(name) > 1:
                    if pic:
                        if pic.startswith('//'):
                            pic = 'http:' + pic
                        elif not pic.startswith('http'):
                            pic = 'http://www.qingting.fm' + pic
                        pic = pic.replace('/160/', '/300/').replace('/120/', '/300/')
                    radios.append({'id': radio_id, 'name': name, 'pic': pic, 'desc': "蜻蜓FM"})
        return radios

    # ==================== homeContent ====================
    def homeContent(self, filter):
        classes = [
            {"type_id": self.live_category_id, "type_name": self.live_category_name},
            {"type_id": "online_radio", "type_name": "📻 网络电台"},
            {"type_id": "short_video", "type_name": "📱 短视频"},
            {"type_id": "gallery", "type_name": "🎨 画廊"},
            {"type_id": "game_hall", "type_name": "🎮 游戏大厅"},
            {"type_id": "web_browser", "type_name": "🌐 网页浏览器"},
        ]

        filters = {
            "online_radio": [{
                "key": "category",
                "name": "📻 电台分类",
                "value": [
                    {"n": "🎵 音乐电台", "v": "442"}, {"n": "🚗 交通电台", "v": "429"},
                    {"n": "📻 江苏电台", "v": "85"}, {"n": "📻 广东电台", "v": "217"},
                    {"n": "📻 浙江电台", "v": "99"}, {"n": "📻 北京电台", "v": "3"},
                    {"n": "📻 天津电台", "v": "5"}, {"n": "📻 河北电台", "v": "7"},
                    {"n": "📻 上海电台", "v": "83"}, {"n": "📻 山西电台", "v": "19"},
                    {"n": "📻 内蒙古电台", "v": "31"}, {"n": "📻 辽宁电台", "v": "44"},
                    {"n": "📻 吉林电台", "v": "59"}, {"n": "📻 黑龙江电台", "v": "69"},
                    {"n": "📻 安徽电台", "v": "111"}, {"n": "📻 福建电台", "v": "129"},
                    {"n": "📻 江西电台", "v": "139"}, {"n": "📻 山东电台", "v": "151"},
                    {"n": "📻 河南电台", "v": "169"}, {"n": "📻 湖北电台", "v": "187"},
                    {"n": "📻 湖南电台", "v": "202"}, {"n": "📻 广西电台", "v": "239"},
                    {"n": "📻 海南电台", "v": "254"}, {"n": "📻 重庆电台", "v": "257"},
                    {"n": "📻 四川电台", "v": "259"}, {"n": "📻 贵州电台", "v": "281"},
                    {"n": "📻 云南电台", "v": "291"}, {"n": "📻 陕西电台", "v": "316"},
                    {"n": "📻 甘肃电台", "v": "327"}, {"n": "📻 宁夏电台", "v": "351"},
                    {"n": "📻 新疆电台", "v": "357"}, {"n": "📻 西藏电台", "v": "308"},
                    {"n": "📻 青海电台", "v": "342"}, {"n": "🎤 资讯电台", "v": "433"},
                    {"n": "💰 经济电台", "v": "439"}, {"n": "🎭 文艺电台", "v": "432"},
                    {"n": "🏙️ 都市电台", "v": "441"}, {"n": "⚽ 体育电台", "v": "430"},
                    {"n": "🌐 双语电台", "v": "431"}, {"n": "📰 综合电台", "v": "440"},
                    {"n": "🏠 生活电台", "v": "438"}, {"n": "✈️ 旅游电台", "v": "435"},
                    {"n": "🎪 曲艺电台", "v": "436"}, {"n": "🗣️ 方言电台", "v": "434"}
                ]
            }],
            "game_hall": [{
                "key": "platform",
                "name": "🎮 游戏平台",
                "value": [
                    {"n": "🎯推荐游戏", "v": "custom"},
                    {"n": "🕹FC游戏", "v": "fc"}, {"n": "🕹SFC游戏", "v": "sfc"},
                    {"n": "🕹街机游戏", "v": "arcade"}, {"n": "🕹GBA游戏", "v": "gba"},
                    {"n": "🕹NDS游戏", "v": "nds"}, {"n": "🕹MD游戏", "v": "md"},
                    {"n": "🕹DOS游戏", "v": "dos"},
                ]
            }],
        }

        return {'class': classes, 'filters': filters}

    # ==================== categoryContent ====================
    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg) if pg else 1

        if tid == "game_hall":
            return self.game_hall.get_category_content(tid, pg, extend)

        if tid == "online_radio":
            cat_id = extend.get("category", "442") if extend and isinstance(extend, dict) else "442"
            return self._online_radio_content(cat_id, pg)

        if tid == "short_video":
            return self._short_video_category_content(pg)

        if tid == "gallery":
            return self._gallery_category_content(pg)

        if tid == self.live_category_id:
            return self._live_category_content(pg)

        if tid == "web_browser":
            return self._web_browser_content(pg)

        return {'list': [], 'page': pg, 'pagecount': 1}

    # ==================== 各模块实现 ====================
    def _online_radio_content(self, category_id, pg):
        pg = int(pg) if pg else 1
        radios = self._get_radios_by_category(category_id)
        if not radios:
            return {'list': [], 'page': pg, 'pagecount': 1}
        vlist = []
        for radio in radios:
            radio_id = str(radio['id'])
            radio_name = radio['name']
            if radio_id in self.cached_radio_ids:
                pic = f"file://{RADIO_COVER_CACHE_DIR}.{radio_id}.jpg"
            else:
                pic = radio.get('pic', '')
                if pic and not RadioCoverRecord.is_cached(radio_id):
                    self.preload_executor.submit(self._cache_radio_cover, radio_id, pic)
            remarks = radio.get('desc', '蜻蜓FM')
            vlist.append({
                'vod_id': radio_id,
                'vod_name': radio_name,
                'vod_pic': pic,
                'vod_remarks': remarks,
                'style': {'type': 'grid', 'ratio': 0.75},
                'vod_player': '听'
            })
        per_page = 30
        total = len(vlist)
        start = (pg - 1) * per_page
        end = min(start + per_page, total)
        pagecount = (total + per_page - 1) // per_page if total > 0 else 1
        return {
            'list': vlist[start:end],
            'page': pg,
            'pagecount': pagecount,
            'limit': per_page,
            'total': total
        }

    def _radio_detail_content(self, radio_id):
        radio_id = str(radio_id)
        if radio_id in self.cached_radio_ids:
            radio_pic_url = f"file://{RADIO_COVER_CACHE_DIR}.{radio_id}.jpg"
        else:
            cached_cover = self._get_radio_cached_cover_path(radio_id)
            if cached_cover:
                self.cached_radio_ids.add(radio_id)
                radio_pic_url = f"file://{cached_cover}"
            else:
                radio_pic_url = ""
        radio_name = f"电台_{radio_id}"
        for cache_key in self.radio_cache:
            for radio in self.radio_cache[cache_key]:
                if str(radio['id']) == radio_id:
                    radio_name = radio['name']
                    break
            if radio_name != f"电台_{radio_id}":
                break
        program_info = RadioProgramFetcher.get_current_program(radio_id)
        play_url = f"http://lhttp.qingting.fm/live/{radio_id}/64k.mp3"
        encoded_play_url = self.e64(f"0@@@@{play_url}")
        program_text = ""
        if program_info:
            program_text = f"🎙️ 正在播放: {program_info.get('current', '加载中')}"
            if program_info.get('current_time'):
                program_text += f" ({program_info['current_time']})"
            if program_info.get('next') and program_info['next'] != '即将播出':
                program_text += f"\n⏩ 下一节目: {program_info['next']}"
        else:
            program_text = "🎙️ 正在播出"
        vod = {
            "vod_id": radio_id,
            "vod_name": radio_name,
            "vod_pic": radio_pic_url,
            "vod_actor": "蜻蜓FM",
            "vod_remarks": program_text,
            "vod_content": program_text,
            "vod_play_from": "蜻蜓FM",
            "vod_play_url": f"播放${encoded_play_url}",
            "style": {"type": "list"},
            "vod_player": "听"
        }
        return {"list": [vod]}

    def _live_category_content(self, pg):
        vlist = []
        for idx, source in enumerate(self.online_live_sources):
            encoded_id = self.b64u_encode(source['id'])
            cover = source.get('cover', TV_COVER)
            remarks = source.get('remarks', '直播源')
            vlist.append({
                'vod_id': f"live://{encoded_id}",
                'vod_name': source['name'],
                'vod_pic': cover,
                'vod_remarks': remarks,
                'vod_tag': 'live_source',
                'style': {'type': 'grid', 'ratio': 0.75},
                'type': 'live'
            })
        return {'list': vlist, 'page': pg, 'pagecount': 1, 'limit': len(vlist), 'total': len(vlist)}

    def _live_source_detail(self, source_id):
        source = next((s for s in self.online_live_sources if s['id'] == source_id), None)
        if not source:
            return {'list': []}
        cover = source.get('cover', TV_COVER)
        programs = self._get_live_programs(source)
        if not programs:
            return {'list': [{
                'vod_id': f"live://{self.b64u_encode(source_id)}",
                'vod_name': source['name'],
                'vod_pic': cover,
                'vod_play_from': '直播源',
                'vod_play_url': '提示$无法获取直播源，请稍后重试',
                'vod_content': f"直播源: {source['url']}\n状态: 获取失败",
                'style': {'type': 'list'},
                'type': 'live',
                'playerType': source.get('playerType', 2)
            }]}
        channels = {}
        for p in programs:
            name = p['name']
            clean_name = re.sub(r'^\[[^\]]+\]\s*', '', name)
            clean_name = re.sub(r'\s*[\[\(（]\s*\d+\s*[\]\)）]\s*$', '', clean_name)
            if clean_name not in channels:
                channels[clean_name] = []
            channels[clean_name].append(p['url'])
        max_lines = max(len(urls) for urls in channels.values())
        original_max_lines = max_lines
        if max_lines > 1:
            max_lines = 1
        ua = source.get('ua', '')
        referer = source.get('referer', '')
        ua_info = self.b64u_encode(json.dumps({'ua': ua, 'referer': referer}))
        from_list = []
        url_list = []
        for line_idx in range(max_lines):
            line_name = f"线路{line_idx + 1}"
            channel_urls = []
            for channel_name, urls in channels.items():
                if line_idx < len(urls):
                    enhanced_url = urls[line_idx] + f"|UAINFO|{ua_info}"
                    channel_urls.append(f"{channel_name}${enhanced_url}")
            if channel_urls:
                from_list.append(line_name)
                url_list.append('#'.join(channel_urls))
        if not from_list:
            return {'list': [{
                'vod_id': f"live://{self.b64u_encode(source_id)}",
                'vod_name': source['name'],
                'vod_pic': cover,
                'vod_play_from': '直播源',
                'vod_play_url': '提示$没有可用的线路',
                'vod_content': f"直播源: {source['url']}\n状态: 没有可用的线路",
                'style': {'type': 'list'},
                'type': 'live',
                'playerType': source.get('playerType', 2)
            }]}
        current_date = time.strftime('%Y.%m.%d', time.localtime())
        total_channels = len(channels)
        total_programs = sum(len(urls) for urls in channels.values())
        remarks = f'更新时间{current_date}'
        if original_max_lines > 1:
            remarks += f' (仅显示第1条线路)'
        return {'list': [{
            'vod_id': f"live://{self.b64u_encode(source_id)}",
            'vod_name': source['name'],
            'vod_pic': cover,
            'vod_play_from': '$$$'.join(from_list),
            'vod_play_url': '$$$'.join(url_list),
            'vod_remarks': remarks,
            'vod_content': f"共 {total_channels} 个频道，{total_programs} 条节目线路",
            'vod_style': {'type': 'live'},
            'vod_type': 4,
            'vod_class': 'live',
            'type': 'live',
            'playerType': source.get('playerType', 2)
        }]}

    def _short_video_category_content(self, pg):
        vlist = []
        for idx, api in enumerate(self.short_video_apis):
            encoded_url = self.b64u_encode(api['url'])
            cover_url = self._get_video_cover(api['name'])
            vlist.append({
                'vod_id': f"short_video_{encoded_url}",
                'vod_name': api['name'],
                'vod_pic': cover_url,
                'vod_remarks': '点击播放短视频',
                'style': {'type': 'grid', 'ratio': 0.75},
                'vod_player': '短'
            })
        return {'list': vlist, 'page': 1, 'pagecount': 1, 'limit': len(vlist), 'total': len(vlist)}

    def _short_video_detail(self, encoded_url):
        try:
            api_url = self.b64u_decode(encoded_url)
        except:
            return {'list': []}
        api_name = "短视频源"
        for api in self.short_video_apis:
            if api['url'] == api_url:
                api_name = api['name']
                break
        cover_url = self._get_video_cover(api_name)
        video_urls = self._get_video_list(api_url, 100)
        play_urls = []
        for i, url in enumerate(video_urls):
            play_urls.append(f"视频{i+1}${url}")
        vod = {
            'vod_id': f"short_video_detail_{encoded_url}",
            'vod_name': f"{api_name} (100个视频)",
            'vod_pic': cover_url,
            'vod_play_from': '短视频播放',
            'vod_play_url': '#'.join(play_urls),
            'vod_remarks': f'共100个随机短视频',
            'style': {'type': 'list'},
            'vod_player': '短'
        }
        return {'list': [vod]}

    def _handle_short_video_play(self, video_url):
        real_url = self._get_real_video_url(video_url)
        return {
            "parse": 0,
            "playUrl": "",
            "url": real_url,
            "header": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://www.douyin.com/",
                "Accept": "video/mp4,video/*;q=0.9,*/*;q=0.8"
            },
            "vod_player": "短"
        }

    def _gallery_category_content(self, pg):
        vlist = []
        for idx, api in enumerate(self.gallery_apis):
            encoded_url = self.b64u_encode(api['url'])
            if '?' in api['url']:
                preview_url = f"{api['url']}&_r={random.randint(1, 999999)}&_t={int(time.time())}"
            else:
                preview_url = f"{api['url']}?_r={random.randint(1, 999999)}&_t={int(time.time())}"
            vlist.append({
                'vod_id': f"gallery_{api['type']}_{encoded_url}",
                'vod_name': api['name'],
                'vod_pic': preview_url,
                'vod_remarks': '点击查看50张',
                'style': {'type': 'grid', 'ratio': 0.75},
                'vod_player': '画'
            })
        return {'list': vlist, 'page': 1, 'pagecount': 1, 'limit': len(vlist), 'total': len(vlist)}

    def _gallery_detail(self, api_type, encoded_url):
        try:
            api_url = self.b64u_decode(encoded_url)
        except:
            return {'list': []}
        api_name = "图库"
        for api in self.gallery_apis:
            if api['url'] == api_url:
                api_name = api['name']
                break
        images = []
        for i in range(50):
            if '?' in api_url:
                rand_url = f"{api_url}&_r={random.randint(1, 999999)}&_t={int(time.time())}"
            else:
                rand_url = f"{api_url}?_r={random.randint(1, 999999)}&_t={int(time.time())}"
            images.append(rand_url)
        pics_protocol = "pics://" + '&&'.join(images)
        vod = {
            'vod_id': f"gallery_{api_type}_{encoded_url}",
            'vod_name': f"{api_name} (50张)",
            'vod_pic': images[0],
            'vod_play_from': '图片浏览',
            'vod_play_url': f"播放${pics_protocol}",
            'vod_remarks': '共50张图片',
            'style': {'type': 'list'},
            'vod_player': '画'
        }
        return {'list': [vod]}

    # ==================== 网页浏览器 ====================
    def _web_browser_content(self, pg):
        items = []
        # 输入框入口
        input_config = json.dumps({
            "actionId": "单项输入",
            "id": "text",
            "type": "input",
            "title": "🌐 输入网址",
            "tip": "请输入网址，如 baidu.com 或 https://xxx.com",
            "value": "",
            "msg": "请输入网址"
        }, ensure_ascii=False)
        items.append({
            'vod_id': input_config,
            'vod_name': '🔍 输入网址跳转',
            'vod_pic': self._generate_colored_icon("#4CAF50", "🔍"),
            'vod_remarks': '点击后输入网址，自动打开',
            'vod_tag': 'action',
            'style': {'type': 'list'},
            'vod_player': '书'
        })

        # 分隔线
        items.append({
            'vod_id': 'separator',
            'vod_name': '———————————— 常用网址 ————————————',
            'vod_pic': self.TRANSPARENT_GIF,
            'vod_remarks': '',
            'style': {'type': 'list'},
            'vod_player': '书'
        })

        # 快捷网址
        for url_info in QUICK_URLS:
            config = json.dumps({
                'actionId': 'OPEN_URL',
                'type': 'browser',
                'title': url_info['name'],
                'url': url_info['url']
            }, ensure_ascii=False)
            items.append({
                'vod_id': config,
                'vod_name': url_info['name'],
                'vod_pic': f"https://picsum.photos/200/300?random={random.randint(1, 999)}",
                'vod_remarks': '点击打开',
                'vod_tag': 'action',
                'style': {'type': 'grid', 'ratio': 0.75}
            })

        return {'list': items, 'page': 1, 'pagecount': 1, 'limit': len(items), 'total': len(items)}

    # ==================== detailContent ====================
    def detailContent(self, ids):
        id_val = ids[0]

        if id_val.startswith("short_video_"):
            encoded_url = id_val[len("short_video_"):]
            return self._short_video_detail(encoded_url)

        try:
            radio_id = int(id_val)
            if radio_id > 100:
                return self._radio_detail_content(str(radio_id))
        except:
            pass

        if id_val.startswith("radio_play_"):
            radio_id = id_val[len("radio_play_"):]
            return self._radio_detail_content(radio_id)

        if id_val.startswith("gallery_"):
            parts = id_val.split('_', 2)
            if len(parts) >= 3:
                return self._gallery_detail(parts[1], parts[2])

        if id_val.startswith("live://"):
            source_id = self.b64u_decode(id_val[len("live://"):])
            return self._live_source_detail(source_id)

        # 处理动作（浏览器快捷网址）
        if id_val.startswith('{') and '"actionId"' in id_val:
            try:
                action_config = json.loads(id_val)
                if action_config.get('actionId') == '单项输入':
                    return {'list': []}
            except:
                pass

        return {'list': []}

    # ==================== playerContent ====================
    def playerContent(self, flag, id, vipFlags):
        if '|UAINFO|' in id:
            parts = id.split('|UAINFO|')
            real_url = parts[0]
            ua_info_json = parts[1]
            try:
                ua_info = json.loads(self.b64u_decode(ua_info_json))
                custom_ua = ua_info.get('ua', '')
                custom_referer = ua_info.get('referer', '')
                headers = {
                    "User-Agent": custom_ua if custom_ua else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "*/*",
                    "Connection": "keep-alive"
                }
                if custom_referer:
                    headers["Referer"] = custom_referer
                return {
                    "parse": 0,
                    "playUrl": "",
                    "url": real_url,
                    "header": headers
                }
            except Exception:
                id = id.split('|UAINFO|')[0]

        if flag == '蜻蜓FM':
            try:
                raw = self.d64(id).split("@@@@")[-1]
                url = raw.split("|||")[0] if "|||" in raw else raw
                url = url.replace(r"\/", "/")
                return {
                    "parse": 0,
                    "playUrl": "",
                    "url": url,
                    "header": {
                        "User-Agent": self.headers["User-Agent"],
                        "Referer": "http://www.qingting.fm/",
                        "Accept": "*/*"
                    },
                    "vod_player": "听"
                }
            except:
                return {"parse": 0, "playUrl": "", "url": "", "header": self.headers}

        if flag == '短视频播放':
            return self._handle_short_video_play(id)

        url = id
        if '$' in url:
            parts = url.split('$', 1)
            if len(parts) == 2:
                url = parts[1]

        headers = self._build_headers(flag, url)
        return {"parse": 0, "playUrl": "", "url": url, "header": headers}

    def _build_headers(self, flag, url):
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Accept": "*/*"}
        if 'rihou.cc' in domain:
            headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Referer": "https://rihou.cc:555/"})
        elif 'miguvideo.com' in domain:
            headers.update({"User-Agent": "com.android.chrome/3.7.0 (Linux;Android 15)", "Referer": "https://www.miguvideo.com/"})
        elif 'gongdian.top' in domain:
            headers.update({"Referer": "https://gongdian.top/"})
        elif domain:
            headers["Referer"] = f"https://{domain}/"
        return headers

    def searchContent(self, key, quick, pg="1"):
        return {'list': [], 'page': 1, 'pagecount': 1}

    def localProxy(self, param):
        url = param.get("url", "")
        if not url:
            return None
        if param.get("type") == "img":
            try:
                response = self.session.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "http://www.qingting.fm/"
                }, timeout=10)
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', 'image/jpeg')
                    return [200, content_type, response.content, {}]
            except:
                pass
            return [404, "text/plain", b"Error", {}]
        if url.startswith('http'):
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://www.douyin.com/",
                    "Accept": "video/mp4,video/*;q=0.9,*/*;q=0.8"
                }
                response = self.session.get(url, headers=headers, timeout=15)
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', 'video/mp4')
                    return [200, content_type, response.content, {}]
            except:
                pass
        return None

    def destroy(self):
        try:
            self.preload_executor.shutdown(wait=False)
        except:
            pass

    def action(self, action_str):
        try:
            if isinstance(action_str, str):
                try:
                    obj = json.loads(action_str)
                except:
                    if action_str.startswith(('http://', 'https://')):
                        return {'action': {'actionId': 'OPEN_URL', 'type': 'browser', 'title': action_str[:30], 'url': action_str}}
                    obj = {"action": action_str}
            else:
                obj = action_str
            act = obj.get('action', '') or obj.get('actionId', '')
            if act == '单项输入':
                url = obj.get('url', '') or obj.get('value', '')
                if isinstance(url, dict):
                    url = url.get('text', '')
                if url and url.strip():
                    if not url.startswith(('http://', 'https://')):
                        url = 'https://' + url
                    return {'action': {'actionId': 'OPEN_URL', 'type': 'browser', 'title': url[:30], 'url': url}}
            if act == 'OPEN_URL':
                url = obj.get('url', '')
                if url:
                    return {'action': {'actionId': 'OPEN_URL', 'type': 'browser', 'title': obj.get('title', url[:30]), 'url': url}}
            return None
        except Exception as e:
            return None