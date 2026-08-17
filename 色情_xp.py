#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
小色姐 (se.xiaosejie73.xyz) — MacCMS v10 伪静态(slug) 爬虫
========================================================
结构（已实测确认）：
  * 分类页  /vodtype/{slug}/           第 N 页 /vodtype/{slug}-{N}/
  * 详情/播放 /vodplay/{id}-{sid}-{nid}/  列表直接链到播放页（无独立详情页）
  * 搜索    /vodsearch/{wd}-------------/     第 N 页 /vodsearch/{wd}----------{N}---.html
  * 播放页内嵌 var player_aaaa={...}：
      url = 真实 m3u8（CDN: aoskkkazy.com 等，直链可播）
      from = 播放源名(Oscar), id/sid/nid, vod_data{vod_name,vod_class,...}
  * ER_POSTER = 封面图（CDN: abfrkjesk.com）
  * 站点为单集影片（source-btn 唯一, nid=1），vod_play_url 直接给出 m3u8
  * MacCMS 标准 API (/api.php/provide/vod/) 已关闭("closed")，必须走页面解析
  * 全站 HTML 实体编码，解析需 html.unescape
"""

import re
import json
import html
import time
import urllib.parse

try:
    import requests
except Exception:
    requests = None


from base.spider import Spider


class Spider(Spider):
    def __init__(self):
        super().__init__()
        self.name = "小色姐"
        self.host = "https://se.xiaosejie73.xyz"
        self.header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Referer": self.host + "/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        self._cats = None

    # ---------------- 网络 ----------------
    def _fetch(self, path, timeout=12):
        """GET 页面，返回 HTML 字符串；失败返回 ""。断连/5xx 重试一次"""
        url = path if path.startswith("http") else self.host + path
        for attempt in (0, 1):
            try:
                if requests is not None:
                    r = requests.get(url, headers=self.header, timeout=timeout)
                    if r.status_code == 200:
                        return r.text
                else:
                    import urllib.request
                    req = urllib.request.Request(url, headers=self.header)
                    with urllib.request.urlopen(req, timeout=timeout) as resp:
                        return resp.read().decode("utf-8", "replace")
            except Exception:
                pass
            if attempt == 0:
                time.sleep(1.0)
        return ""

    # ---------------- 工具 ----------------
    def fix_url(self, url):
        if not url:
            return ""
        url = url.replace("\\u0026", "&").replace("&amp;", "&")
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return urllib.parse.urljoin(self.host, url)
        return url

    def isVideoFormat(self, url):
        if not url:
            return False
        low = url.lower()
        return any(low.endswith(e) for e in [".m3u8", ".mp4", ".flv", ".mkv", ".ts", ".avi", ".mov", ".webm"]) or "m3u8" in low

    def getName(self):
        return self.name

    def init(self, extend=""):
        if extend:
            try:
                cfg = json.loads(extend) if extend.strip().startswith("{") else {}
                if isinstance(cfg, dict):
                    if cfg.get("host"):
                        self.host = cfg["host"].rstrip("/")
                        self.header["Referer"] = self.host + "/"
                    if cfg.get("ua"):
                        self.header["User-Agent"] = cfg["ua"]
            except Exception:
                pass

    # ---------------- 列表解析 ----------------
    def _parse_cards(self, page):
        """解析 vod-item 卡片 -> [{vod_id,vod_name,vod_pic,vod_remarks}]"""
        out = []
        if not page:
            return out
        pat = re.compile(
            r'<a class="vod-cover-link"[^>]*href="(/vodplay/[^"]+)"[^>]*title="([^"]*)"[^>]*>'
            r'</a>\s*<img class="vod-cover"[^>]*src="([^"]+)"'
        )
        for m in pat.finditer(page):
            path, title, cover = m.group(1), m.group(2), m.group(3)
            mid = re.match(r"/vodplay/(.+?)-(\d+)-(\d+)/", path)
            if not mid:
                continue
            vid = mid.group(1)
            vod = {
                "vod_id": vid,
                "vod_name": html.unescape(title).strip(),
                "vod_pic": self.fix_url(cover),
                "vod_remarks": "",
            }
            if vod["vod_name"]:
                out.append(vod)
        # 去重
        seen, uniq = set(), []
        for v in out:
            if v["vod_id"] not in seen:
                seen.add(v["vod_id"])
                uniq.append(v)
        return uniq

    def _parse_classes(self, page):
        """首页导航 -> [{type_id, type_name}]（链接文本可能在 <span> 内）"""
        cats = []
        seen = set()
        for m in re.finditer(r'<a[^>]+href="(/vodtype/[^"]+)"[^>]*>([\s\S]{0,300}?)</a>', page):
            href = m.group(1)
            name = html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
            slug = href.rstrip("/").rsplit("/", 1)[-1]
            if not slug or not name or name in seen:
                continue
            seen.add(name)
            cats.append({"type_id": slug, "type_name": name})
        return cats

    # ---------------- 首页 ----------------
    def homeContent(self, filter):
        result = {"class": [], "filters": {}}
        try:
            page = self._fetch("/")
            cats = self._parse_classes(page)
            if cats:
                result["class"] = cats
            lst = self._parse_cards(page)
            if lst:
                result["list"] = lst[:40]
        except Exception:
            pass
        return result

    def homeVideoContent(self):
        result = {"list": []}
        try:
            page = self._fetch("/")
            lst = self._parse_cards(page)
            result["list"] = lst[:40]
        except Exception:
            pass
        return result

    # ---------------- 分类 ----------------
    def categoryContent(self, tid, pg, filter, extend):
        result = {"list": [], "page": 1, "pagecount": 1, "limit": 30, "total": 0}
        try:
            tid = str(tid or "").strip("/")
            page = max(int(pg or 1), 1)
            path = "/vodtype/%s/" % tid if page <= 1 else "/vodtype/%s-%d/" % (tid, page)
            body = self._fetch(path)
            lst = self._parse_cards(body)
            result["list"] = lst
            result["page"] = page
            if lst:
                result["limit"] = len(lst)
            # 页数：取最大数字分页链接（含「尾页」，如 -675/）
            maxn = 1
            for m in re.finditer(r"/vodtype/%s-(\d+)/" % re.escape(tid), body):
                try:
                    maxn = max(maxn, int(m.group(1)))
                except Exception:
                    pass
            result["pagecount"] = maxn
            # 总数：$(".mac_total").text('20234')
            tm = re.search(r"mac_total\"\)\.text\('(\d+)'\)", body)
            if tm:
                result["total"] = int(tm.group(1))
            else:
                result["total"] = result["limit"] * maxn
        except Exception:
            pass
        return result

    # ---------------- 详情 ----------------
    def detailContent(self, ids):
        result = {"list": []}
        try:
            vid = str(ids[0]) if isinstance(ids, list) else str(ids)
            if not vid:
                return result
            body = self._fetch("/vodplay/%s-1-1/" % vid)
            if not body:
                return result
            dec = html.unescape(body)
            # 1) player_aaaa JSON
            pm = re.search(r'player_aaaa=(\{.*?\})\s*</script>', body, re.S)
            if not pm:
                pm = re.search(r'player_aaaa=(\{.*?\})', body, re.S)
            pdata = json.loads(pm.group(1)) if pm else {}
            vod = {}
            vd = pdata.get("vod_data") or {}
            vod["vod_id"] = vid
            vod["vod_name"] = html.unescape(vd.get("vod_name") or "").strip()
            if not vod["vod_name"]:
                hm = re.search(r"<h1[^>]*>([\s\S]{0,300}?)</h1>", dec)
                if hm:
                    t = re.sub(r"<[^>]+>", "", hm.group(1)).strip()
                    t = re.sub(r"^\[[^\]]*\]\s*", "", t)
                    vod["vod_name"] = t.strip()
            vod["vod_actor"] = vd.get("vod_actor") or ""
            vod["vod_director"] = vd.get("vod_director") or ""
            vod["vod_tag"] = vd.get("vod_class") or ""
            # 2) 封面
            em = re.search(r'ER_POSTER\s*=\s*"([^"]+)"', body)
            vod["vod_pic"] = self.fix_url(em.group(1)) if em else ""
            # 3) 简介
            dm = re.search(r'id="playDescBody"[^>]*>([\s\S]{0,1000}?)</div>', dec)
            if dm:
                vod["vod_content"] = re.sub(r"<[^>]+>", "", dm.group(1)).strip()
            # 4) 播放
            url = pdata.get("url") or ""
            if url and self.isVideoFormat(url):
                from_name = pdata.get("from") or "Oscar"
                vod["vod_play_from"] = from_name
                vod["vod_play_url"] = "正片$%s" % self.fix_url(url)
            if vod.get("vod_name") or vod.get("vod_play_url"):
                result["list"] = [vod]
        except Exception:
            pass
        return result

    # ---------------- 搜索 ----------------
    def searchContent(self, key, quick, pg):
        result = {"list": [], "page": 1, "pagecount": 1, "limit": 24, "total": 0}
        try:
            key = str(key or "").strip()
            if not key:
                return result
            page = max(int(pg or 1), 1)
            wd = urllib.parse.quote(key)
            if page <= 1:
                path = "/vodsearch/%s-------------/" % wd
            else:
                path = "/vodsearch/%s----------%d---.html" % (wd, page)
            body = self._fetch(path)
            lst = self._parse_cards(body)
            result["list"] = lst
            result["page"] = page
            result["pagecount"] = max(1, len(lst) // 24 + 1) if len(lst) >= 24 else 1
        except Exception:
            pass
        return result

    # ---------------- 播放 ----------------
    def playerContent(self, flag, id, vipFlags):
        result = {"parse": 0, "playUrl": "", "url": "", "header": ""}
        try:
            pu = self.fix_url(id) if id else ""
            if self.isVideoFormat(pu):
                result["url"] = pu
                result["header"] = {
                    "User-Agent": self.header["User-Agent"],
                    "Referer": self.host,
                }
        except Exception:
            pass
        return result

    # ---------------- 本地代理（封面图兜底） ----------------
    def localProxy(self, param):
        try:
            url = urllib.parse.unquote(param.get("url", ""))
            if not url:
                return [404, "text/plain", b""]
            h = {"User-Agent": self.header.get("User-Agent", "Mozilla/5.0"), "Referer": self.host}
            try:
                if requests is not None:
                    r = requests.get(url, headers=h, timeout=15)
                    return [r.status_code, r.headers.get("Content-Type", "application/octet-stream"), r.content]
                else:
                    import urllib.request
                    req = urllib.request.Request(url, headers=h)
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        return [resp.status, resp.headers.get("Content-Type", "application/octet-stream"), resp.read()]
            except Exception:
                return [404, "text/plain", b""]
        except Exception:
            return [404, "text/plain", b""]
