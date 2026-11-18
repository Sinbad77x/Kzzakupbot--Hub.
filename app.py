
import json
import time
import logging
import re
import ssl
import os
import urllib.request
import urllib.error
import certifi

from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

from flask import Flask, render_template, jsonify


# =========================================================
# APPLICATION
# =========================================================

app = Flask(__name__)

SOURCE_URL = "https://procurement.gov.kz/ru/search/announce"
SOURCE_HOST = "procurement.gov.kz"

LOCAL_TZ = ZoneInfo("Asia/Almaty")

CACHE_SECONDS = 900
REQUEST_TIMEOUT = 30

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

logger = logging.getLogger(__name__)

_cache = {
    "expires": 0,
    "data": None
}


# =========================================================
# SSL CONFIGURATION AND DIAGNOSTICS
# =========================================================

def log_ssl_configuration():
    """Записывает сведения о сертификатах в Render."""

    logger.info("========== SSL DIAGNOSTICS ==========")

    try:
        logger.info("Python SSL version: %s", ssl.OPENSSL_VERSION)
    except Exception:
        logger.exception("Cannot read OpenSSL version")

    try:
        logger.info("Certifi version: %s", certifi.__version__)
        logger.info("Certifi CA file: %s", certifi.where())
        logger.info(
            "Certifi CA file exists: %s",
            os.path.isfile(certifi.where())
        )
    except Exception:
        logger.exception("Certifi diagnostics failed")

    try:
        logger.info(
            "System default verify paths: %s",
            ssl.get_default_verify_paths()
        )
    except Exception:
        logger.exception("Cannot read system SSL paths")

    logger.info("=====================================")


def create_ssl_contexts():
    """
    Создаёт два безопасных SSL-контекста:
    1. На основе certifi.
    2. На основе системного хранилища Python.

    Проверка сертификатов остаётся включённой.
    """

    contexts = []

    try:
        certifi_context = ssl.create_default_context(
            cafile=certifi.where()
        )

        contexts.append(
            ("certifi", certifi_context)
        )

        logger.info("Created SSL context using certifi")

    except Exception:
        logger.exception("Could not create certifi SSL context")

    try:
        system_context = ssl.create_default_context()

        contexts.append(
            ("system", system_context)
        )

        logger.info("Created system SSL context")

    except Exception:
        logger.exception("Could not create system SSL context")

    if not contexts:
        raise RuntimeError("SSL_CONTEXT_CREATION_FAILED")

    return contexts


# =========================================================
# TEXT AND DATE HELPERS
# =========================================================

def clean_text(value):
    if value is None:
        return ""

    value = re.sub(r"<[^>]+>", " ", str(value))
    value = value.replace("\xa0", " ")

    return re.sub(r"\s+", " ", value).strip()


def parse_date(value):
    if not value:
        return None

    value = clean_text(value)

    formats = [
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            result = datetime.strptime(value, fmt)

            if result.tzinfo is None:
                result = result.replace(tzinfo=LOCAL_TZ)

            return result.astimezone(LOCAL_TZ)

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

    value = (
        value.replace("₸", "")
        .replace("тг.", "")
        .replace("тг", "")
        .replace(" ", "")
        .replace("\u202f", "")
    )

    value = value.replace(",", ".")

    try:
        number = float(value)

        if number.is_integer():
            return int(number)

        return number

    except (ValueError, TypeError):
        return None


# =========================================================
# HTML TABLE PARSER
# =========================================================

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
            self.current_row = []

        elif tag in ("td", "th") and self.current_row is not None:
            self.current_cell = {
                "text": "",
                "links": []
            }

        elif tag == "a" and self.current_cell is not None:
            self.current_link = {
                "href": attrs.get("href", ""),
                "text": ""
            }

    def handle_data(self, data):

        if self.current_cell is not None:
            self.current_cell["text"] += data

        if self.current_link is not None:
            self.current_link["text"] += data

    def handle_endtag(self, tag):

        if tag == "a" and self.current_link is not None:

            if self.current_cell is not None:
                self.current_cell["links"].append(
                    self.current_link
                )

            self.current_link = None

        elif tag in ("td", "th"):

            if (
                self.current_cell is not None
                and self.current_row is not None
            ):
                self.current_cell["text"] = clean_text(
                    self.current_cell["text"]
                )

                self.current_row.append(
                    self.current_cell
                )

            self.current_cell = None

        elif tag == "tr":

            if self.current_row:
                self.rows.append(self.current_row)

            self.current_row = None
            self.current_cell = None
            self.current_link = None


# =========================================================
# ANNOUNCEMENT PARSING
# =========================================================

def extract_number(text):

    match = re.search(
        r"\b\d{6,}-\d+\b",
        text or ""
    )

    if match:
        return match.group(0)

    return None


def extract_source_link(cells):

    for cell in cells:

        for link in cell.get("links", []):

            href = link.get("href", "").strip()

            if not href:
                continue

            absolute_url = urljoin(
                SOURCE_URL,
                href
            )

            parsed = urlparse(absolute_url)

            if (
                parsed.scheme == "https"
                and parsed.hostname
                and (
                    parsed.hostname == SOURCE_HOST
                    or parsed.hostname.endswith("." + SOURCE_HOST)
                )
            ):
                return absolute_url

    return None


def parse_announcement_row(row):

    if len(row) < 7:
        return None

    values = [
        clean_text(cell.get("text", ""))
        for cell in row
    ]

    combined_text = " ".join(values)

    number = extract_number(combined_text)

    if not number:
        return None

    name = values[1] if len(values) > 1 else ""

    organizer = "Организатор не указан"

    organizer_match = re.search(
        r"Организатор\s*:\s*(.+)",
        name,
        flags=re.IGNORECASE
    )

    if organizer_match:
        organizer = organizer_match.group(1).strip()

        name = re.sub(
            r"Организатор\s*:\s*.+$",
            "",
            name,
            flags=re.IGNORECASE
        ).strip()

    if not name:
        name = "Название не указано"

    method = values[2] if len(values) > 2 else ""

    start_date = values[3] if len(values) > 3 else ""

    end_date = values[4] if len(values) > 4 else ""

    amount = values[5] if len(values) > 5 else ""

    status = values[6] if len(values) > 6 else ""

    parsed_end_date = parse_date(end_date)

    if not parsed_end_date:
        return None

    source_link = extract_source_link(row)

    return {
        "id": number,
        "number": number,
        "name": name,
        "amount": parse_amount(amount),
        "amount_text": amount,
        "organizer": organizer,
        "method": method or "Не указан",
        "published": None,
        "start_date": start_date,
        "end_date": end_date,
        "status": status or "Не указан",
        "source": "Государственные закупки РК",
        "url": source_link
    }


# =========================================================
# PORTAL CONNECTION
# =========================================================

def download_portal_page():

    log_ssl_configuration()

    request = urllib.request.Request(
        SOURCE_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
            "Connection": "close"
        },
        method="GET"
    )

    last_error = None

    contexts = create_ssl_contexts()

    for context_name, context in contexts:

        try:

            logger.info(
                "Trying portal connection using SSL context: %s",
                context_name
            )

            with urllib.request.urlopen(
                request,
                timeout=REQUEST_TIMEOUT,
                context=context
            ) as response:

                status_code = response.status

                if status_code != 200:
                    raise RuntimeError(
                        "PORTAL_HTTP_STATUS_" + str(status_code)
                    )

                raw_data = response.read()

                encoding = response.headers.get_content_charset()

                if not encoding:
                    encoding = "utf-8"

                html = raw_data.decode(
                    encoding,
                    errors="replace"
                )

                logger.info(
                    "Portal connection successful using %s. "
                    "HTTP status: %s. Response size: %s bytes",
                    context_name,
                    status_code,
                    len(raw_data)
                )

                return html

        except Exception as error:

            last_error = error

            logger.exception(
                "Portal connection failed using SSL context: %s",
                context_name
            )

    logger.error(
        "All secure SSL connection attempts failed. Last error: %s",
        str(last_error)
    )

    raise RuntimeError(
        "SSL_CONNECTION_FAILED: " + str(last_error)
    )


# =========================================================
# FETCH PUBLIC TENDERS
# =========================================================

def fetch_public_tenders():

    html = download_portal_page()

    parser = AnnouncementHTMLParser()

    parser.feed(html)

    if not parser.rows:

        logger.error(
            "Portal response contains no recognizable HTML table rows"
        )

        raise RuntimeError(
            "PORTAL_HTML_HAS_NO_TABLE_ROWS"
        )

    logger.info(
        "HTML parser found %s table rows",
        len(parser.rows)
    )

    now = datetime.now(LOCAL_TZ)

    tenders = []

    for row in parser.rows:

        try:

            item = parse_announcement_row(row)

            if not item:
                continue

            end_date = parse_date(
                item.get("end_date")
            )

            if not end_date:
                continue

            if end_date <= now:
                continue

            tenders.append(item)

        except Exception:

            logger.exception(
                "Failed to parse one announcement row"
            )

    tenders.sort(
        key=lambda item: (
            parse_date(item.get("end_date"))
            or datetime.max.replace(tzinfo=LOCAL_TZ)
        )
    )

    result = {
        "ok": True,
        "configured": True,
        "items": tenders[:30],
        "count": len(tenders[:30]),
        "updated_at": datetime.now(LOCAL_TZ).isoformat(),
        "source": SOURCE_URL
    }

    logger.info(
        "Successfully processed %s active announcements",
        len(tenders)
    )

    return result


# =========================================================
# MAIN PAGE
# =========================================================

@app.route("/")
def index():

    return render_template("index.html")


# =========================================================
# TENDER API
# =========================================================

@app.route("/api/tenders", methods=["GET"])
def api_tenders():

    now = time.time()

    if (
        _cache["data"] is not None
        and now < _cache["expires"]
    ):

        cached = dict(_cache["data"])
        cached["cached"] = True

        return jsonify(cached)

    try:

        data = fetch_public_tenders()

        _cache["data"] = data
        _cache["expires"] = now + CACHE_SECONDS

        return jsonify(data), 200

    except Exception as error:

        logger.exception(
            "TENDER API: failed to load public announcements"
        )

        if _cache["data"] is not None:

            stale_data = dict(_cache["data"])

            stale_data["stale"] = True
            stale_data["warning"] = str(error)

            return jsonify(stale_data), 200

        return jsonify({
            "ok": False,
            "configured": True,
            "items": [],
            "count": 0,
            "message": (
                "Не удалось получить данные официального портала закупок."
            ),
            "details": str(error),
            "source": SOURCE_URL,
            "updated_at": datetime.now(LOCAL_TZ).isoformat()
        }), 502


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/healthz")
def healthz():

    return jsonify({
        "ok": True,
        "service": "Kzzakupbot Hub",
        "module": "TENDER LIVE",
        "time": datetime.now(LOCAL_TZ).isoformat()
    }), 200


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )
