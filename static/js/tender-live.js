
(() => {
    "use strict";

    const container = document.getElementById("tenderLiveItems");
    const status = document.getElementById("tenderLiveStatus");
    const refreshButton = document.getElementById("tenderLiveRefresh");
    const updatedLabel = document.getElementById("tenderLiveUpdated");

    if (!container || !status || !refreshButton) {
        return;
    }

    const API_URL = "/api/tenders";
    const REFRESH_INTERVAL = 15 * 60 * 1000;

    let loading = false;

    function formatMoney(value) {
        const number = Number(value);

        if (!Number.isFinite(number)) {
            return "Сумма не указана";
        }

        return new Intl.NumberFormat("ru-RU", {
            maximumFractionDigits: 2
        }).format(number) + " ₸";
    }

    function formatDate(value) {
        if (!value) {
            return "Не указана";
        }

        const date = new Date(
            String(value).replace(" ", "T")
        );

        if (Number.isNaN(date.getTime())) {
            return String(value);
        }

        return new Intl.DateTimeFormat("ru-RU", {
            dateStyle: "short",
            timeStyle: "short",
            timeZone: "Asia/Almaty"
        }).format(date);
    }

    function createElement(tag, className, value) {
        const element = document.createElement(tag);

        if (className) {
            element.className = className;
        }

        if (value !== undefined && value !== null) {
            element.textContent = String(value);
        }

        return element;
    }

    function createDetail(label, value) {
        const line = createElement("div", "tender-detail");

        const title = createElement(
            "strong",
            "",
            label + ": "
        );

        const content = document.createTextNode(
            value || "Не указано"
        );

        line.appendChild(title);
        line.appendChild(content);

        return line;
    }

    function createCard(item) {
        const card = createElement("article", "tender-card");

        card.appendChild(
            createElement(
                "div",
                "tender-card-number",
                "Объявление № " + (item.number || item.id)
            )
        );

        card.appendChild(
            createElement(
                "h3",
                "",
                item.name || "Название не указано"
            )
        );

        card.appendChild(
            createElement(
                "div",
                "tender-card-amount",
                formatMoney(item.amount)
            )
        );

        const details = createElement(
            "div",
            "tender-card-details"
        );

        details.appendChild(
            createDetail("Организатор", item.organizer)
        );

        details.appendChild(
            createDetail("Способ закупки", item.method)
        );

        details.appendChild(
            createDetail("Начало приёма", formatDate(item.start_date))
        );

        details.appendChild(
            createDetail("Окончание приёма", formatDate(item.end_date))
        );

        details.appendChild(
            createDetail("Статус", item.status)
        );

        card.appendChild(details);

        if (item.url) {
            const link = createElement(
                "a",
                "tender-card-link",
                "Открыть объявление на портале"
            );

            link.href = item.url;
            link.target = "_blank";
            link.rel = "noopener noreferrer";

            card.appendChild(link);
        }

        return card;
    }

    function renderItems(items) {
        container.replaceChildren();

        if (!Array.isArray(items) || items.length === 0) {
            container.appendChild(
                createElement(
                    "div",
                    "tender-live-empty",
                    "На загруженной странице не найдено объявлений с действующим сроком подачи заявок."
                )
            );

            return;
        }

        const fragment = document.createDocumentFragment();

        items.forEach(item => {
            fragment.appendChild(createCard(item));
        });

        container.appendChild(fragment);
    }

    async function loadTenders() {
        if (loading) {
            return;
        }

        loading = true;
        refreshButton.disabled = true;

        status.textContent =
            "Загружаем объявления с официального портала...";

        try {
            const response = await fetch(API_URL, {
                method: "GET",
                headers: {
                    "Accept": "application/json"
                },
                cache: "no-store"
            });

            const data = await response.json();

            if (!response.ok || !data.ok) {
                throw new Error(
                    data.message || "Ошибка загрузки объявлений."
                );
            }

            renderItems(data.items);

            if (data.stale) {
                status.textContent =
                    "Показаны ранее загруженные данные. " +
                    (data.warning || "Портал временно недоступен.");
            } else {
                status.textContent =
                    "Источник: официальная Единая платформа " +
                    "государственных закупок РК. " +
                    "Найдено объявлений: " + (data.count || 0) + ".";
            }

            if (updatedLabel) {
                updatedLabel.textContent =
                    "Обновлено: " + formatDate(data.updated_at);
            }

        } catch (error) {
            console.error("TENDER LIVE:", error);

            status.textContent = error.message;

            container.replaceChildren();

            container.appendChild(
                createElement(
                    "div",
                    "tender-live-empty",
                    "Не удалось загрузить данные. " +
                    "Проверьте журнал Render. " +
                    "Демонстрационные объявления не используются."
                )
            );

            if (updatedLabel) {
                updatedLabel.textContent = "";
            }

        } finally {
            loading = false;
            refreshButton.disabled = false;
        }
    }

    refreshButton.addEventListener(
        "click",
        loadTenders
    );

    loadTenders();

    window.setInterval(
        loadTenders,
        REFRESH_INTERVAL
    );
})();
