import logging
import os
import re
import socket
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import certifi
from flask import Flask, jsonify, render_template

app = Flask(__name__)

SOURCE_URL = "https://procurement.gov.kz/ru/search/announce"
SOURCE_HOST = "procurement.gov.kz"
PLATFORM_URL = "https://zakup.gov.kz/cabinet/"
PLATFORM_HOST = "zakup.gov.kz"
LOCAL_TZ = ZoneInfo("Asia/Almaty")
CACHE_SECONDS = 900
REQUEST_TIMEOUT = 8
INSPECT_MAX_HTML = 2 * 1024 * 1024
INSPECT_MAX_JS = 2 * 1024 * 1024
INSPECT_MAX_SCRIPTS = 12

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_cache = {"expires": 0, "data": None}


def now_local():
    return datetime.now(LOCAL_TZ).isoformat()


def create_ssl_context():
    return ssl.create_default_context(cafile=certifi.where())


def clean_text(value):
    return re.sub(r"\s+", " ", value or "").strip()


def parse_date(value):
    value = clean_text(value)
    for fmt in ("%d.%m.%Y %H:%M", "%d.%m.%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).isoformat()
        except ValueError:
            pass
    return None


def parse_amount(value):
    value = clean_text(value).replace("\xa0", "").replace(" ", "").replace(",", ".")
    match = re.search(r"\d+(?:\.\d+)?", value)
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


def check_source(url, expected_host):
    result = {
        "url": url,
        "host": expected_host,
        "ok": False,
        "dns_ok": False,
        "https_ok": False,
        "http_status": None,
        "response_time_ms": None,
        "resolved_addresses": [],
        "error": None,
    }
    started = time.monotonic()
    try:
        addresses = socket.getaddrinfo(expected_host, 443, type=socket.SOCK_STREAM)
        result["dns_ok"] = True
        result["resolved_addresses"] = sorted(set(item[4][0] for item in addresses))
    except Exception as error:
        result["error"] = "DNS_ERROR: " + str(error)
        result["response_time_ms"] = round((time.monotonic() - started) * 1000)
        return result

    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; KzzakupbotHub/1.0)",
                "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
                "Accept-Language": "ru,en;q=0.8",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT, context=create_ssl_context()) as response:
                result["http_status"] = response.status
                response.read(1024)
                result["https_ok"] = True
                result["ok"] = 200 <= response.status < 400
        except urllib.error.HTTPError as error:
            result["http_status"] = error.code
            result["https_ok"] = True
            result["ok"] = 200 <= error.code < 400
            result["error"] = "HTTP_ERROR: " + str(error.code)
        except Exception as error:
            result["error"] = type(error).__name__ + ": " + str(error)
    except Exception as error:
        result["error"] = str(error)

    result["response_time_ms"] = round((time.monotonic() - started) * 1000)
    return result


class AnnouncementHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.current_row = None
        self.current_cell = None
        self.in_cell = False
        self.in_link = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tr":
            self.current_row = {"cells": [], "links": []}
        elif tag in ("td", "th") and self.current_row is not None:
            self.current_cell = ""
            self.in_cell = True
        elif tag == "a" and self.current_row is not None:
            self.current_row["links"].append({"href": attrs.get("href", ""), "text": ""})
            self.in_link = True

    def handle_data(self, data):
        if self.current_row is None:
            return
        if self.in_cell:
            self.current_cell += data
        if self.in_link and self.current_row["links"]:
            self.current_row["links"][-1]["text"] += data

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.in_cell:
            self.current_row["cells"].append(clean_text(self.current_cell))
            self.current_cell = None
            self.in_cell = False
        elif tag == "a":
            self.in_link = False
        elif tag == "tr" and self.current_row is not None:
            if self.current_row["cells"]:
                self.rows.append(self.current_row)
            self.current_row = None


def extract_number(value):
    match = re.search(r"\b\d{6,}-\d+\b", value or "")
    return match.group(0) if match else None


def extract_source_link(row):
    for link in row.get("links", []):
        href = link.get("href", "")
        if not href:
            continue
        full_url = urljoin(SOURCE_URL, href)
        parsed = urlparse(full_url)
        if parsed.scheme == "https" and parsed.hostname and (
            parsed.hostname == SOURCE_HOST or parsed.hostname.endswith("." + SOURCE_HOST)
        ):
            return full_url
    return SOURCE_URL


def parse_announcement_row(row):
    cells = row.get("cells", [])
    if len(cells) < 7:
        return None
    number = extract_number(cells[0])
    if not number:
        return None
    combined_text = " ".join(cells)
    organizer_match = re.search(
        r"Организатор\s*:\s*(.*?)(?:Заказчик\s*:|$)", combined_text, re.IGNORECASE
    )
    organizer = clean_text(organizer_match.group(1)) if organizer_match else None
    return {
        "number": number,
        "name": cells[1],
        "method": cells[2],
        "organizer": organizer,
        "start_date": parse_date(cells[3]),
        "end_date": parse_date(cells[4]),
        "amount": parse_amount(cells[5]),
        "status": cells[6],
        "url": extract_source_link(row),
        "source": SOURCE_URL,
    }


def download_portal_page():
    request = urllib.request.Request(
        SOURCE_URL,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; KzzakupbotHub/1.0)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "ru,en;q=0.8",
            "Connection": "close",
        },
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT, context=create_ssl_context()) as response:
        if response.status != 200:
            raise RuntimeError("PORTAL_HTTP_ERROR: " + str(response.status))
        raw = response.read()
        encoding = response.headers.get_content_charset() or "utf-8"
        return raw.decode(encoding, errors="replace")


def fetch_public_tenders():
    html = download_portal_page()
    parser = AnnouncementHTMLParser()
    parser.feed(html)
    if not parser.rows:
        raise RuntimeError("NO_ANNOUNCEMENT_TABLE: структура страницы не распознана")

    items = []
    for row in parser.rows:
        item = parse_announcement_row(row)
        if not item:
            continue
        if item["end_date"]:
            try:
                deadline = datetime.fromisoformat(item["end_date"])
                if deadline < datetime.now():
                    continue
            except ValueError:
                pass
        items.append(item)

    if not items:
        raise RuntimeError("NO_VALID_ANNOUNCEMENTS: объявления не распознаны")
    items.sort(key=lambda item: (item["end_date"] is None, item["end_date"] or ""))
    return {
        "ok": True,
        "configured": True,
        "count": len(items[:30]),
        "items": items[:30],
        "source": SOURCE_URL,
        "updated_at": now_local(),
    }


class PlatformHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self.title = False
        self.title_text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script":
            src = attrs.get("src")
            if src:
                self.scripts.append(src)
        elif tag == "title":
            self.title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self.title = False

    def handle_data(self, data):
        if self.title:
            self.title_text.append(data)


def inspect_platform_assets():
    request = urllib.request.Request(
        PLATFORM_URL,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; KzzakupbotHub/1.0)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT, context=create_ssl_context()) as response:
        status = response.status
        content_type = response.headers.get("Content-Type", "")
        raw_html = response.read(INSPECT_MAX_HTML)
        encoding = response.headers.get_content_charset() or "utf-8"

    html = raw_html.decode(encoding, errors="replace")
    parser = PlatformHTMLParser()
    parser.feed(html)

    scripts = []
    seen = set()
    for src in parser.scripts:
        full_url = urljoin(PLATFORM_URL, src)
        parsed = urlparse(full_url)
        if parsed.scheme != "https" or not parsed.hostname:
            continue
        if parsed.hostname != PLATFORM_HOST and not parsed.hostname.endswith("." + PLATFORM_HOST):
            continue
        if full_url not in seen:
            seen.add(full_url)
            scripts.append(full_url)

    endpoint_pattern = re.compile(
        r"(?:/api/[A-Za-z0-9_./?=&%-]+|/graphql(?:[/?][A-Za-z0-9_./?=&%-]*)?|"
        r"https://[A-Za-z0-9.-]*zakup\.gov\.kz/[A-Za-z0-9_./?=&%-]+)",
        re.IGNORECASE,
    )
    keyword_pattern = re.compile(r"(announcement|announcements|tender|tenders|lot|lots|search|graphql|api)", re.I)
    found = set(endpoint_pattern.findall(html))
    js_checked = []
    js_errors = []

    for script_url in scripts[:INSPECT_MAX_SCRIPTS]:
        try:
            js_request = urllib.request.Request(
                script_url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; KzzakupbotHub/1.0)"},
            )
            with urllib.request.urlopen(
                js_request, timeout=REQUEST_TIMEOUT, context=create_ssl_context()
            ) as response:
                js_raw = response.read(INSPECT_MAX_JS)
            js_text = js_raw.decode("utf-8", errors="replace")
            for candidate in endpoint_pattern.findall(js_text):
                if keyword_pattern.search(candidate):
                    found.add(candidate)
            # Also collect relative route strings that may be used by client-side routers.
            for candidate in re.findall(r"[\"'](/[^\"']{1,180})[\"']", js_text):
                if keyword_pattern.search(candidate) and not candidate.startswith("//"):
                    found.add(candidate)
            js_checked.append({"url": script_url, "bytes_read": len(js_raw), "ok": True})
        except Exception as error:
            js_errors.append({"url": script_url, "error": type(error).__name__ + ": " + str(error)})
            js_checked.append({"url": script_url, "ok": False})

    return {
        "ok": 200 <= status < 400,
        "url": PLATFORM_URL,
        "http_status": status,
        "content_type": content_type,
        "html_bytes_read": len(raw_html),
        "page_title": clean_text(" ".join(parser.title_text)),
        "script_count_found": len(scripts),
        "scripts_checked": js_checked,
        "script_errors": js_errors,
        "candidate_api_or_search_paths": sorted(found)[:100],
        "note": "Это предварительный анализ публичных HTML/JS-файлов, а не подтверждение доступности найденных API-методов.",
    }



def inspect_platform_bootstrap():
    """Return the public bootstrap JavaScript so its module-loading logic can be inspected."""
    html_request = urllib.request.Request(
        PLATFORM_URL,
        headers={"User-Agent": "Mozilla/5.0 (compatible; KzzakupbotHub/1.0)", "Accept": "text/html"},
    )
    with urllib.request.urlopen(
        html_request, timeout=REQUEST_TIMEOUT, context=create_ssl_context()
    ) as response:
        html = response.read(INSPECT_MAX_HTML).decode(
            response.headers.get_content_charset() or "utf-8", errors="replace"
        )

    parser = PlatformHTMLParser()
    parser.feed(html)
    script_urls = []
    for src in parser.scripts:
        full_url = urljoin(PLATFORM_URL, src)
        parsed = urlparse(full_url)
        if (
            parsed.scheme == "https"
            and parsed.hostname
            and (parsed.hostname == PLATFORM_HOST or parsed.hostname.endswith("." + PLATFORM_HOST))
        ):
            script_urls.append(full_url)

    if not script_urls:
        raise RuntimeError("NO_PUBLIC_BOOTSTRAP_SCRIPT_FOUND")

    inspected = []
    for script_url in script_urls[:INSPECT_MAX_SCRIPTS]:
        request = urllib.request.Request(
            script_url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; KzzakupbotHub/1.0)", "Accept": "*/*"},
        )
        with urllib.request.urlopen(
            request, timeout=REQUEST_TIMEOUT, context=create_ssl_context()
        ) as response:
            raw = response.read(INSPECT_MAX_JS)
            content_type = response.headers.get("Content-Type", "")

        js_text = raw.decode("utf-8", errors="replace")
        # Collect import() targets, module URLs, and URL-like string literals.
        dynamic_imports = re.findall(
            r"import\s*\(\s*[\"']([^\"']+)[\"']\s*\)", js_text
        )
        static_imports = re.findall(
            r"(?:from\s*|import\s*)[\"']([^\"']+)[\"']", js_text
        )
        url_literals = re.findall(
            r"[\"']((?:https?://|/)[^\"']{1,500})[\"']", js_text
        )
        inspected.append({
            "url": script_url,
            "content_type": content_type,
            "bytes_read": len(raw),
            "dynamic_imports": sorted(set(dynamic_imports))[:100],
            "static_imports": sorted(set(static_imports))[:100],
            "url_literals": sorted(set(url_literals))[:100],
            "source_text": js_text[:20000],
        })

    return {
        "ok": True,
        "checked_at": now_local(),
        "platform_url": PLATFORM_URL,
        "scripts": inspected,
        "note": "Публичный bootstrap-код. Это не означает, что обнаруженные адреса являются API объявлений."
    }

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/healthz")
def healthz():
    return jsonify({"ok": True, "service": "Kzzakupbot Hub", "time": now_local()})


@app.route("/api/source-check")
def source_check():
    logger.info("Starting official procurement source diagnostics")
    return jsonify({
        "checked_at": now_local(),
        "old_portal": check_source(SOURCE_URL, SOURCE_HOST),
        "new_platform": check_source(PLATFORM_URL, PLATFORM_HOST),
        "note": "Проверяется доступность HTTPS-страниц. Успешное соединение не подтверждает наличие публичного API.",
    })


@app.route("/api/platform-inspect")
def platform_inspect():
    try:
        logger.info("Inspecting public HTML and JavaScript assets of the unified procurement platform")
        return jsonify(inspect_platform_assets())
    except Exception as error:
        logger.exception("Unified platform inspection failed")
        return jsonify({
            "ok": False,
            "url": PLATFORM_URL,
            "error": type(error).__name__ + ": " + str(error),
            "checked_at": now_local(),
        }), 502



@app.route("/api/platform-bootstrap")
def platform_bootstrap():
    try:
        logger.info("Reading public bootstrap JavaScript of unified procurement platform")
        return jsonify(inspect_platform_bootstrap())
    except Exception as error:
        logger.exception("Platform bootstrap inspection failed")
        return jsonify({
            "ok": False,
            "url": PLATFORM_URL,
            "error": type(error).__name__ + ": " + str(error),
            "checked_at": now_local(),
        }), 502

@app.route("/api/tenders")
def api_tenders():
    current_time = time.time()
    if _cache["data"] is not None and current_time < _cache["expires"]:
        return jsonify(_cache["data"])
    try:
        data = fetch_public_tenders()
        _cache["data"] = data
        _cache["expires"] = current_time + CACHE_SECONDS
        return jsonify(data)
    except Exception as error:
        logger.exception("Tender portal request failed")
        return jsonify({
            "ok": False,
            "configured": True,
            "count": 0,
            "items": [],
            "message": "Не удалось получить данные официального портала закупок.",
            "details": str(error),
            "source": SOURCE_URL,
            "updated_at": now_local(),
        }), 502


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
        
