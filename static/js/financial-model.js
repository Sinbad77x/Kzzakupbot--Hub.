
/* Kzzakupbot Hub
   Financial Cabinet MVP
   Calculation engine v1.1
*/
(function (global) {
  "use strict";

  const DAYS_IN_YEAR = 365;

  function toNumber(value, name) {
    const n = Number(value);

    if (!Number.isFinite(n) || n < 0) {
      throw new Error(name + ": укажите корректное неотрицательное число.");
    }

    return n;
  }

  function toDay(value, name) {
    const n = toNumber(value, name);

    if (!Number.isInteger(n)) {
      throw new Error(name + ": укажите целое число дней.");
    }

    return n;
  }

  function round(value) {
    return Math.round((value + Number.EPSILON) * 100) / 100;
  }

  function calculateDeal(input) {
    input = input || {};

    const contract = toNumber(input.contractAmount, "Цена контракта");
    const purchase = toNumber(input.purchaseCost, "Закупка");
    const logistics = toNumber(input.logisticsCost || 0, "Логистика");
    const other = toNumber(input.otherCost || 0, "Прочие расходы");

    const ownFunds = toNumber(input.ownFunds || 0, "Собственные средства");
    const openingBalance = toNumber(
      input.startingBalance || 0,
      "Начальный остаток"
    );

    const advancePercent = toNumber(
      input.advancePercent || 0,
      "Аванс"
    );

    const annualRate = toNumber(
      input.annualRate || 0,
      "Годовая ставка"
    );

    const feePercent = toNumber(
      input.feePercent || 0,
      "Комиссия"
    );

    if (contract <= 0) {
      throw new Error("Цена контракта должна быть больше нуля.");
    }

    if (advancePercent > 100 || feePercent > 100) {
      throw new Error("Процент не может превышать 100.");
    }

    const advanceDay = toDay(input.advanceDay || 0, "День аванса");
    const purchaseDay = toDay(input.purchaseDay || 0, "День закупки");
    const logisticsDay = toDay(input.logisticsDay || 0, "День логистики");
    const otherDay = toDay(input.otherDay || 0, "День прочих расходов");
    const paymentDay = toDay(input.paymentDay || 0, "День окончательной оплаты");

    if (
      advanceDay > paymentDay ||
      purchaseDay > paymentDay ||
      logisticsDay > paymentDay ||
      otherDay > paymentDay
    ) {
      throw new Error(
        "Окончательная оплата не может быть раньше остальных операций."
      );
    }

    const events = new Map();

    function addEvent(day, income, expense, title) {
      const event = events.get(day) || {
        day: day,
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

    const days = Array.from(events.keys()).sort((a, b) => a - b);

    let cash = openingBalance + ownFunds;
    let debt = 0;
    let peakDebt = 0;
    let interest = 0;
    let previousDay = 0;

    const schedule = [];

    for (const day of days) {
      const elapsedDays = day - previousDay;

      interest += debt * annualRate / 100 *
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
        day: day,
        operations: event.operations.join(", "),
        income: round(event.income),
        expense: round(event.expense),
        cash: round(cash),
        debt: round(debt)
      });

      previousDay = day;
    }

    const totalCosts = purchase + logistics + other;
    const operatingProfit = contract - totalCosts;

    const bankFee = peakDebt * feePercent / 100;
    const financingCost = interest + bankFee;
    const netProfit = operatingProfit - financingCost;

    return {
      contractAmount: round(contract),
      totalCosts: round(totalCosts),
      operatingProfit: round(operatingProfit),
      peakDebt: round(peakDebt),
      interest: round(interest),
      bankFee: round(bankFee),
      financingCost: round(financingCost),
      netProfit: round(netProfit),
      margin: round(netProfit / contract * 100),
      schedule: schedule
    };
  }

  global.KzzFinancialModel = {
    calculateDeal: calculateDeal
  };

})(typeof window !== "undefined" ? window : globalThis);
