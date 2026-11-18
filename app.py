
import json
import time
import logging
import re
import ssl
import certifi
import urllib.request
import urllib.error

from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

from flask import Flask, render_template, jsonify

app = Flask(__name__)

SOURCE_URL = "https://procurement.gov.kz/ru/search/announce"
SOURCE_HOST = "procurement.gov.kz"

LOCAL_TZ = ZoneInfo("Asia/Almaty")
CACHE_SECONDS = 900
REQUEST_TIMEOUT = 30

SSL_CONTEXT = ssl.create_default_context(
    cafile=certifi.where()
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

_cache = {
    "expires": 0,
    "data": None
}


def clean_text(value):
    if not value:
        return ""

    value = re.sub(r"\s+", " ", value)
    return value.strip()


def parse_date(value):
    if not value:
        return None

    value = clean_text(value)

    formats = [
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d"
    ]

    for date_format in formats:
        try:
            result = datetime.strptime(value, date_format)
            return result.replace(tzinfo=LOCAL_TZ)
        except ValueError:
            continue

    try:
        result = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

        if result.tzinfo is None:
            result = result.replace(tzinfo=LOCAL_TZ)

        return result.astimezone(LOCAL_TZ)

    except (ValueError, TypeError):
        return None


def parse_amount(value):
    if not value:
        return None

    value = clean_text(value)
    value = value.replace("\xa0", "")
    value = value.replace(" ", "")
    value = value.replace(",", ".")

    match = re.search(r"\d+(?:\.\d+)?", value)

    if not match:
        return None

    try:
        return float(match.group(0))
    except ValueError:
        return None


class AnnouncementHTMLParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.rows = []
        self.current_row = None
        self.current_cell = None
        self.current_link = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag == "tr":
            self.current_row = {
                "cells": [],
                "links": []
            }

        elif tag in ("td", "th") and self.current_row is not None:
            self.current_cell = {
                "text": "",
                "links": []
            }

        elif tag == "a" and self.current_row is not None:
            href = attrs.get("href")

            if href:
                self.current_link = href

    def handle_data(self, data):
        if self.current_cell is not None:
            self.current_cell["text"] += " " + data

        if self.current_link is not None and self.current_row is not None:
            self.current_row["links"].append(self.current_link)

    def handle_endtag(self, tag):
        if tag == "a":
            self.current_link = None

        elif tag in ("td", "th"):
            if self.current_cell is not None and self.current_row is not None:
                self.current_cell["text"] = clean_text(
                    self.current_cell["text"]
                )

                self.current_row["cells"].append(
                    self.current_cell
                )

            self.current_cell = None

        elif tag == "tr":
            if self.current_row is not None:
                self.rows.append(self.current_row)

            self.current_row = None


def extract_number(value):
    match = re.search(r"\b\d{6,}-\d+\b", value or "")
    return match.group(0) if match else None


def extract_source_link(row):
    for href in row.get("links", []):
        full_url = urljoin(SOURCE_URL, href)
        parsed = urlparse(full_url)

        if parsed.scheme != "https":
            continue

        if parsed.hostname not in (
            "procurement.gov.kz",
            "www.procurement.gov.kz"
        ):
            continue

        return full_url

    return None


def parse_announcement_row(row):
    cells = row.get("cells", [])

    if len(cells) < 7:
        return None

    values = [
        clean_text(cell.get("text", ""))
        for cell in cells
    ]

    combined = " ".join(values)

    number = extract_number(combined)

    if not number:
        return None

    name_text = values[1]

    organizer = "Организатор не указан"

    organizer_match = re.search(
        r"Организатор\s*:\s*(.+)",
        name_text,
        re.IGNORECASE
    )

    if organizer_match:
        organizer = clean_text(organizer_match.group(1))
        name_text = clean_text(
            name_text[:organizer_match.start()]
        )

    start_date = parse_date(values[3])
    end_date = parse_date(values[4])

    if not end_date:
        return None

    amount = parse_amount(values[5])

    link = extract_source_link(row)

    return {
        "id": number,
        "number": number,
        "name": name_text or "Название не указано",
        "amount": amount,
        "published": None,
        "start_date": (
            start_date.isoformat() if start_date else None
        ),
        "end_date": end_date.isoformat(),
        "organizer": organizer,
        "method": values[2] or "Не указан",
        "status": values[6] or "Не указан",
        "source": "Государственные закупки РК",
        "url": link
    }


def fetch_public_tenders():

    request = urllib.request.Request(
        SOURCE_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8"
        },
        method="GET"
    )

    logging.info(
        "Запрос публичной страницы закупок: %s",
        SOURCE_URL
    )

    with urllib.request.urlopen(
        request,
        timeout=REQUEST_TIMEOUT,
        context=SSL_CONTEXT
    ) as response:

        status_code = response.status
        final_url = response.geturl()
        html = response.read().decode(
            "utf-8",
            errors="replace"
        )

    logging.info(
        "Ответ портала: HTTP %s, URL: %s, размер: %s",
        status_code,
        final_url,
        len(html)
    )

    parser = AnnouncementHTMLParser()
    parser.feed(html)

    logging.info(
        "Найдено HTML-строк: %s",
        len(parser.rows)
    )

    now = datetime.now(LOCAL_TZ)
    tenders = []

    for row in parser.rows:
        try:
            item = parse_announcement_row(row)

            if not item:
                continue

            end_date = parse_date(item["end_date"])

            if not end_date or end_date <= now:
                continue

            tenders.append(item)

        except Exception:
            logging.exception(
                "Ошибка обработки строки объявления"
            )

    tenders.sort(
        key=lambda item: (
            parse_date(item["end_date"])
            or datetime.max.replace(tzinfo=LOCAL_TZ)
        )
    )

    logging.info(
        "Количество действующих объявлений: %s",
        len(tenders)
    )

    if not parser.rows:
        raise RuntimeError(
            "PORTAL_HTML_HAS_NO_TABLE_ROWS"
        )

    return {
        "ok": True,
        "items": tenders[:30],
        "updated_at": datetime.now(LOCAL_TZ).isoformat(),
        "source": SOURCE_URL,
        "count": len(tenders)
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/tenders")
def api_tenders():

    now = time.time()

    if _cache["data"] and now < _cache["expires"]:
        return jsonify(_cache["data"])

    try:
        data = fetch_public_tenders()

        _cache["data"] = data
        _cache["expires"] = now + CACHE_SECONDS

        return jsonify(data)

    except urllib.error.HTTPError as error:
        logging.exception(
            "HTTP-ошибка портала закупок: %s",
            error.code
        )

        return jsonify({
            "ok": False,
            "message": "Портал вернул HTTP-ошибку.",
            "error_type": "HTTPError",
            "error_code": error.code,
            "source": SOURCE_URL
        }), 502

    except urllib.error.URLError as error:
        logging.exception(
            "Ошибка подключения к порталу закупок"
        )

        return jsonify({
            "ok": False,
            "message": "Не удалось подключиться к порталу закупок.",
            "error_type": "URLError",
            "details": str(error.reason),
            "source": SOURCE_URL
        }), 502

    except Exception as error:
        logging.exception(
            "Ошибка загрузки государственных закупок"
        )

        return jsonify({
            "ok": False,
            "message": "Не удалось загрузить объявления.",
            "error_type": type(error).__name__,
            "details": str(error),
            "source": SOURCE_URL
        }), 502


@app.route("/healthz")
def healthz():
    return "ok", 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
