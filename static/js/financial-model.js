
/* Kzzakupbot Hub
   Financial Cabinet MVP — calculation engine
*/
(function (global) {
  "use strict";

  const DAYS_IN_YEAR = 365;

  function toNumber(value, name) {
    const number = Number(value ?? 0);

    if (!Number.isFinite(number) || number < 0) {
      throw new Error(name + ": некорректное значение.");
    }

    return number;
  }

  function toDay(value, name) {
    const day = toNumber(value, name);

    if (!Number.isInteger(day)) {
      throw new Error(name + ": укажите целое число дней.");
    }

    return day;
  }

  function calculateDeal(input) {
    const contract = toNumber(input.contractAmount, "Цена контракта");
    const purchase = toNumber(input.purchaseCost, "Закупка");
    const logistics = toNumber(input.logisticsCost, "Логистика");
    const other = toNumber(input.otherCost, "Прочие расходы");
    const ownFunds = toNumber(input.ownFunds, "Собственные средства");
    const openingBalance = toNumber(
      input.startingBalance,
      "Начальный остаток"
    );

    const advancePercent = toNumber(
      input.advancePercent,
      "Аванс"
    );

    const annualRate = toNumber(
      input.annualRate,
      "Годовая ставка"
    );

    const feePercent = toNumber(
      input.feePercent,
      "Комиссия"
    );

    if (advancePercent > 100 || feePercent > 100) {
      throw new Error("Процент не может превышать 100%.");
    }

    const advanceDay = toDay(input.advanceDay, "День аванса");
    const purchaseDay = toDay(input.purchaseDay, "День закупки");
    const logisticsDay = toDay(input.logisticsDay, "День логистики");
    const otherDay = toDay(input.otherDay, "День прочих расходов");
    const paymentDay = toDay(input.paymentDay, "День оплаты");

    if (paymentDay < advanceDay ||
        paymentDay < purchaseDay ||
        paymentDay < logisticsDay ||
        paymentDay < otherDay) {
      throw new Error(
        "День окончательной оплаты не может быть раньше операций."
      );
    }

    const events = new Map();

    function addEvent(day, income, expense, title) {
      const event = events.get(day) || {
        day,
        income: 0,
        expense: 0,
        operations: []
      };

      event.income += income;
      event.expense += expense;
      event.operations.push(title);

      events.set(day, event);
    }

    if (advancePercent > 0) {
      addEvent(
        advanceDay,
        contract * advancePercent / 100,
        0,
        "Аванс заказчика"
      );
    }

    addEvent(purchaseDay, 0, purchase, "Закупка");
    addEvent(logisticsDay, 0, logistics, "Логистика");
    addEvent(otherDay, 0, other, "Прочие расходы");

    addEvent(
      paymentDay,
      contract * (1 - advancePercent / 100),
      0,
      "Окончательная оплата"
    );

    const days = [...events.keys()].sort((a, b) => a - b);

    let cash = openingBalance + ownFunds;
    let debt = 0;
    let peakDebt = 0;
    let interest = 0;
    let previousDay = 0;

    const schedule = [];

    for (const day of days) {
      const elapsedDays = day - previousDay;

      interest +=
        debt * (annualRate / 100) *
        elapsedDays / DAYS_IN_YEAR;

      const event = events.get(day);

      cash += event.income - event.expense;

      if (cash < 0) {
        debt += Math.abs(cash);
        cash = 0;
      } else if (debt > 0) {
        const repayment = Math.min(cash, debt);
        debt -= repayment;
        cash -= repayment;
      }

      peakDebt = Math.max(peakDebt, debt);

      schedule.push({
        day,
        operations: event.operations.join(", "),
        income: round(event.income),
        expense: round(event.expense),
        debt: round(debt),
        cash: round(cash)
      });

      previousDay = day;
    }

    const operatingProfit =
      contract - purchase - logistics - other;

    const bankFee = peakDebt * feePercent / 100;
    const financingCost = interest + bankFee;
    const netProfit = operatingProfit - financingCost;

    return {
      contractAmount: round(contract),
      totalCosts: round(purchase + logistics + other),
      operatingProfit: round(operatingProfit),
      peakDebt: round(peakDebt),
      interest: round(interest),
      bankFee: round(bankFee),
      financingCost: round(financingCost),
      netProfit: round(netProfit),
      margin: contract > 0
        ? round(netProfit / contract * 100)
        : 0,
      schedule
    };
  }

  function round(value) {
    return Math.round((value + Number.EPSILON) * 100) / 100;
  }

  global.KzzFinancialModel = {
    calculateDeal
  };

})(typeof window !== "undefined" ? window : globalThis);
