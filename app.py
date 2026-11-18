
import json
import time
import logging
import re
import ssl
import socket
import urllib.request
import urllib.error
import certifi

from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

from flask import Flask, render_template, jsonify


app = Flask(__name__)

SOURCE_URL = "https://procurement.gov.kz/ru/search/announce"
SOURCE_HOST = "procurement.gov.kz"

PLATFORM_URL = "https://zakup.gov.kz/cabinet/"
PLATFORM_HOST = "zakup.gov.kz"

LOCAL_TZ = ZoneInfo("Asia/Almaty")

CACHE_SECONDS = 900
REQUEST_TIMEOUT = 8

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

_cache = {
    "expires": 0,
    "data": None
}


def now_local():
    return datetime.now(LOCAL_TZ).isoformat()


def create_ssl_context():
    return ssl.create_default_context(cafile=certifi.where())


def clean_text(value):
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def parse_date(value):
    value = clean_text(value)

    formats = [
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).isoformat()
        except ValueError:
            pass

    return None


def parse_amount(value):
    if not value:
        return None

    value = clean_text(value)
    value = value.replace("\xa0", "").replace(" ", "")
    value = value.replace(",", ".")

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
        "error": None
    }

    started = time.monotonic()

    try:
        addresses = socket.getaddrinfo(
            expected_host,
            443,
            type=socket.SOCK_STREAM
        )

        result["dns_ok"] = True
        result["resolved_addresses"] = sorted(
            list(set(item[4][0] for item in addresses))
        )

    except Exception as error:
        result["error"] = "DNS_ERROR: " + str(error)
        result["response_time_ms"] = round(
            (time.monotonic() - started) * 1000
        )
        return result

    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "Chrome/120.0 Safari/537.36"
                ),
                "Accept": (
                    "text/html,application/xhtml+xml,"
                    "application/json;q=0.9,*/*;q=0.8"
                ),
                "Accept-Language": "ru,en;q=0.8"
            }
        )

        context = create_ssl_context()

        try:
            response = urllib.request.urlopen(
                request,
                timeout=REQUEST_TIMEOUT,
                context=context
            )

            result["http_status"] = response.status
            response.read(1024)
            response.close()

            result["https_ok"] = True
            result["ok"] = 200 <= result["http_status"] < 400

        except urllib.error.HTTPError as error:
            result["http_status"] = error.code
            result["https_ok"] = True
            result["ok"] = 200 <= error.code < 400
            result["error"] = "HTTP_ERROR: " + str(error.code)

        except Exception as error:
            result["error"] = type(error).__name__ + ": " + str(error)

    except Exception as error:
        result["error"] = str(error)

    result["response_time_ms"] = round(
        (time.monotonic() - started) * 1000
    )

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
            self.current_row = {
                "cells": [],
                "links": []
            }

        elif tag in ("td", "th") and self.current_row is not None:
            self.current_cell = ""
            self.in_cell = True

        elif tag == "a" and self.current_row is not None:
            href = attrs.get("href", "")
            self.current_row["links"].append({
                "href": href,
                "text": ""
            })
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
            self.current_row["cells"].append(
                clean_text(self.current_cell)
            )
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

        if (
            parsed.scheme == "https"
            and (
                parsed.hostname == SOURCE_HOST
                or (
                    parsed.hostname
                    and parsed.hostname.endswith("." + SOURCE_HOST)
                )
            )
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

    name = cells[1]
    method = cells[2]
    start_date = parse_date(cells[3])
    end_date = parse_date(cells[4])
    amount = parse_amount(cells[5])
    status = cells[6]

    combined_text = " ".join(cells)

    organizer_match = re.search(
        r"Организатор\s*:\s*(.*?)(?:Заказчик\s*:|$)",
        combined_text,
        re.IGNORECASE
    )

    organizer = (
        clean_text(organizer_match.group(1))
        if organizer_match
        else None
    )

    return {
        "number": number,
        "name": name,
        "method": method,
        "organizer": organizer,
        "start_date": start_date,
        "end_date": end_date,
        "amount": amount,
        "status": status,
        "url": extract_source_link(row),
        "source": SOURCE_URL
    }


def download_portal_page():
    request = urllib.request.Request(
        SOURCE_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "Chrome/120.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "ru,en;q=0.8",
            "Connection": "close"
        }
    )

    context = create_ssl_context()

    with urllib.request.urlopen(
        request,
        timeout=REQUEST_TIMEOUT,
        context=context
    ) as response:

        if response.status != 200:
            raise RuntimeError(
                "PORTAL_HTTP_ERROR: " + str(response.status)
            )

        raw = response.read()

        encoding = response.headers.get_content_charset() or "utf-8"

        return raw.decode(encoding, errors="replace")


def fetch_public_tenders():
    html = download_portal_page()

    parser = AnnouncementHTMLParser()
    parser.feed(html)

    if not parser.rows:
        raise RuntimeError(
            "NO_ANNOUNCEMENT_TABLE: структура страницы не распознана"
        )

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
        raise RuntimeError(
            "NO_VALID_ANNOUNCEMENTS: объявления не распознаны"
        )

    items.sort(
        key=lambda item: (
            item["end_date"] is None,
            item["end_date"] or ""
        )
    )

    return {
        "ok": True,
        "configured": True,
        "count": len(items[:30]),
        "items": items[:30],
        "source": SOURCE_URL,
        "updated_at": now_local()
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/healthz")
def healthz():
    return jsonify({
        "ok": True,
        "service": "Kzzakupbot Hub",
        "time": now_local()
    })


@app.route("/api/source-check")
def source_check():
    logger.info("Starting official procurement source diagnostics")

    old_portal = check_source(
        SOURCE_URL,
        SOURCE_HOST
    )

    new_platform = check_source(
        PLATFORM_URL,
        PLATFORM_HOST
    )

    return jsonify({
        "checked_at": now_local(),
        "old_portal": old_portal,
        "new_platform": new_platform,
        "note": (
            "Проверяется доступность HTTPS-страниц. "
            "Успешное соединение само по себе "
            "не подтверждает наличие публичного API."
        )
    })


@app.route("/api/tenders")
def api_tenders():
    current_time = time.time()

    if (
        _cache["data"] is not None
        and current_time < _cache["expires"]
    ):
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
            "message": (
                "Не удалось получить данные "
                "официального портала закупок."
            ),
            "details": str(error),
            "source": SOURCE_URL,
            "updated_at": now_local()
        }), 502


if __name__ == "__main__":
    port = int(__import__("os").environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
