
import json
import time
import logging
import re
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_cache = {
    "expires": 0,
    "data": None
}


def clean_text(value):
    if not value:
        return ""

    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def parse_date(value):
    if not value:
        return None

    value = clean_text(value)

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y"
    ]

    for fmt in formats:
        try:
            result = datetime.strptime(value, fmt)
            return result.replace(tzinfo=LOCAL_TZ)
        except ValueError:
            pass

    try:
        result = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

        if result.tzinfo is None:
            result = result.replace(tzinfo=LOCAL_TZ)

        return result.astimezone(LOCAL_TZ)

    except ValueError:
        return None


def parse_amount(value):
    if not value:
        return None

    value = clean_text(value)

    match = re.search(
        r"-?\d[\d\s]*(?:[.,]\d{1,2})?",
        value
    )

    if not match:
        return None

    number = match.group(0)
    number = re.sub(r"\s+", "", number)
    number = number.replace(",", ".")

    try:
        return float(number)
    except ValueError:
        return None


class AnnouncementHTMLParser(HTMLParser):
    """
    Извлекает строки таблиц и ссылки из публичной HTML-страницы.
    Не выполняет JavaScript и не использует авторизацию.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)

        self.rows = []
        self.current_row = None
        self.current_cell = None
        self.current_anchor = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag == "tr" and self.current_row is None:
            self.current_row = {
                "cells": [],
                "links": []
            }

        elif tag in ("td", "th") and self.current_row is not None:
            if self.current_cell is None:
                self.current_cell = {
                    "text": "",
                    "links": []
                }

        elif tag == "a" and self.current_row is not None:
            href = attrs.get("href")

            if href:
                link = {
                    "href": href,
                    "cell": self.current_cell
                }

                self.current_row["links"].append(link)

                if self.current_cell is not None:
                    self.current_cell["links"].append(link)

        elif tag in ("br", "p", "div") and self.current_cell is not None:
            self.current_cell["text"] += " "

    def handle_data(self, data):
        if self.current_cell is not None:
            self.current_cell["text"] += data

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.current_cell is not None:
            self.current_row["cells"].append(
                self.current_cell
            )
            self.current_cell = None

        elif tag == "tr" and self.current_row is not None:
            if self.current_cell is not None:
                self.current_row["cells"].append(
                    self.current_cell
                )
                self.current_cell = None

            if self.current_row["cells"]:
                self.rows.append(self.current_row)

            self.current_row = None


def extract_number(cells):
    for cell in cells:
        text = clean_text(cell.get("text", ""))

        match = re.search(
            r"\b\d{6,}-\d+\b",
            text
        )

        if match:
            return match.group(0)

    return None


def extract_source_link(row):
    links = row.get("links", [])

    # Сначала проверяем ссылки из ячейки с наименованием.
    cells = row.get("cells", [])

    if len(cells) > 1:
        candidates = cells[1].get("links", [])
    else:
        candidates = []

    candidates = candidates + links

    for item in candidates:
        href = item.get("href")

        if not href:
            continue

        absolute_url = urljoin(SOURCE_URL, href)
        parsed = urlparse(absolute_url)

        if parsed.scheme not in ("http", "https"):
            continue

        if parsed.netloc.lower() != SOURCE_HOST:
            continue

        if parsed.path == "/":
            continue

        return absolute_url

    return None


def parse_announcement_row(row, now):
    cells = row.get("cells", [])

    if len(cells) < 7:
        return None

    number = extract_number(cells)

    if not number:
        return None

    name_cell = clean_text(cells[1].get("text", ""))

    organizer = "Не указан"

    organizer_match = re.search(
        r"Организатор\s*:\s*(.*)",
        name_cell,
        flags=re.IGNORECASE
    )

    if organizer_match:
        organizer = clean_text(
            organizer_match.group(1)
        )

        name = clean_text(
            name_cell[:organizer_match.start()]
        )
    else:
        name = name_cell

    method = clean_text(cells[2].get("text", ""))
    start_text = clean_text(cells[3].get("text", ""))
    end_text = clean_text(cells[4].get("text", ""))
    amount_text = clean_text(cells[5].get("text", ""))
    status = clean_text(cells[6].get("text", ""))

    start_date = parse_date(start_text)
    end_date = parse_date(end_text)

    # Если срок не удалось распознать, не выдаём запись
    # за действующую закупку.
    if not end_date:
        return None

    # Не показываем объявления с истёкшим сроком подачи.
    if end_date <= now:
        return None

    if not name:
        name = "Название не указано"

    return {
        "id": number,
        "number": number,
        "name": name,
        "method": method or "Не указан",
        "organizer": organizer,
        "amount": parse_amount(amount_text),
        "published": None,
        "start_date": start_text or None,
        "end_date": end_text or None,
        "status": status or "Не указан",
        "url": extract_source_link(row),
        "source": "Единая платформа государственных закупок РК"
    }


def fetch_public_tenders():
    request = urllib.request.Request(
        SOURCE_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (compatible; "
                "KzzakupbotHub/1.0)"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "ru-RU,ru;q=0.9,kk;q=0.8"
        },
        method="GET"
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:

        status_code = response.getcode()

        if status_code != 200:
            raise RuntimeError(
                "PUBLIC_PORTAL_HTTP_ERROR"
            )

        raw_html = response.read()

        charset = response.headers.get_content_charset()

        if not charset:
            charset = "utf-8"

        html = raw_html.decode(
            charset,
            errors="replace"
        )

    parser = AnnouncementHTMLParser()
    parser.feed(html)

    if not parser.rows:
        raise RuntimeError(
            "PUBLIC_PORTAL_TABLE_NOT_FOUND"
        )

    now = datetime.now(LOCAL_TZ)
    tenders = []

    for row in parser.rows:
        item = parse_announcement_row(row, now)

        if item:
            tenders.append(item)

    # Сортировка по сроку окончания:
    # ближайшие дедлайны идут первыми.
    tenders.sort(
        key=lambda item: (
            parse_date(item["end_date"])
            or datetime.max.replace(tzinfo=LOCAL_TZ)
        )
    )

    return {
        "ok": True,
        "configured": True,
        "items": tenders[:30],
        "count": len(tenders[:30]),
        "updated_at": datetime.now(LOCAL_TZ).isoformat(),
        "source": SOURCE_URL,
        "source_name": (
            "Официальная Единая платформа "
            "государственных закупок РК"
        ),
        "cache_seconds": CACHE_SECONDS
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/tenders")
def api_tenders():
    now = time.time()

    if (
        _cache["data"] is not None
        and now < _cache["expires"]
    ):
        return jsonify(_cache["data"])

    try:
        data = fetch_public_tenders()

        _cache["data"] = data
        _cache["expires"] = now + CACHE_SECONDS

        return jsonify(data)

    except urllib.error.HTTPError as error:
        logger.exception(
            "Публичный портал вернул HTTP-ошибку"
        )

        message = (
            "Публичный портал временно отклонил запрос."
        )

    except urllib.error.URLError:
        logger.exception(
            "Не удалось подключиться к публичному порталу"
        )

        message = (
            "Не удалось подключиться к порталу закупок."
        )

    except Exception:
        logger.exception(
            "Ошибка загрузки публичных объявлений"
        )

        message = (
            "Не удалось обработать таблицу объявлений. "
            "Возможно, портал изменил структуру страницы."
        )

    # Если свежая загрузка не удалась, можно показать
    # предыдущий кэш, явно обозначив его как устаревший.
    if _cache["data"] is not None:
        stale_data = dict(_cache["data"])
        stale_data["stale"] = True
        stale_data["warning"] = message

        return jsonify(stale_data)

    return jsonify({
        "ok": False,
        "configured": True,
        "message": message,
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
