(function(){
var $=function(i){return document.getElementById(i)};
var f=function(n){return Math.round(n).toLocaleString('ru-RU').replace(/\u00a0/g,' ')+' ₸'};
function num(id){var v=Number($(id).value);return Number.isFinite(v)?v:0}
function showMode(){
var t=$('tax').value;
$('snrFields').hidden=t!=='snr';
$('generalFields').hidden=t==='snr';
$('vatFields').hidden=t!=='vat';
}
function setLegalFormRate(){
$('incomeRate').value=$('legalForm').value==='ip'?'10':'20';
}
function calc(){
var cost=num('cost'),mk=num('mk'),bid=num('bid'),ctr=num('ctr'),fee=num('fee'),minFee=num('minFee');
var t=$('tax').value,snrRate=num('snrRate'),incomeRate=num('incomeRate'),vatRate=num('vatRate'),inputVat=num('inputVat');
var vals=[cost,mk,bid,ctr,fee,minFee,snrRate,incomeRate,vatRate,inputVat];
if(vals.some(function(v){return v<0})||cost<=0||mk>10000||bid>100||ctr>100||fee>100||snrRate<2||snrRate>6||incomeRate>100||vatRate>100){
$('res').innerHTML='<b>Проверьте введённые значения</b><p class="mut">Себестоимость должна быть больше нуля; ставки и проценты должны находиться в допустимых пределах. Для СНР ставка — от 2% до 6%.</p>';
return;
}
var price=cost*(1+mk/100),gross=price-cost,incomeTax=0,outputVat=0,vatDue=0,taxLabel='',taxBase=price;
if(t==='snr'){
incomeTax=price*snrRate/100;
taxLabel='ИПН / КПН по СНР ('+snrRate.toFixed(1)+'% с дохода)';
}else{
taxBase=gross;
incomeTax=gross*incomeRate/100;
taxLabel='Оценка '+(incomeRate.toFixed(1))+'% КПН / ИПН с расчётной прибыли';
if(t==='vat'){
outputVat=price*vatRate/100;
vatDue=outputVat-inputVat;
}
}
var contractAmount=price+outputVat;
var gb=contractAmount*bid/100,gc=contractAmount*ctr/100,commissionByRate=(gb+gc)*fee/100,comm=(gb+gc)>0?Math.max(commissionByRate,minFee):0;
var net=gross-incomeTax-comm,margin=price?net/price*100:0;
var rows=[
['Цена предложения без НДС',f(price)],
['Валовая прибыль до налога',f(gross)],
[taxLabel,f(incomeTax)],
['Чистая прибыль после налога и расчётной комиссии',f(net),1],
['Итоговая маржа от цены без НДС',margin.toFixed(2)+'%',1]
];
if(t==='vat'){
rows.push(['Исходящий НДС ('+vatRate.toFixed(1)+'%)',f(outputVat)]);
rows.push(['Входящий НДС к зачёту',f(inputVat)]);
rows.push([vatDue>=0?'Расчётный НДС к уплате':'Превышение входящего НДС над исходящим',f(vatDue)]);
rows.push(['Цена предложения с НДС',f(contractAmount)]);
}
rows.push(['База для расчёта обеспечений',f(contractAmount)]);
rows.push(['Обеспечение заявки (сумма гарантии / блокировки)',f(gb)]);
rows.push(['Обеспечение исполнения договора (сумма гарантии / блокировки)',f(gc)]);
rows.push(['Расчётная комиссия банка (процент / минимум)',f(comm)]);
$('res').innerHTML='<b>Результаты расчёта</b>'+rows.map(function(r){return '<div class="row'+(r[2]?' hl':'')+'"><span>'+r[0]+'</span><b>'+r[1]+'</b></div>'}).join('');
}
$('tax').addEventListener('change',function(){showMode();calc()});
$('legalForm').addEventListener('change',function(){setLegalFormRate();calc()});
$('go').addEventListener('click',calc);
['cost','mk','snrRate','incomeRate','vatRate','inputVat','bid','ctr','fee','minFee'].forEach(function(id){$(id).addEventListener('input',calc)});
showMode();calc();
})();

(function(){
var D='14.11.2026',NE='Не уточняется на сайте';
var P=[];
function add(x){P.push(x)}
// --- AIFC Academy
var AI={o:'AIFC Academy',ty:'direct',dt:D,l:'ru',so:'open',st:'Доступна покупка на сайте; даты см. в расписании организатора'};
function A(n,c,d,au,fm,fk,dur,dh,cert,u){var x={n:n,c:c,d:d,a:au,fm:fm,fk:fk,dur:dur,dh:dh,cert:cert,u:u,k:'Подробнее о программе',r:u,rk:'Записаться (кнопка на странице)'};for(var k in AI)x[k]=AI[k];add(x)}
A('AI for Finance',[6],'ИИ в финансах: промпты, анализ договоров и МСФО, модели в Excel, SQL/Python через ИИ, дашборды.','Финансовые аналитики, FP&A, экономисты, казначеи, CFO',NE,[],'16 часов',16,NE,'https://academy.aifc.kz/product/ai-for-finance/');
A('Корпоративное право МФЦА',[3,4],'Источники права МФЦА, формы юрлиц, корпоративное управление, акционерные соглашения, структура капитала.','Юристы и специалисты, работающие с юрисдикцией МФЦА','Офлайн',['offline'],'8 часов',8,'Сертификат о прохождении обучения','https://academy.aifc.kz/product/korporativnoe-pravo-mftsa-2/');
A('Инвестиционные фонды МФЦА: юридические и налоговые аспекты',[6,3],'Правовой режим фондов МФЦА, виды фондов, налогообложение, листинг на бирже AIX.','Юристы, налоговые консультанты, инвесторы','Онлайн',['online'],'6 часов',6,'Электронный сертификат','https://academy.aifc.kz/product/investitsionnye-fondy-mftsa-klyuchevye-yuridicheskie-i-nalogovye-aspekty/');
A('Защита персональных данных',[4,3],'Регулирование данных в РК, МФЦА и ЕС (GDPR), права субъектов, утечки, трансграничная передача.','Юристы, комплаенс, руководители компаний','Онлайн',['online'],'4 часа',4,'Электронный сертификат','https://academy.aifc.kz/product/zashhita-personalnyh-dannyh/');
// --- Inside Business
var IB={o:'Inside Business (ТОО «INSIDE BUSINESS GROUP»)',ty:'direct',dt:D,c:[1,2],d:'Госзакупки, закупки Самрук-Қазына, недропользователей и MITWORK с практикой на порталах и кураторством.',a:'Предприниматели, тендерные специалисты, сотрудники компаний',dur:'2 месяца',dh:null,cert:'Сертификат о прохождении обучения',so:'open',st:'Заявка через форму на странице; даты групп не указаны',u:'https://inside-b.kz/obuchenie-dlja-postavshhikov',k:'Подробнее о программе',r:'https://inside-b.kz/obuchenie-dlja-postavshhikov',rk:'Записаться (форма на странице)'};
function I(n,fm,fk){var x={n:n,fm:fm,fk:fk};for(var k in IB)x[k]=IB[k];add(x)}
I('Поставщик online (5 практических курсов)','Онлайн в прямом эфире',['online']);
I('Поставщик offline (5 практических курсов)','Очно в аудитории',['offline']);
// --- Центр государственных закупок
add({n:'Особенности участия потенциальных поставщиков на основных площадках закупок в РК',o:'Центр государственных закупок (ТОО)',ty:'direct',c:[1,2],d:'Двухдневный семинар: госзакупки, портал Самрук-Қазына, ПКО, закупки недропользователей, другие площадки.',a:'Потенциальные поставщики',dur:'2 дня (10:00–17:00/18:00)',dh:null,fm:NE,fk:[],so:'unk',st:'Актуальность не подтверждена: описание ссылается на изменения 2019 года, подвал сайта датирован 2016–2019',dt:D,u:'https://zakupgov.kz/?page_id=241',k:'Подробнее о программе',r:'https://zakupgov.kz/?page_id=241',rk:'Записаться (кнопка на странице)'});
add({n:'Особенности проведения государственных закупок в электронном формате для Заказчиков/Организаторов',o:'Центр государственных закупок (ТОО)',ty:'direct',c:[1],d:'Семинар для заказчиков и организаторов; страница программы в этой проверке не открывалась.',so:'unk',st:'Актуальность не подтверждена',dt:D,u:'https://zakupgov.kz/?page_id=239',k:'Подробнее о программе'});
// --- Lider Edu
add({n:'Закупки Самрук-Қазына в 2026 году для поставщиков',o:'Lider Edu (учебный центр, Астана)',ty:'direct',c:[2,1],d:'13 модулей: порядок закупок Фонда, ПКО 2.0, электронный магазин SK Store, ЗЦП, тендерная заявка, условные скидки, исполнение договора.',a:'Поставщики, товаропроизводители, МСБ, ИП, тендерные специалисты',fm:'Офлайн / онлайн',fk:['online','offline'],dur:NE,dh:null,cert:NE,so:'open',st:'Заявка через WhatsApp или форму на странице; даты не указаны',dt:D,u:'https://lider-edu.kz/kursy/kursy-gosudarstvennykh-zakupok-v-astane/kursy-zakupki-samruk-k-azyna-v-2026-godu-dlya-postavshchikov-v-astane',k:'Подробнее о программе',r:'https://wa.me/77758168380',rk:'Записаться (WhatsApp)'});
// --- ВШЭ ИПБА
var HS={o:'ВШЭ ИПБА (Высшая школа экономики Институт профессиональных бухгалтеров и аудиторов)',ty:'direct',dt:D,fm:'Формат конкретной программы не указан (организатор проводит очно, онлайн и с выездом)',fk:[],so:'open',st:'Группы набираются по факту укомплектования; даты и город уточняются в расписании организатора',k:'Подробнее о программе'};
function H(n,c,d,dur,cert,u,more){var x={n:n,c:c,d:d,dur:dur,dh:null,cert:cert,u:u,r:u,rk:'Записаться (заявка на сайте)'};for(var k in HS)if(!(k in x))x[k]=HS[k];if(more)for(k in more)x[k]=more[k];add(x)}
H('Корпоративное право',[3,4],'Корпоративное управление и защита интересов компании, 5 модулей.','2 дня','Сертификат о повышении квалификации','https://hseipaa.kz/obuchenie/korp');
H('Договорное право',[3],'Договорные отношения и управление юридическими рисками, разбор кейсов.','2 дня семинара','Сертификат участника семинара','https://hseipaa.kz/obuchenie/dog-pravo');
H('Антикоррупционный комплаенс',[4],'Антикоррупционная система и работа комплаенс-службы.','Семинар (длительность не указана)','Сертификат участника семинара','https://hseipaa.kz/obuchenie/anticor');
H('Эффективный корпоративный секретарь. Практический курс',[4,3],'Организация корпоративного управления и работы органов компании.','По расписанию','Сертификат о прохождении обучения','https://hseipaa.kz/obuchenie/effektivnyy-korporativnyy-sekretar-prakticheskiy-kurs',{fm:'Онлайн и очно',fk:['online','offline']});
H('Государственные закупки',[1],'Программа числится в разделе «Закупки» каталога организатора; страница программы в этой проверке не открывалась.',null,null,'https://hseipaa.kz/obuchenie/gos-zakypki',{fm:null,st:'Статус набора не подтверждён',so:'unk'});
H('Инвестиции',[6],'Программа числится в разделе «Инвестиции» каталога организатора; страница программы в этой проверке не открывалась.',null,null,'https://hseipaa.kz/obuchenie/investing',{fm:null,st:'Статус набора не подтверждён',so:'unk'});
// --- Uchet.Академия
var UA={o:'Uchet.Академия (ТОО «ПРОФИТренинг»)',ty:'direct',dt:D,u:'https://academy.uchet.kz/catalog',k:'Перейти к курсам',so:'open',dur:NE,dh:null,cert:NE,fk:[]};
function U(n,c,d,fm,st){var x={n:n,c:c,d:d,fm:fm,st:st};for(var k in UA)x[k]=UA[k];add(x)}
U('Двухнедельный интенсив «PRO Налоги 2026»',[5],'Интенсив по налогам; программа в каталоге организатора.','Интенсив (по каталогу)','Старт 23 ноября (по каталогу)');
U('Школа по НДС: новые правила — новая практика',[5],'Программа по НДС в каталоге организатора.','Онлайн (по каталогу)','Отмечена как «Онлайн» в каталоге');
U('НДС: переход с 12% на 16%',[5],'Программа по изменению ставки НДС в каталоге организатора.','В записи (по каталогу)','Отмечена как «В записи» в каталоге');
U('Финансовый менеджмент: инвестиции, оборотный капитал и анализ результатов',[6],'Программа по финансовому менеджменту в каталоге организатора.','В записи (по каталогу)','Отмечена как «В записи» в каталоге');
// --- QAZAQ PROFI
var QP={o:'QAZAQ PROFI (учебный центр, Астана)',ty:'direct',dt:D,so:'open',cert:'Сертификат вручается по окончании (общее описание центра)',u:'https://www.qazaq-profi.kz/kurse.html',k:'Перейти к расписанию',r:'https://www.qazaq-profi.kz/kurse.html',rk:'Записаться (форма на странице)'};
function Q(n,c,d,fm,fk,dur,dh,st){var x={n:n,c:c,d:d,fm:fm,fk:fk,dur:dur,dh:dh,st:st};for(var k in QP)x[k]=QP[k];add(x)}
Q('Антикоррупционный комплаенс. Внутренний аудит коррупционных рисков',[4],'Семинар в расписании на ноябрь 2026.','Очно / дистанционно',['online','offline'],'12 акад. часов',12,'20–21.11.2026 (по расписанию на 14.11.2026)');
Q('Системные навыки современного корпоративного секретаря',[4,3],'Семинар в расписании на ноябрь 2026.','Очно / дистанционно',['online','offline'],'16 акад. часов',16,'19–20.11.2026 (по расписанию на 14.11.2026)');
Q('Противодействие легализации доходов и финансированию терроризма (ПОД/ФТ)',[4],'Семинар в расписании на ноябрь 2026.','Дистанционно',['online'],'16 акад. часов',16,'27–28.11.2026 (по расписанию на 14.11.2026)');
Q('Повышение квалификации профессиональных бухгалтеров (обязательные часы)',[5],'Курс в расписании на ноябрь 2026.','Очно / дистанционно',['online','offline'],'40 акад. часов',40,'18–20.11.2026 (по расписанию на 14.11.2026)');
// --- Skillbox KZ
add({n:'Финансы для предпринимателя',o:'Skillbox Казахстан (ТОО «Ньюскилз», эксклюзивный партнёр Skillbox)',ty:'direct',c:[7,6],d:'Финансовая отчётность, учёт денег и ДДС, налоги, юнит-экономика, финмодель и точка безубыточности; итоговая работа — аудит бизнеса.',a:'Предприниматели, руководители, будущие владельцы бизнеса',fm:'Онлайн-платформа: видео, задания, кураторы',fk:['online'],dur:'1 месяц, 11 тематических модулей',dh:null,cert:'Сертификат от Lerna',so:'open',st:'Старт 17 ноября (по данным страницы)',dt:D,note:'Часть модулей основана на законодательстве Российской Федерации (указано на странице). Эта же программа размещена в каталоге Lerna и здесь не дублируется.',u:'https://skillbox.kz/course/businessman-finance/',k:'Подробнее о программе',r:'https://skillbox.kz/course/businessman-finance/',rk:'Записаться (форма на странице)'});
// --- LERNA (aggregator)
add({n:'Каталог Lerna: Финансы',o:'LERNA.kz — агрегатор онлайн-курсов (ТОО «Ньюскилз»). Обучение проводят школы-партнёры, в тексте каталога они не названы',ty:'agg',c:[6,5],d:'Каталог из 59 онлайн-курсов по финансам и бухгалтерии разных школ. Перед записью проверьте, какая школа проводит конкретный курс.',so:'unk',st:'Статус набора по отдельным курсам не проверялся',dt:D,u:'https://www.lerna.kz/courses/finance/',k:'Перейти к курсам'});
add({n:'Эффективное управление рестораном. Практический курс',o:'Размещён на LERNA.kz (агрегатор). Адрес страницы курса относится к Skillbox; название школы в тексте каталога не указано',ty:'agg',c:[7],d:'Практический курс по управлению рестораном.',dur:'2 месяца',dh:null,so:'unk',st:'Статус набора не подтверждён',dt:D,u:'https://skillbox.lerna.kz/course/restaurantmanager/',k:'Подробнее о программе'});
add({n:'Лаборатория сильных продуктов и развития бизнеса',o:'Размещена на LERNA.kz (агрегатор). Название школы в тексте каталога не указано',ty:'agg',c:[7],d:'Программа по развитию продуктов и бизнеса; в каталоге два тарифа (индивидуальный и командный).',dur:'3 месяца',dh:null,so:'unk',st:'Статус набора не подтверждён',dt:D,u:'https://productlab.lerna.kz/product-rocket-individual/',k:'Подробнее о программе'});
// --- Не подтверждены (сайт недоступен для проверки)
function V(n,o,c,u,k,why){add({n:n,o:o,ty:'unv',c:c,d:why,so:'unk',st:'Статус набора не подтверждён',dt:'Не проверено',u:u,k:k})}
var W1='Сайт закрыт для автоматической проверки. Откройте страницу организатора.';
V('Академия Госзакупок','МЦФЭР',[1],'https://academy.zakup.mcfr.kz/','Перейти к курсам',W1);
V('Обучение поставщиков','MITWORK',[1,2],'https://new.mitwork.kz/supplier-training','Подробнее о программе',W1);
V('Образовательные программы (для внешних слушателей — уточнить)','Samruk Business Academy',[2],'https://sba.kz/education?index=4','Перейти к курсам','Страница загружается скриптом, содержимое проверить не удалось.');
V('Каталог курсов','Skills Enbek',[7,6],'https://skills.enbek.kz/','Перейти к курсам',W1);
V('Основы предпринимательства','Бастау Бизнес',[7],'https://business.enbek.kz/','Перейти к курсам',W1);
V('Государственные закупки','International Business Academy (IBA)',[1],'https://www.iba.kz/en/seminary/procurement/','Подробнее о программе','Страница вернула ошибку при проверке.');
V('Управление закупками и отношениями с поставщиками','International Business Academy (IBA)',[1],'https://www.iba.kz/en/seminary/upravlenie-zakupkami/','Подробнее о программе','Страница вернула ошибку при проверке.');
V('Учебная платформа AIFC Academy','AIFC Academy',[6,3],'https://aifc-academy.courstore.com/ru/login','Перейти к курсам',W1);
V('Расписание семинаров','Все Закупки',[1,2],'https://www.vsezakupki.kz/raspisanie-seminarov','Перейти к расписанию',W1);
V('Информация об обучении','Zakupki Tender Asia',[1],'https://zakupki-tender.asia.kz/info.html','Подробнее о программе',W1);
V('Программы по корпоративному управлению','Национальный совет по корпоративному управлению',[4],'https://ncgc.kz/','Перейти к курсам','Страница вернула ошибку при проверке.');
V('Курсы повышения квалификации (КПК)','KBTU — Академия корпоративного образования',[5,6],'https://www.kbtu.kz/ru/akademiya-korporativnogo-obrazovaniya/nepreryvnoe-obrazovanie/4907-kursy-povysheniya-kvalifikatsii-kpk','Подробнее о программе',W1);
var CN={1:'Государственные закупки и тендеры',2:'Самрук-Қазына и недропользователи',3:'Корпоративное право и договорная работа',4:'Корпоративное управление и комплаенс',5:'Бухгалтерия, налоги и МСФО',6:'Финансовый менеджмент и инвестиции',7:'Предпринимательство и управление бизнесом'};
var TN={direct:'Прямой организатор',agg:'Агрегатор',unv:'Данные не подтверждены'};
var L={ru:'Русский',kk:'Казахский',en:'Английский'};
var $=function(i){return document.getElementById(i)};
function row(t,v){return v?'<dt>'+t+'</dt><dd>'+v+'</dd>':''}
function card(x){
var cats=x.c.map(function(i){return CN[i]}).join('; ');
var h='<div class="card pc"><div><span class="badge '+(x.ty==='unv'?'b-no':'b-ok')+'" style="margin:0">'+TN[x.ty]+'</span> <span class="note">'+(x.ty==='unv'?'Не проверено':'Проверено '+x.dt)+'</span></div><h4>'+x.n+'</h4><div class="mut" style="font-size:13px">'+x.o+'</div><p style="font-size:14px;margin:0">'+x.d+'</p><dl>'
+row('Категория',cats)+row('Аудитория',x.a)+row('Язык',x.l?L[x.l]:'')+row('Формат',x.fm)+row('Длительность',x.dur)+row('Документ',x.cert)+row('Набор',x.st)+row('Примечание',x.note)
+'</dl><p class="note" style="margin:0">Стоимость и условия обучения уточняйте на официальном сайте организатора.</p>'
+'<div class="btns"><a href="'+x.u+'" target="_blank" rel="noopener">'+x.k+'</a>'+(x.r?'<a class="pri" href="'+x.r+'" target="_blank" rel="noopener">'+x.rk+'</a>':'')+'</div></div>';
return h}
function render(){
var q=$('q').value.trim().toLowerCase(),c=$('fc').value,t=$('ft').value,f=$('ff').value,l=$('fl').value,s=$('fs').value,o=$('so').value;
var r=P.filter(function(x){
if(q&&(x.n+' '+x.o+' '+x.d).toLowerCase().indexOf(q)<0)return false;
if(c&&x.c.indexOf(+c)<0)return false;if(t&&x.ty!==t)return false;
if(f&&(!x.fk||x.fk.indexOf(f)<0))return false;if(l&&x.l!==l)return false;if(s&&x.so!==s)return false;return true});
var big=1e12;
if(o==='dur')r.sort(function(a,b){return (a.dh==null?big:a.dh)-(b.dh==null?big:b.dh)});
if(o==='date')r.sort(function(a,b){return (a.ty==='unv'?1:0)-(b.ty==='unv'?1:0)});
$('plist').innerHTML=r.map(card).join('');$('empty').hidden=r.length>0;$('cnt').textContent='Показано программ и страниц: '+r.length+' из '+P.length}
['q','fc','ft','ff','fl','fs','so'].forEach(function(i){$(i).addEventListener(i==='q'?'input':'change',render)});
render();
var S=[['МЦФЭР','https://academy.zakup.mcfr.kz/','не проверено'],['MITWORK','https://new.mitwork.kz/supplier-training','не проверено'],['Samruk Business Academy','https://sba.kz/education?index=4','не проверено'],['AIFC Academy','https://academy.aifc.kz/','проверено (4 программы)'],['Платформа AIFC Academy','https://aifc-academy.courstore.com/ru/login','не проверено'],['Skills Enbek','https://skills.enbek.kz/','не проверено'],['Бастау Бизнес','https://business.enbek.kz/','не проверено'],['IBA','https://www.iba.kz/en/seminary/procurement/','не проверено'],['Inside Business','https://inside-b.kz/obuchenie-dlja-postavshhikov','проверено (2 программы)'],['Все Закупки','https://www.vsezakupki.kz/raspisanie-seminarov','не проверено'],['Центр государственных закупок','https://zakupgov.kz/','проверено, актуальность не подтверждена'],['Lider Edu','https://lider-edu.kz/kursy/kursy-gosudarstvennykh-zakupok-v-astane/kursy-zakupki-samruk-k-azyna-v-2026-godu-dlya-postavshchikov-v-astane','проверено (1 программа)'],['Zakupki Tender Asia','https://zakupki-tender.asia.kz/info.html','не проверено'],['ВШЭ ИПБА','https://hseipaa.kz/obuchenie?category=yurisprudentsiya','проверено (каталог; 4 программы с данными)'],['Нац. совет по корпоративному управлению','https://ncgc.kz/','не проверено (ошибка страницы)'],['Uchet.Академия','https://academy.uchet.kz/catalog','проверено (каталог)'],['QAZAQ PROFI','https://www.qazaq-profi.kz/kurse.html','проверено (расписание)'],['KBTU — Академия корпоративного образования','https://www.kbtu.kz/ru/akademiya-korporativnogo-obrazovaniya/nepreryvnoe-obrazovanie/4907-kursy-povysheniya-kvalifikatsii-kpk','не проверено'],['Skillbox Казахстан','https://skillbox.kz/course/businessman-finance/','проверено (1 программа)'],['LERNA Kazakhstan (агрегатор)','https://www.lerna.kz/courses/entrepreneurship/','проверено (агрегатор)']];
$('srcs').innerHTML=S.map(function(x){return '<div class="card" style="padding:10px"><a class="link" href="'+x[1]+'" target="_blank" rel="noopener">'+x[0]+'</a><div class="note">'+x[2]+'</div></div>'}).join('');
})();

