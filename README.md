# Kzzakupbot Hub

Flask-сайт: закупки РК, тендерный калькулятор, банки и гарантии, академия поставщика (каталог 20 источников, без цен).

Структура: `app.py` (маршрут `/`), `templates/index.html`, `static/css/style.css`, `static/js/main.js`.

Локально: `pip install -r requirements.txt && python app.py` (http://localhost:5000).
Render: Blueprint из `render.yaml` или Web Service, Build `pip install -r requirements.txt`, Start `gunicorn app:app`.
