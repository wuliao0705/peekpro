# -*- coding: utf-8 -*-
# 黄果短剧 - 完整版（含排行榜三榜 + 吃瓜筛选 + 精选推荐 + 逐集全集抓取）
import sys
import re
import json
import time
import requests
from urllib.parse import urljoin, quote

try:
    sys.path.append('..')
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def getName(self): return "Base"
        def init(self, extend=""): pass
        def homeContent(self, filter): return {"class": [], "filters": {}}
        def categoryContent(self, tid, pg, filter, extend): return {"list": [], "page": 1, "pagecount": 1, "limit": 20, "total": 0}
        def detailContent(self, ids): return {"list": []}
        def playerContent(self, flag, id, vipFlags=None): return {"parse": 0, "url": "", "header": {}}
        def searchContent(self, key, quick, pg="1"): return {"list": [], "page": 1}
        def isVideoFormat(self, url): return False
        def manualVideoCheck(self): return False
        def localProxy(self, param): return [404, "text/plain", b""]

class Spider(BaseSpider):
    def __init__(self):
        super().__init__()
        self.host = "https://huangguoai.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": self.host + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        self.base_cates = [
            {"id": "ai-duanju", "name": "AI成人短剧"},
            {"id": "ai-manju", "name": "AI成人漫剧"},
            {"id": "ai-huanlian", "name": "AI换脸"},
            {"id": "ai-mogai", "name": "AI魔改"},
        ]
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.MAX_PAGES = 100
        self._recommend_cache = None

    def getName(self):
        return "黄果短剧"

    def init(self, extend=""):
        pass

    def fix_url(self, url):
        if not url:
            return ""
        url = url.replace("\\u0026", "&").replace("&amp;", "&")
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.host + url
        return url

    def _fetch_html(self, url):
        try:
            print(f"[黄果] 请求: {url}")
            resp = self.session.get(url, timeout=20)
            if resp.status_code == 200:
                return resp.text
            return None
        except Exception as e:
            print(f"[黄果] 请求失败: {e}")
            return None

    def _extract_json(self, html):
        if not html:
            return None
        m = re.search(r'<script\s+id="videoInitialData"\s+type="application/json">(.*?)</script>', html, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except:
                pass
        return None

    def extract_cards(self, html):
        result = []
        seen = set()
        matches = list(re.finditer(r'data-track-id="(\d+)"', html))
        for i, m in enumerate(matches):
            try:
                start = m.start()
                end = matches[i + 1].start() if i + 1 < len(matches) else min(start + 3000, len(html))
                chunk = html[start:end]
                vod_id = m.group(1)
                if vod_id in seen:
                    continue
                link = re.search(r'href="(/detail/%s/)"' % re.escape(vod_id), chunk)
                if not link:
                    link = re.search(r'href="(/detail/%s)"' % re.escape(vod_id), chunk)
                if not link:
                    continue
                seen.add(vod_id)
                title = re.search(r'data-track-title="([^"]*)"', chunk)
                vod_name = title.group(1) if title else ""
                pic = re.search(r'data-src="(https?://[^"]*)"', chunk)
                if not pic:
                    pic = re.search(r'<img[^>]*src="(https?://[^"]*)"', chunk)
                vod_pic = pic.group(1) if pic else ""
                ep = re.search(r'hg-drama-card__episode[^>]*>([^<]*)', chunk)
                vod_remarks = ep.group(1).strip() if ep else ""
                if not vod_remarks:
                    score = re.search(r'hg-drama-card__score[^>]*>([^<]*)', chunk)
                    vod_remarks = score.group(1).strip() if score else ""
                if vod_name and vod_id:
                    result.append({
                        "vod_id": vod_id,
                        "vod_name": vod_name,
                        "vod_pic": vod_pic,
                        "vod_remarks": vod_remarks
                    })
            except:
                continue
        return result

    def extract_rank_items(self, html):
        """从排行榜页面提取视频"""
        result = []
        items = re.findall(r'<div class="hg-rank-item"[^>]*data-track-id="(\d+)"[^>]*data-track-title="([^"]+)"[^>]*>.*?<img[^>]+data-src="([^"]+)"[^>]*>', html, re.DOTALL)
        if not items:
            items = re.findall(r'data-track-id="(\d+)".*?data-track-title="([^"]+)".*?<img[^>]+data-src="([^"]+)"', html, re.DOTALL)
        for vid, title, pic in items:
            pic = self.fix_url(pic)
            result.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": "排行榜"
            })
        return result

    def extract_posts(self, html):
        result = []
        if not html:
            return result
        pattern = r'<a class="hg-post-card"[^>]*href="(/archives/(\d+)/)"[^>]*>.*?<img[^>]+(?:data-src|src)="([^"]+)"[^>]*>.*?<h3>(.*?)</h3>'
        items = re.findall(pattern, html, re.DOTALL)
        for href, post_id, pic, title in items:
            pic = self.fix_url(pic)
            result.append({
                "vod_id": f"archives_{post_id}",
                "vod_name": title.strip(),
                "vod_pic": pic,
                "vod_remarks": "吃瓜"
            })
        return result

    # ================== 首页 ==================
    def homeContent(self, filter):
        result = {"class": [], "filters": {}}
        
        # 1. 精选推荐
        result["class"].append({"type_id": "recommend", "type_name": "⭐精选推荐"})
        
        # 2. 四个主要分类 + 筛选器
        for base in self.base_cates:
            result["class"].append({"type_id": base["id"], "type_name": base["name"]})
            result["filters"][base["id"]] = [
                {
                    "key": "sort",
                    "name": "排序",
                    "value": [
                        {"n": "最新更新", "v": "latest"},
                        {"n": "当前热播", "v": "hot"},
                        {"n": "独家原创", "v": "original"},
                        {"n": "随机推荐", "v": "random"},
                    ]
                }
            ]
        
        # 3. 排行榜（父分类，带三个分榜筛选）
        result["class"].append({"type_id": "ranks", "type_name": "📊排行榜"})
        result["filters"]["ranks"] = [
            {
                "key": "rank_type",
                "name": "榜单",
                "value": [
                    {"n": "热播榜", "v": "hot"},
                    {"n": "推荐榜", "v": "recommend"},
                    {"n": "潜力榜", "v": "potential"},
                ]
            }
        ]
        
        # 4. 黄果吃瓜 + 筛选器
        result["class"].append({"type_id": "chigua", "type_name": "🍉黄果吃瓜"})
        result["filters"]["chigua"] = [
            {
                "key": "cate",
                "name": "分类",
                "value": [
                    {"n": "全部", "v": "all"},
                    {"n": "热门吃瓜", "v": "remen"},
                    {"n": "AI原创", "v": "yuanchuang"},
                ]
            }
        ]
        
        return result

    def homeVideoContent(self):
        if self._recommend_cache is not None:
            return {"list": self._recommend_cache}
        try:
            html = self._fetch_html(self.host)
            if not html:
                return {"list": []}
            cards = self.extract_cards(html)
            seen = set()
            unique = []
            for c in cards:
                if c["vod_id"] not in seen:
                    seen.add(c["vod_id"])
                    unique.append(c)
            self._recommend_cache = unique[:20]
            return {"list": unique[:20]}
        except Exception as e:
            print(f"[黄果] homeVideoContent 异常: {e}")
            return {"list": []}

    # ================== 分类页 ==================
    def categoryContent(self, tid, pg, filter, extend):
        # 精选推荐
        if tid == "recommend":
            return self.homeVideoContent()

        # 排行榜（三榜切换）
        if tid == "ranks":
            rank_type = "hot"
            if extend and isinstance(extend, dict):
                rank_type = extend.get("rank_type", "hot")
            return self._category_ranks(rank_type)

        # 黄果吃瓜
        if tid == "chigua":
            cate = "all"
            if extend and isinstance(extend, dict):
                cate = extend.get("cate", "all")
            return self._category_chigua_all(cate)

        # 主要分类
        sort = "latest"
        is_original = 0
        if extend and isinstance(extend, dict):
            sort = extend.get("sort", "latest")
            if sort == "original":
                sort = "hot"
                is_original = 1
            elif sort == "random":
                return self._category_random(tid)

        return self._category_api_all(tid, sort, is_original)

    # ====== 排行榜（三榜通用，循环翻页） ======
    def _category_ranks(self, rank_type="hot"):
        result = {"list": [], "page": 1, "pagecount": 1, "limit": 10000, "total": 0}
        all_videos = []
        seen = set()
        page = 1

        # 排行榜URL映射
        rank_urls = {
            "hot": "/ranks/hot/",
            "recommend": "/ranks/recommend/",
            "potential": "/ranks/potential/",
        }
        base_path = rank_urls.get(rank_type, "/ranks/hot/")
        rank_names = {"hot": "热播榜", "recommend": "推荐榜", "potential": "潜力榜"}
        rank_name = rank_names.get(rank_type, "排行榜")

        print(f"[黄果] 排行榜: {rank_name}")

        while page <= self.MAX_PAGES:
            try:
                if page == 1:
                    url = self.host + base_path
                else:
                    url = self.host + base_path.rstrip("/") + f"?page={page}"
                html = self._fetch_html(url)
                if not html:
                    break
                items = self.extract_rank_items(html)
                if not items:
                    break
                for item in items:
                    if item["vod_id"] in seen:
                        continue
                    seen.add(item["vod_id"])
                    all_videos.append(item)
                # 检查下一页
                next_match = re.search(r'<a[^>]+href="[^"]*\?page=(\d+)"[^>]*>.*?下一页', html)
                if next_match:
                    page += 1
                else:
                    break
                time.sleep(0.2)
            except Exception as e:
                print(f"[黄果] 排行榜异常: {e}")
                break

        result["list"] = all_videos
        result["total"] = len(all_videos)
        print(f"[黄果] {rank_name} 共获取 {len(all_videos)} 个视频")
        return result

    # ====== 吃瓜（循环翻页） ======
    def _category_chigua_all(self, cate="all"):
        result = {"list": [], "page": 1, "pagecount": 1, "limit": 10000, "total": 0}
        all_posts = []
        seen = set()
        page = 1

        if cate == "all":
            base_path = "/chigua/"
        elif cate == "remen":
            base_path = "/chigua/remen/"
        elif cate == "yuanchuang":
            base_path = "/chigua/yuanchuang/"
        else:
            base_path = "/chigua/"

        while page <= self.MAX_PAGES:
            try:
                if page == 1:
                    url = self.host + base_path
                else:
                    base_clean = base_path.rstrip("/")
                    url = self.host + base_clean + f"/page/{page}/"
                html = self._fetch_html(url)
                if not html:
                    break
                items = self.extract_posts(html)
                if not items:
                    break
                for item in items:
                    if item["vod_id"] in seen:
                        continue
                    seen.add(item["vod_id"])
                    all_posts.append(item)
                pages_match = re.search(r'data-pages="(\d+)"', html)
                if pages_match:
                    total_pages = int(pages_match.group(1))
                    if page >= total_pages:
                        break
                else:
                    next_match = re.search(r'<a[^>]+href="[^"]*page/(\d+)/"[^>]*>.*?下一页', html)
                    if next_match:
                        page += 1
                        continue
                    elif len(items) < 12:
                        break
                page += 1
                time.sleep(0.3)
            except Exception as e:
                print(f"[黄果] 吃瓜异常: {e}")
                break

        result["list"] = all_posts
        result["total"] = len(all_posts)
        print(f"[黄果] 吃瓜({cate}) 共获取 {len(all_posts)} 个帖子")
        return result

    # ====== 随机推荐 ======
    def _category_random(self, base_id):
        result = {"list": [], "page": 1, "pagecount": 1, "limit": 20, "total": 0}
        try:
            url = f"{self.host}/api/videos/category/{base_id}"
            params = {"sort": "random", "size": 20}
            resp = self.session.get(url, params=params, timeout=15)
            if resp.status_code != 200:
                return result
            data = resp.json()
            items = data.get("data", {}).get("items", []) or data.get("list", [])
            for item in items:
                vid = str(item.get("id", ""))
                if not vid:
                    continue
                pic = item.get("cover", "")
                if pic and not pic.startswith("http"):
                    pic = self.fix_url(pic)
                remarks = ""
                if item.get("is_finished"):
                    remarks = f"全{item.get('total_episodes', 0)}集"
                else:
                    ep = item.get("episode_count", 0)
                    if ep:
                        remarks = f"更新至{ep}集"
                result["list"].append({
                    "vod_id": vid,
                    "vod_name": item.get("title", "未知"),
                    "vod_pic": pic,
                    "vod_remarks": remarks,
                })
            result["total"] = len(result["list"])
        except Exception as e:
            print(f"[黄果] 随机推荐异常: {e}")
        return result

    # ====== API分类 ======
    def _category_api_all(self, base_id, sort="latest", is_original=0):
        result = {"list": [], "page": 1, "pagecount": 1, "limit": 10000, "total": 0}
        all_videos = []
        seen = set()
        page = 1
        per_page = 20

        while page <= self.MAX_PAGES:
            try:
                url = f"{self.host}/api/videos/category/{base_id}"
                params = {"page": page, "size": per_page, "sort": sort}
                if is_original:
                    params["is_original"] = 1
                resp = self.session.get(url, params=params, timeout=15)
                if resp.status_code != 200:
                    break
                data = resp.json()
                items = data.get("data", {}).get("items", []) or data.get("list", [])
                if not items:
                    break
                for item in items:
                    vid = str(item.get("id", ""))
                    if not vid or vid in seen:
                        continue
                    seen.add(vid)
                    pic = item.get("cover", "")
                    if pic and not pic.startswith("http"):
                        pic = self.fix_url(pic)
                    remarks = ""
                    if item.get("is_finished"):
                        remarks = f"全{item.get('total_episodes', 0)}集"
                    else:
                        ep = item.get("episode_count", 0)
                        if ep:
                            remarks = f"更新至{ep}集"
                    all_videos.append({
                        "vod_id": vid,
                        "vod_name": item.get("title", "未知"),
                        "vod_pic": pic,
                        "vod_remarks": remarks,
                    })
                total = data.get("data", {}).get("total", 0)
                if total > 0:
                    total_pages = (total + per_page - 1) // per_page
                    if page >= total_pages:
                        break
                elif len(items) < per_page:
                    break
                page += 1
                time.sleep(0.2)
            except Exception as e:
                print(f"[黄果] API请求异常: {e}")
                break

        result["list"] = all_videos
        result["total"] = len(all_videos)
        return result

    # ================== 详情页（逐集抓取全部集数） ==================
    def detailContent(self, ids):
        result = {"list": []}
        vid = ids[0] if ids else ""
        if not vid:
            return result

        if vid.startswith("archives_"):
            return self._detail_archives(vid.replace("archives_", ""))
        else:
            return self._detail_video(vid)

    def _detail_video(self, vid):
        result = {"list": []}
        first_url = f"{self.host}/video/{vid}/"
        first_html = self._fetch_html(first_url)
        if not first_html:
            return result
        first_data = self._extract_json(first_html)
        if not first_data:
            return result

        title = first_data.get("title", "未知")
        cover = first_data.get("coverSrc") or first_data.get("posterSrc") or ""
        if cover and not cover.startswith("http"):
            cover = self.fix_url(cover)
        desc = first_data.get("description", "")

        ep_numbers = []
        for m in re.finditer(r'<a[^>]+class="[^"]*hg-play__ep-item[^"]*"[^>]*>(\d+)</a>', first_html):
            ep_numbers.append(int(m.group(1)))
        if not ep_numbers:
            for href in re.findall(r'href="([^"]+)"', first_html):
                m = re.search(r'/ep-(\d+)/', href)
                if m:
                    ep_numbers.append(int(m.group(1)))
            if ep_numbers and 1 not in ep_numbers:
                ep_numbers.append(1)
        if not ep_numbers:
            ep_srcs = first_data.get("epPlaySrcs", {})
            if ep_srcs:
                ep_numbers = sorted([int(k) for k in ep_srcs.keys()])
            else:
                ep_numbers = [1]

        max_ep = max(ep_numbers) if ep_numbers else 1
        ep_srcs = {}
        for ep_num in range(1, max_ep + 1):
            if ep_num == 1:
                ep_url = first_url
            else:
                ep_url = f"{self.host}/video/{vid}/ep-{ep_num}/"
            html = self._fetch_html(ep_url)
            if not html:
                continue
            data = self._extract_json(html)
            if not data:
                continue
            src = data.get("videoSrc", "")
            if src:
                ep_srcs[str(ep_num)] = src
            time.sleep(0.3)

        if ep_srcs:
            play_segments = []
            for ep_num in sorted(ep_srcs.keys(), key=lambda x: int(x)):
                url = ep_srcs[ep_num]
                if url:
                    safe_url = quote(url, safe=':/?&=')
                    play_segments.append(f"{int(ep_num):02d}${safe_url}")
            play_url = "#".join(play_segments)
        else:
            fallback = first_data.get("videoSrc", "")
            if fallback:
                play_url = f"01${quote(fallback, safe=':/?&=')}"
            else:
                play_url = f"01${vid}"

        result["list"].append({
            "vod_id": vid,
            "vod_name": title,
            "vod_pic": cover,
            "vod_content": desc,
            "vod_play_from": "黄果短剧",
            "vod_play_url": play_url,
        })
        print(f"[黄果] 视频 {vid} 共获取 {len(ep_srcs)} 集")
        return result

    def _detail_archives(self, post_id):
        result = {"list": []}
        try:
            url = f"{self.host}/archives/{post_id}/"
            html = self._fetch_html(url)
            if not html:
                return result
            title_match = re.search(r'<title>(.*?)</title>', html)
            title = title_match.group(1).strip() if title_match else f"吃瓜{post_id}"
            img_match = re.search(r'<img[^>]+data-src="([^"]+)"', html)
            if not img_match:
                img_match = re.search(r'<img[^>]+src="([^"]+)"', html)
            pic = img_match.group(1) if img_match else ""
            if pic and not pic.startswith("http"):
                pic = self.fix_url(pic)
            video_url = ""
            m = re.search(r'<video[^>]+src="([^"]+)"', html)
            if m:
                video_url = m.group(1)
            if not video_url:
                m = re.search(r'<iframe[^>]+src="([^"]+)"', html)
                if m:
                    video_url = m.group(1)
            if not video_url:
                m = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html)
                if m:
                    video_url = m.group(1)
            if video_url:
                play_url = f"01${quote(video_url, safe=':/?&=')}"
            else:
                play_url = f"01${post_id}"
            result["list"].append({
                "vod_id": f"archives_{post_id}",
                "vod_name": title,
                "vod_pic": pic,
                "vod_content": "吃瓜内容",
                "vod_play_from": "黄果短剧",
                "vod_play_url": play_url,
            })
        except Exception as e:
            print(f"[黄果] _detail_archives 异常: {e}")
        return result

    # ================== 播放 ==================
    def playerContent(self, flag, id, vipFlags=None):
        result = {"parse": 0, "playUrl": "", "url": "", "header": ""}
        if not id:
            return result
        if id.startswith("http"):
            result["url"] = id
            result["header"] = json.dumps({"User-Agent": self.headers["User-Agent"], "Referer": self.host})
            return result

        vid = str(id).strip()
        if vid.startswith("archives_"):
            result["url"] = id
            return result

        first_url = f"{self.host}/video/{vid}/"
        html = self._fetch_html(first_url)
        if html:
            data = self._extract_json(html)
            if data:
                src = data.get("videoSrc", "")
                if src:
                    result["url"] = src
                    result["header"] = json.dumps({"User-Agent": self.headers["User-Agent"], "Referer": self.host})
                    return result
        result["url"] = id
        return result

    # ================== 搜索 ==================
    def searchContent(self, key, quick, pg="1"):
        result = {"list": [], "page": int(pg), "pagecount": 1, "limit": 20, "total": 0}
        try:
            page = int(pg) if pg else 1
            url = f"{self.host}/search/?keyword={quote(key)}"
            if page > 1:
                url += f"&page={page}"
            html = self._fetch_html(url)
            if not html:
                return result
            result["list"] = self.extract_cards(html)
            total = re.search(r'data-track-search-total="(\d+)"', html)
            if total:
                result["total"] = int(total.group(1))
            result["page"] = page
        except Exception as e:
            print(f"[黄果] searchContent 异常: {e}")
        return result

    # ================== 其他 ==================
    def isVideoFormat(self, url):
        if not url:
            return False
        exts = ['.m3u8', '.mp4', '.avi', '.flv', '.mkv', '.ts']
        return any(url.lower().endswith(ext) for ext in exts) or 'm3u8' in url.lower()

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return {"url": "", "header": ""}

Spider = Spider