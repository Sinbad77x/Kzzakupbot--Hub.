
import os
import json
import time
import logging
import urllib.request
import urllib.error

from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask, render_template, jsonify

app = Flask(__name__)

API_URL = "https://ows.goszakup.gov.kz/v3/graphql"
LOCAL_TZ = ZoneInfo("Asia/Almaty")
CACHE_SECONDS = 300

logging.basicConfig(level=logging.INFO)

_cache = {
    "expires": 0,
    "data": None
}


def parse_date(value):
    if not value:
        return None

    try:
        result = datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        )

        if result.tzinfo is None:
            result = result.replace(tzinfo=LOCAL_TZ)

        return result.astimezone(LOCAL_TZ)

    except (ValueError, TypeError):
        return None


def fetch_tenders():
    token = os.environ.get("GOSZAKUP_API_TOKEN", "").strip()

    if not token:
        raise RuntimeError("API_TOKEN_NOT_CONFIGURED")

    query = """
    query(
        $limit: Int,
        $after: Int,
        $filter: TrdBuyFiltersInput
    ) {
        TrdBuy(
            limit: $limit,
            after: $after,
            filter: $filter
        ) {
            id
            numberAnno
            nameRu
            nameKz
            totalSum
            publishDate
            startDate
            endDate
            refBuyStatusId
            orgBin
            orgNameRu
            customerNameRu
            systemId
        }
    }
    """

    payload = {
        "operationName": None,
        "query": query,
        "variables": {
            "limit": 100,
            "after": None,
            "filter": {
                "refBuyStatusId": [210, 220]
            }
        }
    }

    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + token
        },
        method="POST"
    )

    with urllib.request.urlopen(request, timeout=25) as response:
        result = json.loads(
            response.read().decode("utf-8")
        )

    if result.get("errors"):
        logging.error("GraphQL errors: %s", result["errors"])
        raise RuntimeError("GOSZAKUP_GRAPHQL_ERROR")

    raw_items = (
        result.get("data", {}).get("TrdBuy") or []
    )

    now = datetime.now(LOCAL_TZ)
    tenders = []

    for item in raw_items:
        end_date = parse_date(item.get("endDate"))

        if end_date and end_date <= now:
            continue

        tender_id = item.get("id")

        if not tender_id:
            continue

        name = (
            item.get("nameRu")
            or item.get("nameKz")
            or "Название не указано"
        )

        tenders.append({
            "id": tender_id,
            "number": item.get("numberAnno") or str(tender_id),
            "name": name,
            "amount": item.get("totalSum"),
            "published": item.get("publishDate"),
            "start_date": item.get("startDate"),
            "end_date": item.get("endDate"),
            "organizer": (
                item.get("orgNameRu")
                or item.get("customerNameRu")
                or "Организатор не указан"
            ),
            "bin": item.get("orgBin"),
            "status_id": item.get("refBuyStatusId"),
            "source": "Государственные закупки РК",
            "url": (
                "https://www.goszakup.gov.kz/ru/announce/index/"
                + str(tender_id)
            )
        })

    tenders.sort(
        key=lambda item: (
            parse_date(item.get("published"))
            or datetime.min.replace(tzinfo=LOCAL_TZ)
        ),
        reverse=True
    )

    return {
        "ok": True,
        "items": tenders[:30],
        "updated_at": datetime.now(LOCAL_TZ).isoformat(),
        "source": "Официальный портал государственных закупок"
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/tenders")
def api_tenders():
    now = time.time()

    if _cache["data"] and now < _cache["expires"]:
        return jsonify(_cache["data"])

    if not os.environ.get("GOSZAKUP_API_TOKEN", "").strip():
        return jsonify({
            "ok": False,
            "configured": False,
            "message": "Не настроен API-токен государственных закупок."
        }), 503

    try:
        data = fetch_tenders()

        _cache["data"] = data
        _cache["expires"] = now + CACHE_SECONDS

        return jsonify(data)

    except Exception:
        logging.exception("Ошибка загрузки государственных закупок")

        if _cache["data"]:
            stale_data = dict(_cache["data"])
            stale_data["stale"] = True
            return jsonify(stale_data)

        return jsonify({
            "ok": False,
            "message": "Не удалось получить данные портала. Проверьте API-токен и журнал Render."
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
    
