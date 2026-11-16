
/* Kzzakupbot Hub
   Financial Cabinet MVP — interface controller
*/
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);

  const form = $("finDealForm");
  const calculateButton = $("finCalculate");
  const resetButton = $("finReset");

  if (!form || !calculateButton || !resetButton) {
    console.error(
      "[Financial Cabinet] Не найдена форма или кнопки. Проверьте HTML ID."
    );
    return;
  }

  if (
    !window.KzzFinancialModel ||
    typeof window.KzzFinancialModel.calculateDeal !== "function"
  ) {
    showError("Расчётная модель не загружена. Проверьте financial-model.js.");
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

    Object.entries(fields).forEach(([key, id]) => {
      const element = $(id);

      if (!element) {
        throw new Error("Не найдено поле #" + id);
      }

      data[key] = element.value === "" ? 0 : element.value;
    });

    return data;
  }

  function money(value) {
    return new Intl.NumberFormat("ru-RU", {
      maximumFractionDigits: 0
    }).format(Math.round(Number(value) || 0)) + " ₸";
  }

  function setValue(id, value) {
    const element = $(id);
    if (element) element.textContent = value;
  }

  function showError(message) {
    const error = $("finError");

    if (error) {
      error.textContent = message;
      error.hidden = false;
      error.style.display = "block";
    } else {
      console.error("[Financial Cabinet]", message);
    }
  }

  function clearError() {
    const error = $("finError");

    if (error) {
      error.textContent = "";
      error.hidden = true;
      error.style.display = "none";
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
    if (!table) return;

    if (!schedule.length) {
      table.innerHTML =
        '<tr><td colspan="6">Нет операций для отображения</td></tr>';
      return;
    }

    table.innerHTML = schedule.map(function (item) {
      return `
        <tr>
          <td>${item.day}</td>
          <td>${escapeHTML(item.operations)}</td>
          <td>${money(item.income)}</td>
          <td>${money(item.expense)}</td>
          <td>${money(item.debt)}</td>
          <td>${money(item.cash)}</td>
        </tr>
      `;
    }).join("");
  }

  function renderResult(result) {
    setValue("finKpiFunding", money(result.peakDebt));
    setValue("finKpiDebt", money(result.peakDebt));
    setValue("finKpiCost", money(result.financingCost));
    setValue("finKpiProfit", money(result.netProfit));

    setValue("finKpiOperating", money(result.operatingProfit));
    setValue("finKpiMargin", result.margin.toFixed(2) + "%");
    setValue("finKpiInterest", money(result.interest));
    setValue("finKpiFee", money(result.bankFee));

    renderSchedule(result.schedule);

    setValue(
      "finAssumptions",
      "Расчёт является планировочной моделью. " +
      "Проценты начисляются на фактический долг по дням. " +
      "Налоги, НДС и банковские ограничения не включены."
    );

    const resultBlock = $("finResult");

    if (resultBlock) {
      resultBlock.hidden = false;
      resultBlock.style.display = "";
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
        "[Financial Cabinet] Расчёт выполнен успешно.",
        result
      );

    } catch (error) {
      showError(
        error && error.message
          ? error.message
          : "Ошибка при выполнении расчёта."
      );

      console.error("[Financial Cabinet]", error);
    }
  }

  // Обработка нажатия кнопки.
  calculateButton.addEventListener("click", function (event) {
    event.preventDefault();

    if (calculateButton.type === "submit") {
      return;
    }

    calculate();
  });

  // Поддержка отправки формы клавишей Enter.
  form.addEventListener("submit", function (event) {
    event.preventDefault();
    calculate();
  });

  // Сброс формы и результатов.
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
      setValue(id, "—");
    });

    const table = $("finSchedule");

    if (table) {
      table.innerHTML = "";
    }

    setValue("finAssumptions", "");

    console.info("[Financial Cabinet] Форма сброшена.");
  });

  console.info("[Financial Cabinet] Модуль интерфейса инициализирован.");

})();
