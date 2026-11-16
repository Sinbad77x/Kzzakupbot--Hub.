
/* Kzzakupbot Hub
   Financial Cabinet MVP
   Interface controller v1.1
*/
(function () {
  "use strict";

  const $ = function (id) {
    return document.getElementById(id);
  };

  const form = $("finDealForm");
  const calculateButton = $("finCalculate");
  const resetButton = $("finReset");

  if (!form || !calculateButton || !resetButton) {
    console.error("[Financial Cabinet] Не найдена форма или кнопки.");
    return;
  }

  if (
    !window.KzzFinancialModel ||
    typeof window.KzzFinancialModel.calculateDeal !== "function"
  ) {
    showError("Не загружена расчётная модель financial-model.js.");
    calculateButton.disabled = true;
    return;
  }

  const fields = {
    contractAmount: "finContractAmount",
    purchaseCost: "finPurchaseCost",
    logisticsCost: "finLogisticsCost",
    otherCost: "finOtherCost",
    ownFunds: "finOwnFunds",
    startingBalance: "finStartingBalance",
    advancePercent: "finAdvancePercent",
    advanceDay: "finAdvanceDay",
    purchaseDay: "finPurchaseDay",
    logisticsDay: "finLogisticsDay",
    otherDay: "finOtherDay",
    paymentDay: "finPaymentDay",
    annualRate: "finAnnualRate",
    feePercent: "finFeePercent"
  };

  function readForm() {
    const data = {};

    Object.keys(fields).forEach(function (key) {
      const element = $(fields[key]);

      if (!element) {
        throw new Error("Не найдено поле: " + fields[key]);
      }

      data[key] = element.value;
    });

    return data;
  }

  function money(value) {
    return new Intl.NumberFormat("ru-RU", {
      maximumFractionDigits: 0
    }).format(Math.round(Number(value) || 0)) + " ₸";
  }

  function setText(id, value) {
    const element = $(id);

    if (element) {
      element.textContent = value;
    }
  }

  function showError(message) {
    const element = $("finError");

    if (element) {
      element.textContent = message;
      element.hidden = false;
      element.style.display = "block";
    }

    console.error("[Financial Cabinet]", message);
  }

  function clearError() {
    const element = $("finError");

    if (element) {
      element.textContent = "";
      element.hidden = true;
      element.style.display = "none";
    }
  }

  function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, function (char) {
      return {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }[char];
    });
  }

  function renderSchedule(schedule) {
    const table = $("finSchedule");

    if (!table) {
      throw new Error("Не найдена таблица #finSchedule.");
    }

    if (!schedule.length) {
      table.innerHTML =
        '<tr><td colspan="6">Нет операций для отображения</td></tr>';
      return;
    }

    table.innerHTML = schedule.map(function (item) {
      return (
        "<tr>" +
          "<td>" + item.day + "</td>" +
          "<td>" + escapeHTML(item.operations) + "</td>" +
          "<td>" + money(item.income) + "</td>" +
          "<td>" + money(item.expense) + "</td>" +
          "<td>" + money(item.cash) + "</td>" +
          "<td>" + money(item.debt) + "</td>" +
        "</tr>"
      );
    }).join("");
  }

  function renderResult(result) {
    setText("finKpiFunding", money(result.peakDebt));
    setText("finKpiDebt", money(result.peakDebt));
    setText("finKpiCost", money(result.financingCost));
    setText("finKpiProfit", money(result.netProfit));

    setText("finKpiOperating", money(result.operatingProfit));
    setText("finKpiMargin", result.margin.toFixed(2) + "%");
    setText("finKpiInterest", money(result.interest));
    setText("finKpiFee", money(result.bankFee));

    renderSchedule(result.schedule);

    setText(
      "finAssumptions",
      "Модель учитывает поступления и расходы по дням. " +
      "Проценты начисляются на остаток долга по ставке годовых / 365. " +
      "Комиссия рассчитывается от максимального долга."
    );

    const resultBlock = $("finResult");

    if (resultBlock) {
      resultBlock.hidden = false;
      resultBlock.style.display = "block";
    }
  }

  function calculate() {
    clearError();

    try {
      const input = readForm();

      const result =
        window.KzzFinancialModel.calculateDeal(input);

      renderResult(result);

      console.info(
        "[Financial Cabinet] Расчёт выполнен.",
        result
      );

    } catch (error) {
      showError(
        error && error.message
          ? error.message
          : "Ошибка выполнения расчёта."
      );
    }
  }

  // Кнопка запускает расчёт напрямую.
  calculateButton.addEventListener("click", function (event) {
    event.preventDefault();
    calculate();
  });

  // Поддержка отправки формы клавишей Enter.
  form.addEventListener("submit", function (event) {
    event.preventDefault();
    calculate();
  });

  // Сброс результатов.
  resetButton.addEventListener("click", function (event) {
    event.preventDefault();

    form.reset();
    clearError();

    const resultBlock = $("finResult");

    if (resultBlock) {
      resultBlock.hidden = true;
      resultBlock.style.display = "none";
    }

    [
      "finKpiFunding",
      "finKpiDebt",
      "finKpiCost",
      "finKpiProfit",
      "finKpiOperating",
      "finKpiMargin",
      "finKpiInterest",
      "finKpiFee"
    ].forEach(function (id) {
      setText(id, "—");
    });

    const table = $("finSchedule");

    if (table) {
      table.innerHTML = "";
    }

    setText("finAssumptions", "");

    console.info("[Financial Cabinet] Данные сброшены.");
  });

  console.info("[Financial Cabinet] Модуль успешно подключён.");

})();
