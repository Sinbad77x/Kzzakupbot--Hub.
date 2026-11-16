/* Kzzakupbot Financial Cabinet — pure calculation model (KZT, integer tenge). */
(function (root) {
  'use strict';
  const n = (v, name) => {
    const x = Number(v);
    if (!Number.isFinite(x)) throw new Error(`${name}: укажите корректное число`);
    return x;
  };
  const nonNegative = (v, name) => {
    const x = n(v, name);
    if (x < 0) throw new Error(`${name}: значение не может быть отрицательным`);
    return x;
  };
  const valueOr = (input, key, fallback) => input[key] === undefined || input[key] === null || input[key] === '' ? fallback : input[key];
  function calculate(input) {
    const contract = nonNegative(input.contractAmount, 'Цена контракта');
    if (contract <= 0) throw new Error('Цена контракта должна быть больше нуля');
    const cost = nonNegative(input.purchaseCost, 'Закупочная стоимость');
    const logistics = nonNegative(valueOr(input, 'logisticsCost', 0), 'Логистика');
    const other = nonNegative(valueOr(input, 'otherCost', 0), 'Прочие расходы');
    const own = nonNegative(valueOr(input, 'ownFunds', 0), 'Собственные средства');
    const advancePct = n(valueOr(input, 'advancePercent', 0), 'Аванс');
    const advanceDay = Math.floor(nonNegative(valueOr(input, 'advanceDay', 0), 'День аванса'));
    const purchaseDay = Math.floor(nonNegative(valueOr(input, 'purchaseDay', 1), 'День закупки'));
    const logisticsDay = Math.floor(nonNegative(valueOr(input, 'logisticsDay', 1), 'День логистики'));
    const otherDay = Math.floor(nonNegative(valueOr(input, 'otherDay', 1), 'День прочих расходов'));
    const paymentDay = Math.floor(nonNegative(valueOr(input, 'paymentDay', 30), 'День окончательной оплаты'));
    const annualRate = nonNegative(valueOr(input, 'annualRate', 0), 'Годовая ставка');
    const feePct = nonNegative(valueOr(input, 'feePercent', 0), 'Комиссия за финансирование');
    const startBalance = n(valueOr(input, 'startingBalance', 0), 'Начальный остаток');
    if (advancePct > 100) throw new Error('Аванс: максимум 100%');
    if (annualRate > 1000 || feePct > 100) throw new Error('Проверьте процентную ставку или комиссию');
    if ([advanceDay, purchaseDay, logisticsDay, otherDay, paymentDay].some(day => day > 3650)) throw new Error('Срок сделки не должен превышать 10 лет в этой версии');
    if (paymentDay < advanceDay || paymentDay < purchaseDay || paymentDay < logisticsDay || paymentDay < otherDay) {
      throw new Error('День окончательной оплаты не может быть раньше указанных расходов или аванса');
    }
    const events = new Map();
    const add = (day, amount, label, type) => {
      const d = Math.floor(day);
      if (!events.has(d)) events.set(d, []);
      events.get(d).push({ amount, label, type });
    };
    if (advancePct > 0) add(advanceDay, contract * advancePct / 100, 'Аванс заказчика', 'in');
    add(purchaseDay, -cost, 'Закупка товара / материалов', 'out');
    if (logistics) add(logisticsDay, -logistics, 'Логистика', 'out');
    if (other) add(otherDay, -other, 'Прочие расходы', 'out');
    add(paymentDay, contract * (1 - advancePct / 100), 'Окончательный расчёт заказчика', 'in');

    const lastDay = Math.max(...events.keys(), 0);
    let balance = startBalance + own;
    let peakDeficit = 0;
    let peakDebt = 0;
    let debt = 0;
    let interest = 0;
    let cumulativeIn = 0;
    let cumulativeOut = 0;
    const rows = [];
    for (let day = 0; day <= lastDay; day++) {
      // Interest accrues on the debt outstanding during the preceding day.
      if (day > 0 && debt > 0) interest += debt * annualRate / 100 / 365;
      const dayEvents = events.get(day) || [];
      let dayIn = 0, dayOut = 0;
      for (const e of dayEvents) {
        if (e.amount >= 0) dayIn += e.amount;
        else dayOut += -e.amount;
      }
      balance += dayIn - dayOut;
      cumulativeIn += dayIn;
      cumulativeOut += dayOut;
      const deficit = Math.max(0, -balance);
      peakDeficit = Math.max(peakDeficit, deficit);
      debt = deficit;
      peakDebt = Math.max(peakDebt, debt);
      rows.push({ day, incoming: dayIn, outgoing: dayOut, net: dayIn - dayOut,
        balance, deficit, debt, events: dayEvents.map(e => e.label) });
    }
    const financingFee = peakDebt > 0 ? peakDebt * feePct / 100 : 0;
    const totalFinancing = interest + financingFee;
    const operatingProfit = contract - cost - logistics - other;
    const netProfit = operatingProfit - totalFinancing;
    const margin = contract > 0 ? netProfit / contract * 100 : 0;
    return {
      contractAmount: contract, totalCosts: cost + logistics + other,
      operatingProfit, ownFunds: own, peakFundingNeed: peakDeficit,
      peakDebt, interestCost: interest, financingFee, totalFinancing,
      netProfit, marginPercent: margin, finalCashBalance: balance - interest - financingFee,
      totalIncoming: cumulativeIn, totalOutgoing: cumulativeOut, rows
    };
  }
  const api = { calculate };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.KzzFinancialModel = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
