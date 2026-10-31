const DEFAULT_BADGE_DEFINITIONS = [
  {
    "id": "the-main-character",
    "name": "The Main Character",
    "icon": "👑",
    "description": "Current category leader by published cumulative score; final champion after Week 5.",
    "category": "ranking",
    "criteria": "Highest cumulative score within your category across published weeks. Missing scores count as zero; at least one graded result is required. Ties share the badge.",
    "image_url": "/assets/badges/the-main-character.png"
  },
  {
    "id": "the-ace",
    "name": "The Ace",
    "icon": "⚡",
    "description": "Highest scorer in an individual weekly exam.",
    "category": "ranking",
    "criteria": "Highest score in your category for each published weekly exam. Ties share the badge; multiple weekly awards are retained.",
    "image_url": "/assets/badges/the-ace.png"
  },
  {
    "id": "the-glow-up",
    "name": "The Glow Up",
    "icon": "📈",
    "description": "Biggest improvement compared with the previous weekly exam.",
    "category": "ranking",
    "criteria": "Largest positive gain in your category for each consecutive published exam pair. Both scores must be graded. Ties share the badge.",
    "image_url": "/assets/badges/the-glow-up.png"
  },
  {
    "id": "on-fire",
    "name": "On Fire",
    "icon": "🔥",
    "description": "Consistently scores at least 80% across three consecutive weekly exams.",
    "category": "milestone",
    "criteria": "Score 80% or higher in any three consecutive finalized weekly exams.",
    "image_url": "/assets/badges/on-fire.png"
  },
  {
    "id": "flawless",
    "name": "Flawless",
    "icon": "💎",
    "description": "Achieved a perfect score in a weekly exam.",
    "category": "milestone",
    "criteria": "Achieve a perfect 100% score in any verified weekly exam.",
    "image_url": "/assets/badges/flawless.png"
  },
  {
    "id": "the-comeback-arc",
    "name": "The Comeback Arc",
    "icon": "🚀",
    "description": "Makes a remarkable recovery after a low scoring exam.",
    "category": "milestone",
    "criteria": "Score strictly below 50% in one exam and improve by at least 20 percentage points in the next exam.",
    "image_url": "/assets/badges/the-comeback-arc.png"
  },
  {
    "id": "the-unlocked-five",
    "name": "The Unlocked Five",
    "icon": "🔒",
    "description": "Has graded results in all five published weekly exams.",
    "category": "milestone",
    "criteria": "All five weeks must be published and graded. A graded zero counts; a blank score does not. Scores serve as the participation record.",
    "image_url": "/assets/badges/the-unlocked-five.png"
  }
];

let datasets={junior:[],cs:[],core:[]},category='junior',period='all',publishedWeek=0,boardRevision=0,badgeDefinitions=[...DEFAULT_BADGE_DEFINITIONS],allContenders=[];
const $=s=>document.querySelector(s),initials=n=>n.split(' ').map(x=>x[0]).slice(0,2).join('');
const escapeHTML=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const formatScore=n=>Number(n).toLocaleString('en-IN',{maximumFractionDigits:2});
const total=p=>period==='all'?Math.round(p.scores.slice(0,publishedWeek).reduce((a,b)=>a+(b??0),0)*100)/100:(p.scores[Number(period)]??0);
function avatar(p){const n=p.index%16;return `<span class="avatar-art" style="background-position:${(n%4)*100/3}% ${Math.floor(n/4)*100/3}%" aria-hidden="true"></span>`}
function renderBadges(p){
 const list=p.badges||[];
 if(!list.length) return '';
 return `<div class="student-badges-list">${list.map(b=>`
   <span class="badge-chip" title="${escapeHTML(b.name)} · ${escapeHTML(b.evidence||b.description)}" tabindex="0">
     <img class="badge-chip-icon" src="${escapeHTML(b.image_url)}" alt="">
     <span class="badge-chip-name">${escapeHTML(b.name)}${b.count>1?` <b class="badge-chip-count">×${b.count}</b>`:''}</span>
   </span>
 `).join('')}</div>`;
}

let lastPodiumKey='',leaderboardPage=1,lastPaginationFilter='';const pageSize=15;
function render(){
 const key=category==='junior'?'junior':$('#track').value;
 const data=[...datasets[key]].filter(p=>publishedWeek>0&&(period==='all'?p.scores.slice(0,publishedWeek).some(s=>s!==null):p.scores[Number(period)]!==null)).sort((a,b)=>total(b)-total(a)||a.id.localeCompare(b.id));
 data.forEach((p,i)=>p.rank=i&&total(p)===total(data[i-1])?data[i-1].rank:i+1);
 const max=period==='all'?500:100;$('#max').textContent=max;
 const podiumKey=key+period+boardRevision;
 if(lastPodiumKey!==podiumKey){lastPodiumKey=podiumKey;const order=[data[1],data[0],data[2]].filter(Boolean);$('#podium').innerHTML=order.map(p=>`<article class="pod-entry ${p.rank===1?'first':p.rank===2?'second':'third'}"><div class="pod-person"><div class="avatar">${p.rank===1?'<span class="crown">♛</span>':''}${avatar(p)}</div><h3>${escapeHTML(p.name)}</h3><span class="pod-points"><span class="score-value" data-score="${total(p)}">${formatScore(total(p))}</span><small>PTS</small></span></div><div class="pod-block"><div class="platform-top"></div><div class="pod-liquid" style="height:${Math.max(12,Math.min(100,total(p)/(period==='all'?Math.max(100,publishedWeek*100):100)*100))}%" aria-hidden="true"><div class="liquid-wave wave-back"><svg viewBox="0 0 400 40" preserveAspectRatio="none"><path d="M0 20Q50 0 100 20T200 20T300 20T400 20V40H0Z"/></svg></div><div class="liquid-wave wave-front"><svg viewBox="0 0 400 40" preserveAspectRatio="none"><path d="M0 20Q50 0 100 20T200 20T300 20T400 20V40H0Z"/></svg></div></div><strong>${p.rank}</strong><span>${p.rank===1?'THE PACESETTER':'THE CONTENDER'}</span></div></article>`).join('');}
 const query=$('#search').value.trim().toLowerCase(),filtered=data.filter(p=>(p.name+' '+p.id).toLowerCase().includes(query));
 $('#count').textContent=`${filtered.length} of ${data.length} contenders · ${category==='junior'?'Junior':key==='cs'?'Senior / CS':'Senior / Core'} · ${period==='all'?'Cumulative / 500':`Week ${Number(period)+1}`}`;
 const filterKey=key+'|'+period+'|'+query;if(filterKey!==lastPaginationFilter){leaderboardPage=1;lastPaginationFilter=filterKey;}const pages=Math.max(1,Math.ceil(filtered.length/pageSize));leaderboardPage=Math.min(leaderboardPage,pages);const start=(leaderboardPage-1)*pageSize,visible=filtered.slice(start,start+pageSize);renderPagination(filtered.length,pages,start,visible.length);
 $('#rows').innerHTML=filtered.length?visible.map(p=>`<article class="rank-row ${p.rank===1?'leader':''}"><span class="rank-number">${p.rank}</span><span class="avatar">${avatar(p)}</span><div class="rank-info"><h3>${escapeHTML(p.name)}</h3><div class="rank-meta"><span>${escapeHTML(p.id)}</span><span>·</span><span class="student-year">${p.year}</span></div>${renderBadges(p)}</div><div class="rank-total"><strong class="score-value" data-score="${total(p)}">${formatScore(total(p))}</strong><small>pts</small><div class="bar"><span style="width:${total(p)/max*100}%"></span></div></div></article>`).join(''):`<p class="empty">${query?'No contenders match your search.':publishedWeek===0?'The first results are on their way. Check back after publication.':'No graded results in this category yet.'}</p>`;
 const weekly=[...datasets[key]].filter(p=>publishedWeek>0&&p.scores[publishedWeek-1]!==null).sort((a,b)=>(b.scores[publishedWeek-1]??0)-(a.scores[publishedWeek-1]??0));const winner=weekly[0];
 const mainChars=allContenders.flatMap(p=>(p.badges||[]).filter(b=>b.id==='the-main-character').map(b=>({...b,student:p})));
 const currentAces=allContenders.flatMap(p=>(p.badges||[]).filter(b=>b.id==='the-ace'&&(publishedWeek?b.qualifying_exam_id==='week'+publishedWeek:true)).map(b=>({...b,student:p})));
 const unlockedCount=allContenders.filter(p=>(p.badges||[]).some(b=>b.id==='the-unlocked-five')).length;

}
function renderPagination(total,pages,start,count){
 const nav=$('#leaderboard-pagination');if(!nav)return;nav.hidden=total===0;
 const candidates=new Set([1,pages,leaderboardPage-1,leaderboardPage,leaderboardPage+1]);const numbers=[...candidates].filter(n=>n>0&&n<=pages).sort((a,b)=>a-b);let previous=0;
 const links=numbers.map(n=>{const gap=previous&&n-previous>1?'<span class="page-gap" aria-hidden="true">…</span>':'';previous=n;return gap+`<button type="button" data-board-page="${n}" ${n===leaderboardPage?'aria-current="page"':''} aria-label="Page ${n}">${n}</button>`}).join('');
 nav.innerHTML=`<div class="pagination-controls"><button type="button" class="page-arrow" data-board-page="${leaderboardPage-1}" ${leaderboardPage===1?'disabled':''} aria-label="Previous page">←</button><div class="page-pill">${links}</div><button type="button" class="page-arrow" data-board-page="${leaderboardPage+1}" ${leaderboardPage===pages?'disabled':''} aria-label="Next page">→</button></div>`;
}
$('#leaderboard-pagination')?.addEventListener('click',event=>{const button=event.target.closest('[data-board-page]');if(!button||button.disabled)return;leaderboardPage=Number(button.dataset.boardPage);render();const current=$('#leaderboard-pagination').querySelector('[aria-current="page"]');current?.focus({preventScroll:true});$('.ranking-panel').scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});});
function renderBadgesPage(){
 if(!$('#badges-grid')) return;
 const list=(badgeDefinitions&&badgeDefinitions.length)?badgeDefinitions:DEFAULT_BADGE_DEFINITIONS;
 $('#badges-grid').innerHTML=list.map((b,index)=>{
  return `<article class="badge-card minimal-badge" style="--card-delay:${index*45}ms"><div class="honour-art"><span class="honour-index">0${index+1}</span><img src="${escapeHTML(b.image_url)}" alt="${escapeHTML(b.name)}" class="badge-card-image"></div><div class="honour-copy"><span class="honour-category">${b.category==='ranking'?'PERFORMANCE':'MILESTONE'}</span><h3 class="badge-card-title">${escapeHTML(b.name)}</h3><p class="badge-card-desc">${escapeHTML(b.description)}</p><details class="honour-rule"><summary>How it’s earned <span>＋</span></summary><p class="badge-card-criteria-text">${escapeHTML(b.criteria)}</p></details></div></article>`;
 }).join('');
}
let leaderboardLoadActive=false,lastResultsSignature="";
async function loadLeaderboard(){
 if(leaderboardLoadActive)return;leaderboardLoadActive=true;
 try{
  const response=await fetch('/api/leaderboard',{cache:'no-store'});
  if(!response.ok)throw Error('Unable to load results.');
  const payload=await response.json();
  const signature=JSON.stringify(payload);
  if(signature===lastResultsSignature)return;
  publishedWeek=payload.published_week||0;
  badgeDefinitions=(payload.badge_definitions&&payload.badge_definitions.length)?payload.badge_definitions.map(b=>({...b,image_url:b.image_url?b.image_url.replace(/^\//,''):`assets/badges/${b.id}.png`})):DEFAULT_BADGE_DEFINITIONS;
  allContenders=payload.participants||[];
  datasets={junior:[],cs:[],core:[]};
  allContenders.forEach((p,index)=>{
   const ord={1:'1st',2:'2nd',3:'3rd',4:'4th'};
   datasets[p.track].push({name:p.full_name,id:p.sic,year:ord[p.year]+' yr',scores:p.scores,badges:p.badges||[],index});
  });
  boardRevision++;
  if(period!=='all'&&Number(period)>=publishedWeek)period='all';
  $('#week').innerHTML='<option value="all">Overall / 500</option>'+Array.from({length:publishedWeek},(_,i)=>`<option value="${i}">Week ${i+1}</option>`).join('');
  $('#week').value=period;
  document.querySelector('.demo-pill').textContent=allContenders.length&&allContenders.every(p=>p.sic.startsWith('demo'))?'DEMO STANDINGS':'OFFICIAL STANDINGS';
  document.querySelector('.round-tag').innerHTML=`${publishedWeek?'RESULTS THROUGH WEEK '+publishedWeek:'AWAITING FIRST RESULTS'}`;
  document.querySelector('.arena-round strong').innerHTML=`Week ${String(publishedWeek).padStart(2,'0')} <em>/ 05</em>`;
  document.querySelectorAll('.round-dots i').forEach((dot,i)=>{dot.classList.toggle('completed',i<publishedWeek);dot.classList.toggle('current',i===publishedWeek-1);});
  document.querySelector('.list-footer>span').textContent='Published results · Equal scores share a rank';
  render();
  renderBadgesPage();
  lastResultsSignature=signature;
  if(!$('#leaderboard').hidden)requestAnimationFrame(()=>{try{replayScorecard()}catch(animationError){console.warn('Score animation unavailable',animationError)}});
 }
 catch(error){console.error('Leaderboard load failed',error);lastResultsSignature='';$('#rows').innerHTML='<div class="empty">Unable to load results. <button id="retry-results" type="button">Try again ↗</button></div>';$('#retry-results').addEventListener('click',loadLeaderboard);document.querySelector('.demo-pill').textContent='CONNECTION UNAVAILABLE';}
 finally{leaderboardLoadActive=false;}
}
document.querySelectorAll('[data-cat]').forEach(b=>b.addEventListener('click',()=>{category=b.dataset.cat;document.querySelectorAll('[data-cat]').forEach(x=>x.setAttribute('aria-pressed',x===b));$('#track').hidden=category==='junior';render()}));$('#week').addEventListener('change',e=>{period=e.target.value;render()});$('#track').addEventListener('change',render);$('#search').addEventListener('input',render);render();renderBadgesPage();loadLeaderboard();
function theme(value){document.documentElement.dataset.theme=value;document.querySelectorAll('button[data-theme]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.theme===value));document.querySelector('meta[name="theme-color"]').content=value==='dark'?'#100c1e':'#f2edff';try{localStorage.setItem('ax-theme',value)}catch(e){}}
document.querySelectorAll('button[data-theme]').forEach(b=>b.addEventListener('click',()=>theme(b.dataset.theme)));theme(document.documentElement.dataset.theme||'dark');
const labels={leaderboard:'Leaderboard',badges:'Badges & Achievements',schedule:'Schedule of Examination',about:'About Achievers’ Club'};function renderRoute(){const page=location.hash.slice(1) in labels?location.hash.slice(1):'leaderboard';document.body.dataset.page=page;document.querySelectorAll('.page').forEach(p=>p.hidden=p.id!==page);document.querySelectorAll('[data-page]').forEach(a=>{a.classList.toggle('active',a.dataset.page===page);if(a.dataset.page===page)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current')});$('#page-label').textContent=labels[page];$('#island-title').textContent=labels[page];document.title=`${labels[page]} — AchieveX`;window.scrollTo({top:0,behavior:"instant"});if(page==='badges')renderBadgesPage();}
let activeTransition;
function route(){if(!document.startViewTransition||matchMedia('(prefers-reduced-motion: reduce)').matches){renderRoute();return;}activeTransition?.skipTransition();activeTransition=document.startViewTransition(()=>{renderRoute()});activeTransition.updateCallbackDone.then(()=>{if(!$('#leaderboard').hidden)replayScorecard();if(location.hash==='#schedule')animateAgenda();}).catch(()=>{});activeTransition.finished.catch(()=>{});}
window.addEventListener('hashchange',route);renderRoute();
const island=$('#mobile-island'),islandTrigger=$('#island-trigger'),islandLinks=$('#island-links');
function setIsland(open,restore=false){island.classList.toggle('expanded',open);islandTrigger.setAttribute('aria-expanded',String(open));islandLinks.hidden=!open;if(restore)islandTrigger.focus();}
islandTrigger.addEventListener('click',()=>setIsland(islandTrigger.getAttribute('aria-expanded')!=='true'));
islandLinks.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>setIsland(false)));
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&island.classList.contains('expanded'))setIsland(false,true)});
document.addEventListener('pointerdown',e=>{if(!island.contains(e.target))setIsland(false)});
function updateIslandTheme(){const dark=document.documentElement.dataset.theme==='dark';$('#island-theme').textContent=dark?'☾':'☀';$('#island-theme').setAttribute('aria-label',dark?'Switch to light mode':'Switch to dark mode');}
$('#island-theme').addEventListener('click',()=>{theme(document.documentElement.dataset.theme==='dark'?'light':'dark');updateIslandTheme()});
document.querySelectorAll('button[data-theme]').forEach(b=>b.addEventListener('click',updateIslandTheme));updateIslandTheme();
const reduceMotion=matchMedia('(prefers-reduced-motion: reduce)');
function animateBoard(){if(reduceMotion.matches||document.startViewTransition)return;const panel=$('.page:not([hidden])');if(panel)panel.animate([{opacity:.65,transform:'translateY(8px)'},{opacity:1,transform:'translateY(0)'}],{duration:250,easing:'cubic-bezier(.23,1,.32,1)'});}
window.addEventListener('hashchange',animateBoard);
function animateRankings(){if(reduceMotion.matches)return;document.querySelectorAll('.rank-row').forEach((row,i)=>{row.getAnimations().forEach(a=>a.cancel());row.animate([{opacity:.35,transform:'translateY(9px)'},{opacity:1,transform:'translateY(0)'}],{duration:240,delay:Math.min(i,7)*30,easing:'cubic-bezier(.23,1,.32,1)',fill:'backwards'});});}
document.querySelectorAll('[data-cat],#week,#track').forEach(control=>control.addEventListener('click',e=>{if(e.currentTarget.matches('[data-cat]'))animateRankings()}));
['#week','#track'].forEach(selector=>$(selector).addEventListener('change',animateRankings));
animateBoard();animateRankings();

let scheduleCategory='junior',scheduleData={junior:[],cs:[],core:[]};const scheduleLabels={junior:'Junior category',cs:'Senior / Computer Science',core:'Senior / Core'};
function renderSchedule(){
 $('#agenda-category').textContent=scheduleLabels[scheduleCategory].toUpperCase();
 const entries=scheduleData[scheduleCategory];
 $('#schedule-list').innerHTML=Array.from({length:5},(_,i)=>{const e=entries[i]||{round:i+1,revealed:false};return `<button type="button" class="agenda-row tone-${i%3} ${e.revealed?'revealed':'unrevealed'}" data-round="${i}" ${e.revealed?'':'disabled'}><div class="agenda-round"><span>ROUND</span><b>0${i+1}</b></div><div class="agenda-main"><span>${scheduleLabels[scheduleCategory]}</span><h3>${e.revealed?escapeHTML(e.subject):'The next challenge awaits.'}</h3><p>${e.revealed?'View syllabus & assessment scope ↗':'Subject not yet revealed · Stay ready'}</p></div><div class="agenda-points"><b>100</b><span>POINTS</span></div><div class="agenda-date"><h4>${e.date?escapeHTML(e.date):'DATE<br>AWAITED'}</h4><p>${e.revealed?'SYLLABUS AVAILABLE':'REVEAL COMING SOON'}</p></div><span class="agenda-arrow" aria-hidden="true">${e.revealed?'↗':'⌁'}</span></button>`}).join('');
 document.querySelectorAll('[data-schedule]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.schedule===scheduleCategory)));
}
async function loadSchedule(){try{const r=await fetch('/api/schedule',{cache:'no-store'});if(!r.ok)throw Error('Schedule unavailable');scheduleData=(await r.json()).schedule;renderSchedule()}catch(e){$('#schedule-list').innerHTML='<p class="empty">The schedule is temporarily unavailable. Please refresh to retry.</p>';}}
document.querySelectorAll('[data-schedule]').forEach(b=>b.addEventListener('click',()=>{scheduleCategory=b.dataset.schedule;renderSchedule()}));renderSchedule();loadSchedule();
$('#schedule-list').addEventListener('click',event=>{const button=event.target.closest('[data-round]');if(!button)return;const item=scheduleData[scheduleCategory][Number(button.dataset.round)];if(!item?.revealed)return;$('#syllabus-title').textContent=item.subject;$('#syllabus-category').textContent=scheduleLabels[scheduleCategory]+' / Round '+item.round;$('#syllabus-scope').textContent=item.scope||'Syllabus reference';const link=$('#syllabus-link');link.hidden=!item.syllabus_url;if(item.syllabus_url&&new URL(item.syllabus_url).protocol==='https:')link.href=item.syllabus_url;$('#syllabus-dialog').showModal();});
$('#close-syllabus').addEventListener('click',()=>$('#syllabus-dialog').close());
$('#syllabus-dialog').addEventListener('click',e=>{if(e.target===$('#syllabus-dialog')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
window.addEventListener('focus',loadSchedule);window.addEventListener('hashchange',()=>{if(location.hash==='#schedule')loadSchedule()});
// Replay the complete scorecard when it becomes visible, including returning to the same route.
let scoreFrame=0;
function replayScorecard(){
 if($('#leaderboard').hidden)return;
 cancelAnimationFrame(scoreFrame);
 const values=[...document.querySelectorAll('.score-value')];
 const finish=()=>values.forEach(el=>el.textContent=formatScore(el.dataset.score));
 if(reduceMotion.matches){finish();return;}
 const ease='cubic-bezier(.23,1,.32,1)';
 document.querySelectorAll('.pod-block').forEach((el,i)=>{el.getAnimations().forEach(a=>a.cancel());el.animate([{transform:'translateY(75%)',opacity:0},{transform:'translateY(0)',opacity:1}],{duration:850,delay:i*80,easing:ease,fill:'backwards'});});
 document.querySelectorAll('.pod-person').forEach((el,i)=>{el.getAnimations().forEach(a=>a.cancel());el.animate([{transform:'translateY(22px)',opacity:0},{transform:'translateY(0)',opacity:1}],{duration:550,delay:150+i*80,easing:ease,fill:'backwards'});});
 document.querySelectorAll('.bar>span').forEach((el,i)=>{el.getAnimations().filter(a=>a.effect?.target===el).forEach(a=>a.cancel());el.animate([{transform:'scaleX(.02)'},{transform:'scaleX(1)'}],{duration:950,delay:Math.min(i,7)*55,easing:ease,fill:'backwards'});});
 const start=performance.now();
 function tick(now){const progress=Math.min((now-start)/1100,1);const eased=1-Math.pow(1-progress,3);values.forEach(el=>{el.textContent=formatScore(Math.round(Number(el.dataset.score)*eased*100)/100)});if(progress<1)scoreFrame=requestAnimationFrame(tick);else finish();}
 scoreFrame=requestAnimationFrame(tick);animateRankings();
}
window.addEventListener('hashchange',replayScorecard);
document.querySelectorAll('a[href="#leaderboard"]').forEach(a=>a.addEventListener('click',()=>{if(!$('#leaderboard').hidden)replayScorecard()}));
document.querySelectorAll('[data-cat]').forEach(b=>b.addEventListener('click',replayScorecard));['#week','#track'].forEach(s=>$(s).addEventListener('change',replayScorecard));
requestAnimationFrame(replayScorecard);

// Reveal cards once as they enter the viewport, keeping reading and scrolling stable.
const revealObserver=new IntersectionObserver(entries=>{entries.forEach(entry=>{if(!entry.isIntersecting)return;revealObserver.unobserve(entry.target);if(reduceMotion.matches)return;entry.target.animate([{opacity:0,transform:'translateY(22px)'},{opacity:1,transform:'translateY(0)'}],{duration:500,easing:'cubic-bezier(.23,1,.32,1)',fill:'backwards'});});},{threshold:.12});
document.querySelectorAll('.faculty-card,.member-card,.highlight,.about-grid article').forEach(el=>revealObserver.observe(el));
function animateAgenda(){if(reduceMotion.matches)return;document.querySelectorAll('.agenda-row').forEach((row,i)=>row.animate([{opacity:0,transform:'translateY(26px)'},{opacity:1,transform:'translateY(0)'}],{duration:450,delay:i*55,easing:'cubic-bezier(.23,1,.32,1)',fill:'backwards'}));}
document.querySelectorAll('[data-schedule]').forEach(button=>button.addEventListener('click',animateAgenda));
window.addEventListener('hashchange',()=>{if(location.hash==='#schedule')animateAgenda()});
document.querySelectorAll('.about-story,.playbook-grid article,.about-honours,.about-closing').forEach(el=>revealObserver.observe(el));

setInterval(()=>{if(!document.hidden)loadLeaderboard()},30000);window.addEventListener("focus",loadLeaderboard);
