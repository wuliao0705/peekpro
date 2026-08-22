# -*- coding: utf-8 -*-
# 一抖阁 - TVBox 视频爬虫（含三级分类：父级 -> 子级 -> 排序）
# 目标: https://yidouge.com
# 增强：首页支持多卡片提取（轮播、更新、推荐、热门等）

import sys
import re
import json
import urllib.parse
from base.spider import Spider
from bs4 import BeautifulSoup
import requests


class Spider(Spider):
    def getName(self):
        return "一抖阁"

    def init(self, extend=""):
        self.host = "https://yidouge.com"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.host + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cookie": "gv_age_verified=1",
        })

        # ===== 分类树（父级 → 子级列表） =====
        self.category_tree = {
            "ai_short": {
                "name": "AI短剧",
                "slug": "v2/ai%e7%9f%ad%e5%89%a7",
                "children": [
                    {"name": "伦理绿帽NTR", "slug": "v2/%e7%bb%bf%e5%b8%bdntr"},
                    {"name": "动漫短剧", "slug": "v2/%e5%8a%a8%e6%bc%ab%e7%9f%ad%e5%89%a7"},
                    {"name": "古装", "slug": "v2/%e5%8f%a4%e8%a3%85"},
                    {"name": "奇幻", "slug": "v2/%e5%a5%87%e5%b9%bb"},
                    {"name": "小说 影视剧同人", "slug": "v2/%e5%b0%8f%e8%af%b4%e5%90%8c%e4%ba%ba"},
                    {"name": "微恐", "slug": "v2/%e5%be%ae%e6%81%90"},
                    {"name": "现代", "slug": "v2/%e9%83%bd%e5%b8%82"},
                    {"name": "短篇", "slug": "v2/%e7%9f%ad%e7%af%87"},
                    {"name": "穿越", "slug": "v2/%e7%a9%bf%e8%b6%8a"},
                    {"name": "重生", "slug": "v2/%e9%87%8d%e7%94%9f"},
                ]
            },
            "pmv": {
                "name": "PMV",
                "slug": "v2/pmv",
                "children": [
                    {"name": "AI风格PMV", "slug": "v2/ai%e9%a3%8e%e6%a0%bcpmv"},
                    {"name": "AV剧情剪辑", "slug": "v2/avjuqing"},
                    {"name": "B站舞蹈", "slug": "v2/b%e7%ab%99%e8%88%9e%e8%b9%88"},
                    {"name": "KPOP深度换脸", "slug": "v2/dfpmv"},
                    {"name": "MMD动画", "slug": "v2/mmd%e5%8a%a8%e7%94%bb"},
                    {"name": "寸止挑战", "slug": "v2/cunzhi"},
                    {"name": "抖音混剪", "slug": "v2/dyhunjian"},
                    {"name": "拼接跳转", "slug": "v2/%e6%8b%bc%e6%8e%a5%e8%b7%b3%e8%bd%ac"},
                    {"name": "欧美PMV", "slug": "v2/oumeipmv"},
                    {"name": "舞蹈", "slug": "v2/wudaopmv"},
                ]
            },
            "magic_remake": {
                "name": "魔改影视剧",
                "slug": "v2/%e9%ad%94%e6%94%b9%e5%bd%b1%e8%a7%86%e5%89%a7",
                "children": [
                    {"name": "魔改电影电视剧", "slug": "v2/%e9%ad%94%e6%94%b9%e7%94%b5%e5%bd%b1%e7%94%b5%e8%a7%86%e5%89%a7"},
                    {"name": "魔改综艺", "slug": "v2/%e9%ad%94%e6%94%b9%e7%bb%bc%e8%89%ba"},
                ]
            },
            "celebrity_edit": {
                "name": "名人二创",
                "slug": "v2/%e6%98%8e%e6%98%9f%e4%ba%8c%e5%88%9b",
                "children": [
                    {"name": "明星换脸", "slug": "v2/%e6%98%8e%e6%98%9f%e6%8d%a2%e8%84%b8"},
                    {"name": "明星短剧 去衣", "slug": "v2/%e6%98%8e%e6%98%9f%e5%8e%bb%e8%a1%a3"},
                    {"name": "网红去衣", "slug": "v2/%e7%bd%91%e7%ba%a2%e5%8e%bb%e8%a1%a3"},
                ]
            },
            "vam": {
                "name": "VAM动画",
                "slug": "v2/vam%e5%8a%a8%e7%94%bb-%e6%bc%ab%e7%94%bb",
                "children": []
            },
            "domestic": {
                "name": "国产",
                "slug": "v1/%e5%9b%bd%e4%ba%a7",
                "children": [
                    {"name": "91大神", "slug": "v1/91%e5%a4%a7%e7%a5%9e"},
                    {"name": "国产订阅博主", "slug": "v1/%e5%9b%bd%e4%ba%a7%e8%ae%a2%e9%98%85%e5%8d%9a%e4%b8%bb"},
                    {"name": "泄露门事件", "slug": "v1/%e6%b3%84%e9%9c%b2%e9%97%a8%e4%ba%8b%e4%bb%b6"},
                    {"name": "绿帽NTR", "slug": "v1/%e7%bb%bf%e5%b8%bdntr"},
                    {"name": "萝莉福利姬", "slug": "v1/%e8%90%9d%e8%8e%89%e7%a6%8f%e5%88%a9%e5%a7%ac-%e5%9b%bd%e4%ba%a7"},
                    {"name": "调教SM", "slug": "v1/%e8%b0%83%e6%95%99sm"},
                ]
            },
            "ri_fan": {
                "name": "里番",
                "slug": "v1/%e9%87%8c%e7%95%aa",
                "children": []
            },
        }

    def _fix_url(self, url):
        if not url:
            return ""
        if url.startswith("http"):
            return url
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.host + url
        return self.host + "/" + url

    def _fetch(self, url, timeout=15):
        try:
            resp = self.session.get(url, timeout=timeout)
            resp.encoding = "utf-8"
            return resp.text
        except Exception as e:
            print(f"[Fetch Error] {url} -> {e}")
            return ""

    # ===== 生成分类列表与筛选器（含子分类 + 排序） =====
    def homeContent(self, filter=False):
        classes = []
        filters = {}
        for key, cat in self.category_tree.items():
            slug = cat["slug"]
            classes.append({"type_id": slug, "type_name": cat["name"]})

            # 子分类筛选
            sub_options = [{"n": "全部", "v": ""}]
            for child in cat.get("children", []):
                sub_options.append({"n": child["name"], "v": child["slug"]})

            # 排序筛选（最近更新/播放最多）
            sort_options = [
                {"n": "最近更新", "v": ""},
                {"n": "播放最多", "v": "views"},
            ]

            filters[slug] = [
                {"key": "subcat", "name": "子分类", "value": sub_options},
                {"key": "video_sort", "name": "排序", "value": sort_options},
            ]
        return {"class": classes, "filters": filters}

    # ========== 新增：首页专用提取（多种卡片） ==========
    def _extract_home_videos(self, html):
        """从首页提取所有视频卡片（轮播、更新、推荐、热门等）"""
        soup = BeautifulSoup(html, "html.parser")
        videos = []
        seen = set()

        # 1. 轮播图 .cnh-hero-slide
        for item in soup.select(".cnh-hero-slide"):
            a_tag = item.find("a", href=True)
            if not a_tag:
                continue
            href = a_tag.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)
            id_match = re.search(r"/video/([^/]+)/", href)
            if not id_match:
                continue
            vod_id = id_match.group(1)
            title_tag = item.select_one(".cnh-hero-title")
            title = title_tag.get_text(strip=True) if title_tag else ""
            pic = ""
            bg_tag = item.select_one(".cnh-hero-bg")
            if bg_tag:
                style = bg_tag.get("style", "")
                m = re.search(r"url\('([^']+)'\)", style)
                if m:
                    pic = self._fix_url(m.group(1))
            videos.append({"vod_id": vod_id, "vod_name": title, "vod_pic": pic, "vod_remarks": "推荐"})

        # 2. 更新卡片 .update-card-item
        for item in soup.select(".update-card-item"):
            a_tag = item.find("a", href=True)
            if not a_tag:
                continue
            href = a_tag.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)
            id_match = re.search(r"/video/([^/]+)/", href)
            if not id_match:
                continue
            vod_id = id_match.group(1)
            title_tag = item.select_one(".title")
            title = title_tag.get_text(strip=True) if title_tag else ""
            img_tag = item.select_one("img")
            pic = ""
            if img_tag:
                pic = img_tag.get("src", "") or img_tag.get("data-src", "")
                pic = self._fix_url(pic)
            remark = ""
            desc_tag = item.select_one(".desc a")
            if desc_tag:
                remark = desc_tag.get_text(strip=True)
            videos.append({"vod_id": vod_id, "vod_name": title, "vod_pic": pic, "vod_remarks": remark})

        # 3. 推荐卡片 .recommend-card-item
        for item in soup.select(".recommend-card-item"):
            a_tag = item.find("a", href=True)
            if not a_tag:
                continue
            href = a_tag.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)
            id_match = re.search(r"/video/([^/]+)/", href)
            if not id_match:
                continue
            vod_id = id_match.group(1)
            title_tag = item.select_one(".title")
            title = title_tag.get_text(strip=True) if title_tag else ""
            img_tag = item.select_one("img")
            pic = ""
            if img_tag:
                pic = img_tag.get("src", "") or img_tag.get("data-src", "")
                pic = self._fix_url(pic)
            tags = item.select(".tag")
            remarks = " ".join([t.get_text(strip=True) for t in tags])
            videos.append({"vod_id": vod_id, "vod_name": title, "vod_pic": pic, "vod_remarks": remarks})

        # 4. 首页热门 .home-hot-item
        for item in soup.select(".home-hot-item"):
            a_tag = item.find("a", href=True)
            if not a_tag:
                continue
            href = a_tag.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)
            id_match = re.search(r"/video/([^/]+)/", href)
            if not id_match:
                continue
            vod_id = id_match.group(1)
            title_tag = item.select_one(".title")
            title = title_tag.get_text(strip=True) if title_tag else ""
            img_tag = item.select_one("img")
            pic = ""
            if img_tag:
                pic = img_tag.get("src", "") or img_tag.get("data-src", "")
                pic = self._fix_url(pic)
            desc_tag = item.select_one(".desc")
            remarks = desc_tag.get_text(strip=True) if desc_tag else ""
            videos.append({"vod_id": vod_id, "vod_name": title, "vod_pic": pic, "vod_remarks": remarks})

        # 5. 其他 .video-card（以防遗漏）
        for item in soup.select(".video-card"):
            a_tag = item.find("a", href=True)
            if not a_tag:
                continue
            href = a_tag.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)
            id_match = re.search(r"/video/([^/]+)/", href)
            if not id_match:
                continue
            vod_id = id_match.group(1)
            title_tag = item.select_one(".video-card__title")
            title = title_tag.get_text(strip=True) if title_tag else ""
            img_tag = item.select_one(".video-card__media img")
            pic = ""
            if img_tag:
                pic = img_tag.get("src", "") or img_tag.get("data-src", "")
                pic = self._fix_url(pic)
            duration = item.select_one(".video-card__duration")
            remarks = duration.get_text(strip=True) if duration else ""
            videos.append({"vod_id": vod_id, "vod_name": title, "vod_pic": pic, "vod_remarks": remarks})

        # 去重
        unique = []
        seen_ids = set()
        for v in videos:
            if v["vod_id"] not in seen_ids:
                seen_ids.add(v["vod_id"])
                unique.append(v)
        return unique

    # ===== 首页推荐 =====
    def homeVideoContent(self):
        try:
            html = self._fetch(self.host)
            if not html:
                return {"list": []}
            videos = self._extract_home_videos(html)
            return {"list": videos[:50]}  # 返回前50个
        except Exception as e:
            print(f"首页异常: {e}")
            return {"list": []}

    # ===== 构造分类页URL（分页 + 排序） =====
    def _build_category_url(self, slug, pg, sort=""):
        if pg <= 1:
            base = f"{self.host}/{slug}/"
        else:
            base = f"{self.host}/{slug}/page/{pg}/"
        if sort:
            return f"{base}?video_sort={sort}"
        return base

    # ===== 分类列表：支持子分类 + 排序 + 分页修复 =====
    def categoryContent(self, tid, pg, filter=False, extend=None):
        pg = int(pg) if pg else 1
        extend = extend or {}

        subcat = extend.get("subcat", "")
        target_slug = subcat if subcat else tid
        sort = extend.get("video_sort", "")

        url = self._build_category_url(target_slug, pg, sort)
        html = self._fetch(url)
        if not html:
            return {"list": [], "page": pg, "pagecount": 1, "limit": 20, "total": 0}

        videos = self._extract_category_videos(html)
        pagecount = self._extract_pagecount(html)

        # 如果 pagecount 仍为1，但视频数量达到每页上限，则假设还有更多页
        if pagecount <= 1 and len(videos) >= 20:
            pagecount = pg + 1
        # 确保 pagecount 至少为当前页
        if pagecount < pg:
            pagecount = pg

        limit = 20
        total = pagecount * limit
        # 如果当前页视频少于 limit 且为最后一页，则修正 total
        if len(videos) < limit and pg == pagecount:
            total = (pg - 1) * limit + len(videos)

        return {
            "list": videos,
            "page": pg,
            "pagecount": pagecount,
            "limit": limit,
            "total": total
        }

    # ===== 提取总页数（改进版） =====
    def _extract_pagecount(self, html):
        """提取总页数，返回整数页码"""
        soup = BeautifulSoup(html, "html.parser")
        page_nums = []
        # 查找所有页码链接（包括数字和'...'但只取数字）
        for a in soup.select(".page-numbers"):
            href = a.get("href", "")
            m = re.search(r"/page/(\d+)/", href)
            if m:
                try:
                    num = int(m.group(1))
                    page_nums.append(num)
                except:
                    pass
        if page_nums:
            return max(page_nums)
        # 如果没找到，尝试从"尾页"或"下一页"的链接取数字
        last_link = soup.select_one("a.video-pagination__edge[href*='/page/']:last-of-type")
        if last_link:
            m = re.search(r"/page/(\d+)/", last_link.get("href", ""))
            if m:
                return int(m.group(1))
        # 如果页面中有跳转表单，从data-total属性获取
        jump_form = soup.select_one("form.video-pagination__jump")
        if jump_form:
            total = jump_form.get("data-total")
            if total:
                try:
                    return int(total)
                except:
                    pass
        return 1

    # ===== 提取分类页视频列表（保留原逻辑） =====
    def _extract_category_videos(self, html):
        soup = BeautifulSoup(html, "html.parser")
        videos = []
        seen = set()

        for item in soup.select(".video-card, .video-grid .video-card"):
            a_tag = item.find("a", href=True)
            if not a_tag:
                continue
            href = a_tag.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)

            if not re.search(r"/video/[^/]+/", href):
                continue

            id_match = re.search(r"/video/([^/]+)/", href)
            vod_id = id_match.group(1) if id_match else ""

            title_tag = item.select_one(".video-card__title")
            title = title_tag.get_text(strip=True) if title_tag else ""

            img_tag = item.select_one(".video-card__media img")
            pic = ""
            if img_tag:
                pic = img_tag.get("src", "") or img_tag.get("data-src", "")
                pic = self._fix_url(pic)

            remark = ""
            label_tag = item.select_one(".video-card__label")
            if label_tag:
                remark = label_tag.get_text(strip=True)
            if not remark:
                duration_tag = item.select_one(".video-card__duration")
                if duration_tag:
                    remark = duration_tag.get_text(strip=True)

            if vod_id:
                videos.append({
                    "vod_id": vod_id,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": remark
                })

        return videos

    # ===== 首页推荐视频提取（保留旧方法但不再使用） =====
    def _extract_videos_from_home(self, html):
        # 直接调用新方法
        return self._extract_home_videos(html)

    # ===== 详情页（支持合集选集） =====
    def detailContent(self, ids):
        vod_id = ids[0]
        url = f"{self.host}/video/{vod_id}/"
        html = self._fetch(url)

        if not html:
            return {"list": []}

        soup = BeautifulSoup(html, "html.parser")

        title = ""
        title_tag = soup.select_one("h1, .entry-title, .video-title")
        if title_tag:
            title = title_tag.get_text(strip=True)
        if not title:
            title_match = re.search(r"<title>(.*?)</title>", html)
            if title_match:
                title = title_match.group(1).strip()
                title = re.sub(r'\s*[-|]\s*一抖阁.*$', '', title)

        pic = ""
        img_tag = soup.select_one(".video-card__media img, .post-thumbnail img, .featured-image img")
        if img_tag:
            pic = img_tag.get("src", "") or img_tag.get("data-src", "")
            pic = self._fix_url(pic)
        if not pic:
            player_div = soup.select_one("[data-video-player-wrap]")
            if player_div:
                poster = player_div.get("data-video-poster", "")
                if poster:
                    pic = self._fix_url(poster)

        intro = ""
        intro_tag = soup.select_one(".entry-content, .video-description, .content")
        if intro_tag:
            intro = intro_tag.get_text(strip=True)

        # ----- 检测是否为合集页（作者页面或含有剧集列表） -----
        if "/creator/" in url or soup.select_one(".author-playlist__list"):
            # 复用分类提取方法提取剧集（因为 _extract_category_videos 只匹配 video-card，而作者列表是 author-playlist__item，需要单独处理）
            # 这里我们使用 BeautifulSoup 直接提取
            episodes = []
            seen = set()
            for item in soup.select(".author-playlist__item"):
                a_tag = item.find("a", href=True)
                if not a_tag:
                    continue
                href = a_tag.get("href", "")
                if not href or href in seen:
                    continue
                seen.add(href)
                id_match = re.search(r"/video/([^/]+)/", href)
                if not id_match:
                    continue
                vid = id_match.group(1)
                strong = item.select_one("strong")
                title = strong.get_text(strip=True) if strong else a_tag.get_text(strip=True)
                img_tag = item.select_one(".author-playlist__thumb img")
                pic2 = ""
                if img_tag:
                    pic2 = img_tag.get("src", "") or img_tag.get("data-src", "")
                    pic2 = self._fix_url(pic2)
                em = item.select_one("em")
                remark = em.get_text(strip=True) if em else ""
                episodes.append({"vod_id": vid, "vod_name": title, "vod_pic": pic2, "vod_remarks": remark})

            if len(episodes) > 1:
                parts = []
                for ep in episodes:
                    ep_title = ep.get("vod_name") or "第{}集".format(parts.__len__()+1)
                    parts.append(f"{ep_title}${ep['vod_id']}")
                if parts:
                    vod = {
                        "vod_id": vod_id,
                        "vod_name": title or f"视频{vod_id}",
                        "vod_pic": pic or (episodes[0].get("vod_pic") if episodes else ""),
                        "vod_content": intro,
                        "vod_play_from": "一抖阁 (合集)",
                        "vod_play_url": "#".join(parts)
                    }
                    return {"list": [vod]}

        # ----- 普通视频页：提取播放地址 -----
        play_url = ""

        video_tag = soup.select_one("video source, video")
        if video_tag:
            play_url = video_tag.get("src", "") or video_tag.get("data-src", "")
            play_url = self._fix_url(play_url)

        if not play_url:
            iframe_tag = soup.select_one("iframe")
            if iframe_tag:
                play_url = iframe_tag.get("src", "")
                play_url = self._fix_url(play_url)

        if not play_url:
            m3u8_match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html)
            if m3u8_match:
                play_url = m3u8_match.group(1)
            else:
                mp4_match = re.search(r'(https?://[^\s"\']+\.mp4[^\s"\']*)', html)
                if mp4_match:
                    play_url = mp4_match.group(1)

        if not play_url:
            js_match = re.search(r'file\s*:\s*["\']([^"\']+\.(?:m3u8|mp4)[^"\']*)["\']', html)
            if js_match:
                play_url = js_match.group(1)
                play_url = self._fix_url(play_url)

        if not play_url:
            embed_match = re.search(r'\[video[^\]]*src=["\']([^"\']+)["\']', html)
            if embed_match:
                play_url = embed_match.group(1)
                play_url = self._fix_url(play_url)

        if not play_url:
            # 尝试从 data-video-url 或 JSON-LD 提取
            player_div = soup.select_one("[data-video-player-wrap]")
            if player_div:
                dv = player_div.get("data-video-url", "")
                if dv:
                    play_url = self._fix_url(dv)
            if not play_url:
                json_ld = soup.select_one('script[type="application/ld+json"]')
                if json_ld:
                    try:
                        data = json.loads(json_ld.string)
                        if isinstance(data, dict):
                            content_url = data.get("contentUrl") or data.get("embedUrl")
                            if content_url:
                                play_url = self._fix_url(content_url)
                    except:
                        pass

        if not play_url:
            play_url = url

        return {"list": [{
            "vod_id": vod_id,
            "vod_name": title or f"视频{vod_id}",
            "vod_pic": pic,
            "vod_content": intro,
            "vod_play_from": "一抖阁",
            "vod_play_url": f"播放${play_url}"
        }]}

    # ===== 播放器 =====
    def playerContent(self, flag, id, vipFlags=None):
        if id.startswith("http") and (".m3u8" in id or ".mp4" in id):
            return {"parse": 0, "playUrl": "", "url": id, "header": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": self.host + "/"
            }}

        if id.startswith(self.host) or id.startswith("/video/"):
            try:
                url = id if id.startswith("http") else self._fix_url(id)
                html = self._fetch(url)
                if html:
                    # 尝试 data-video-url
                    dm = re.search(r'data-video-url="([^"]+)"', html)
                    if dm:
                        return {"parse": 0, "playUrl": "", "url": self._fix_url(dm.group(1)), "header": {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            "Referer": self.host + "/"
                        }}
                    # 尝试 JSON-LD
                    json_ld = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
                    if json_ld:
                        try:
                            data = json.loads(json_ld.group(1))
                            if isinstance(data, dict):
                                content_url = data.get("contentUrl") or data.get("embedUrl")
                                if content_url:
                                    return {"parse": 0, "playUrl": "", "url": self._fix_url(content_url), "header": {
                                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                                        "Referer": self.host + "/"
                                    }}
                        except:
                            pass
                    m3u8_match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html)
                    if m3u8_match:
                        return {"parse": 0, "playUrl": "", "url": m3u8_match.group(1), "header": {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            "Referer": self.host + "/"
                        }}
                    mp4_match = re.search(r'(https?://[^\s"\']+\.mp4[^\s"\']*)', html)
                    if mp4_match:
                        return {"parse": 0, "playUrl": "", "url": mp4_match.group(1), "header": {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            "Referer": self.host + "/"
                        }}
                    video_match = re.search(r'<video[^>]+src=["\']([^"\']+)["\']', html)
                    if video_match:
                        return {"parse": 0, "playUrl": "", "url": self._fix_url(video_match.group(1)), "header": {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            "Referer": self.host + "/"
                        }}
            except Exception:
                pass

        return {"parse": 1, "playUrl": "", "url": id, "header": {}}

    # ===== 搜索 =====
    def searchContent(self, key, quick=False, pg="1"):
        pg = int(pg) if pg else 1
        enc_key = urllib.parse.quote(key)

        if pg <= 1:
            url = f"{self.host}/?s={enc_key}&post_type=video"
        else:
            url = f"{self.host}/page/{pg}/?s={enc_key}&post_type=video"

        html = self._fetch(url)
        if not html:
            return {"list": [], "page": pg, "pagecount": 1, "limit": 20, "total": 0}

        videos = self._extract_search_results(html)
        pagecount = self._extract_pagecount(html)

        if pagecount <= 1 and len(videos) >= 20:
            pagecount = pg + 1
        if pagecount < pg:
            pagecount = pg

        return {"list": videos, "page": pg, "pagecount": pagecount, "limit": 20, "total": pagecount * 20}

    def _extract_search_results(self, html):
        soup = BeautifulSoup(html, "html.parser")
        videos = []
        seen = set()

        for item in soup.select(".video-card, .search-result, article"):
            a_tag = item.find("a", href=True)
            if not a_tag:
                continue
            href = a_tag.get("href", "")
            if not href or href in seen:
                continue
            seen.add(href)

            if not re.search(r"/video/[^/]+/", href):
                continue

            id_match = re.search(r"/video/([^/]+)/", href)
            vod_id = id_match.group(1) if id_match else ""

            title_tag = item.select_one(".video-card__title, .entry-title, h2, h3")
            title = title_tag.get_text(strip=True) if title_tag else ""

            img_tag = item.select_one(".video-card__media img, .attachment-post-thumbnail, img")
            pic = ""
            if img_tag:
                pic = img_tag.get("src", "") or img_tag.get("data-src", "")
                pic = self._fix_url(pic)

            remark = ""
            duration_tag = item.select_one(".video-card__duration")
            if duration_tag:
                remark = duration_tag.get_text(strip=True)

            if vod_id:
                videos.append({"vod_id": vod_id, "vod_name": title, "vod_pic": pic, "vod_remarks": remark})

        return videos

    def isVideoFormat(self, url):
        return url and (".m3u8" in url.lower() or ".mp4" in url.lower())

    def manualVideoCheck(self):
        return False

    def destroy(self):
        if self.session:
            self.session.close()

    def localProxy(self, param):
        return None