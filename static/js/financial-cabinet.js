(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const fmt = v => new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 }).format(Math.round(v)) + ' ₸';
  const fields = ['contractAmount','purchaseCost','logisticsCost','otherCost','ownFunds','advancePercent','advanceDay','purchaseDay','logisticsDay','otherDay','paymentDay','annualRate','feePercent','startingBalance'];
  function values() { const o = {}; fields.forEach(k => o[k] = $(k).value); return o; }
  function render() {
    const error = $('error'); error.textContent = '';
    try {
      const r = KzzFinancialModel.calculate(values());
      $('kpiFunding').textContent = fmt(r.peakFundingNeed);
      $('kpiDebt').textContent = fmt(r.peakDebt);
      $('kpiCost').textContent = fmt(r.totalFinancing);
      $('kpiProfit').textContent = fmt(r.netProfit);
      $('kpiMargin').textContent = r.marginPercent.toFixed(2).replace('.', ',') + '%';
      $('kpiInterest').textContent = fmt(r.interestCost);
      $('kpiFee').textContent = fmt(r.financingFee);
      $('kpiOperating').textContent = fmt(r.operatingProfit);
      $('schedule').innerHTML = r.rows.map(row => `<tr><td>${row.day}</td><td>${row.events.length ? row.events.join('; ') : '—'}</td><td>${row.incoming ? fmt(row.incoming) : '—'}</td><td>${row.outgoing ? fmt(row.outgoing) : '—'}</td><td>${fmt(row.balance)}</td><td>${row.deficit ? fmt(row.deficit) : '—'}</td></tr>`).join('');
      $('result').hidden = false;
      $('assumptions').textContent = `Учтено ${r.rows.length} календарных дней. Проценты рассчитаны по ежедневному остатку привлечённого долга по простой годовой ставке 365 дней; комиссия начислена один раз на максимальную задолженность. Налоги, НДС, банковские гарантии, задержки приёмки и изменение цены не включены.`;
    } catch (e) {
      $('result').hidden = true;
      error.textContent = e.message || 'Не удалось выполнить расчёт';
    }
  }
  $('reset').addEventListener('click', () => { $('dealForm').reset(); render(); });
  $('dealForm').addEventListener('submit', e => { e.preventDefault(); render(); });
  render();
})();
