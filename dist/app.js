let datasets={junior:[],cs:[],core:[]},category='junior',period='all',publishedWeek=0,boardRevision=0;
const $=s=>document.querySelector(s),initials=n=>n.split(' ').map(x=>x[0]).slice(0,2).join('');
const escapeHTML=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const formatScore=n=>Number(n).toLocaleString('en-IN',{maximumFractionDigits:2});
const total=p=>period==='all'?Math.round(p.scores.slice(0,publishedWeek).reduce((a,b)=>a+(b??0),0)*100)/100:(p.scores[Number(period)]??0);
function avatar(p){const n=p.index%16;return `<span class="avatar-art" style="background-position:${(n%4)*100/3}% ${Math.floor(n/4)*100/3}%" aria-hidden="true"></span>`}
let lastPodiumKey='';
function render(){
 const key=category==='junior'?'junior':$('#track').value;
 const data=[...datasets[key]].filter(p=>publishedWeek>0&&(period==='all'?p.scores.slice(0,publishedWeek).some(s=>s!==null):p.scores[Number(period)]!==null)).sort((a,b)=>total(b)-total(a)||a.id.localeCompare(b.id));
 data.forEach((p,i)=>p.rank=i&&total(p)===total(data[i-1])?data[i-1].rank:i+1);
 const max=period==='all'?500:100;$('#max').textContent=max;
 const podiumKey=key+period+boardRevision;
 if(lastPodiumKey!==podiumKey){lastPodiumKey=podiumKey;const order=[data[1],data[0],data[2]].filter(Boolean);$('#podium').innerHTML=order.map(p=>`<article class="pod-entry ${p.rank===1?'first':p.rank===2?'second':'third'}"><div class="pod-person"><div class="avatar">${p.rank===1?'<span class="crown">♛</span>':''}${avatar(p)}</div><h3>${escapeHTML(p.name)}</h3><span class="pod-points"><span class="score-value" data-score="${total(p)}">${formatScore(total(p))}</span><small>PTS</small></span></div><div class="pod-block"><div class="platform-top"></div><strong>${p.rank}</strong><span>${p.rank===1?'THE PACESETTER':'THE CONTENDER'}</span></div></article>`).join('');}
 const query=$('#search').value.trim().toLowerCase(),filtered=data.filter(p=>(p.name+' '+p.id).toLowerCase().includes(query));
 $('#count').textContent=`${filtered.length} of ${data.length} contenders · ${category==='junior'?'Junior':key==='cs'?'Senior / CS':'Senior / Core'} · ${period==='all'?'Cumulative / 500':`Week ${Number(period)+1}`}`;
 $('#rows').innerHTML=filtered.length?filtered.map(p=>`<article class="rank-row ${p.rank===1?'leader':''}"><span class="rank-number">${p.rank}</span><span class="avatar">${avatar(p)}</span><div class="rank-info"><h3>${escapeHTML(p.name)}</h3><div class="rank-meta"><span>${escapeHTML(p.id)}</span><span>·</span><span class="student-year">${p.year}</span></div></div><div class="rank-total"><strong class="score-value" data-score="${total(p)}">${formatScore(total(p))}</strong><small>pts</small><div class="bar"><span style="width:${total(p)/max*100}%"></span></div></div></article>`).join(''):`<p class="empty">${query?'No contenders match your search.':publishedWeek===0?'The first results are on their way. Check back after publication.':'No graded results in this category yet.'}</p>`;
 const weekly=[...datasets[key]].filter(p=>publishedWeek>0&&p.scores[publishedWeek-1]!==null).sort((a,b)=>(b.scores[publishedWeek-1]??0)-(a.scores[publishedWeek-1]??0));const winner=weekly[0],tied=winner?weekly.filter(p=>p.scores[publishedWeek-1]===winner.scores[publishedWeek-1]).length:0;
 $('#recognition').innerHTML=`<article class="highlight"><span class="highlight-icon">✧</span><div><small>${publishedWeek?'WEEK '+publishedWeek+' / TOP PERFORMER':'RESULTS / COMING SOON'}</small><h3>${winner?(tied>1?tied+' joint top performers':escapeHTML(winner.name)):'Your moment is ahead.'}</h3><p>${winner?formatScore(winner.scores[publishedWeek-1])+' / 100 · Leading by example.':'Official results will appear after publication.'}</p></div></article><article class="highlight"><span class="highlight-icon">↗</span><div><small>EVERY POINT COUNTS</small><h3>Five weeks. One journey.</h3><p>Cumulative scores out of 500. Equal scores share a rank.</p></div></article><article class="highlight"><span class="highlight-icon">◎</span><div><small>THE PERFECT FIVE</small><h3>Show up. All five weeks.</h3><p>Consistency deserves its own spotlight.</p></div></article>`;
}
let leaderboardLoadActive=false,lastResultsSignature="";
async function loadLeaderboard(){
 if(leaderboardLoadActive)return;leaderboardLoadActive=true;
 try{const response=await fetch('/api/leaderboard',{cache:'no-store'});if(!response.ok)throw Error('Unable to load results.');const payload=await response.json();const signature=JSON.stringify(payload);if(signature===lastResultsSignature)return;lastResultsSignature=signature;publishedWeek=payload.published_week;datasets={junior:[],cs:[],core:[]};payload.participants.forEach((p,index)=>{const ord={1:'1st',2:'2nd',3:'3rd',4:'4th'};datasets[p.track].push({name:p.full_name,id:p.sic,year:ord[p.year]+' yr',scores:p.scores,index});});boardRevision++;if(period!=='all'&&Number(period)>=publishedWeek)period='all';$('#week').innerHTML='<option value="all">Overall / 500</option>'+Array.from({length:publishedWeek},(_,i)=>`<option value="${i}">Week ${i+1}</option>`).join('');$('#week').value=period;document.querySelector('.demo-pill').textContent='OFFICIAL STANDINGS';document.querySelector('.round-tag').innerHTML=`<span class="status-dot"></span>${publishedWeek?'RESULTS THROUGH WEEK '+publishedWeek:'AWAITING FIRST RESULTS'}`;document.querySelector('.arena-round strong').innerHTML=`Week ${String(publishedWeek).padStart(2,'0')} <em>/ 05</em>`;document.querySelectorAll('.round-dots i').forEach((dot,i)=>{dot.classList.toggle('completed',i<publishedWeek);dot.classList.toggle('current',i===publishedWeek-1);});document.querySelector('.list-footer>span').textContent='Published results · Equal scores share a rank';render();if(!$('#leaderboard').hidden)replayScorecard();}
 catch(error){$('#rows').innerHTML='<p class="empty">Results are temporarily unavailable. Please refresh to try again.</p>';document.querySelector('.demo-pill').textContent='CONNECTION UNAVAILABLE';}
 finally{leaderboardLoadActive=false;}
}
document.querySelectorAll('[data-cat]').forEach(b=>b.addEventListener('click',()=>{category=b.dataset.cat;document.querySelectorAll('[data-cat]').forEach(x=>x.setAttribute('aria-pressed',x===b));$('#track').hidden=category==='junior';render()}));$('#week').addEventListener('change',e=>{period=e.target.value;render()});$('#track').addEventListener('change',render);$('#search').addEventListener('input',render);render();
function theme(value){document.documentElement.dataset.theme=value;document.querySelectorAll('button[data-theme]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.theme===value));document.querySelector('meta[name="theme-color"]').content=value==='dark'?'#100c1e':'#f2edff';try{localStorage.setItem('ax-theme',value)}catch(e){}}
document.querySelectorAll('button[data-theme]').forEach(b=>b.addEventListener('click',()=>theme(b.dataset.theme)));theme(document.documentElement.dataset.theme||'dark');
const labels={leaderboard:'Leaderboard',team:'Our Team',schedule:'Schedule of Examination',about:'About AchieveX'};function renderRoute(){const page=location.hash.slice(1) in labels?location.hash.slice(1):'leaderboard';document.body.dataset.page=page;document.querySelectorAll('.page').forEach(p=>p.hidden=p.id!==page);document.querySelectorAll('[data-page]').forEach(a=>{a.classList.toggle('active',a.dataset.page===page);if(a.dataset.page===page)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current')});$('#page-label').textContent=labels[page];$('#island-title').textContent=labels[page];document.title=`${labels[page]} — AchieveX`;window.scrollTo({top:0,behavior:"instant"}) }
let activeTransition;
function route(){if(!document.startViewTransition||matchMedia('(prefers-reduced-motion: reduce)').matches){renderRoute();return;}activeTransition?.skipTransition();activeTransition=document.startViewTransition(()=>{renderRoute()});activeTransition.updateCallbackDone.then(()=>{if(!$('#leaderboard').hidden)replayScorecard();if(location.hash==='#schedule')animateAgenda();}).catch(()=>{});activeTransition.finished.catch(()=>{});}
window.addEventListener('hashchange',route);renderRoute();
const subjects={junior:['Aptitude','BEE / Basic Electronics','English','C Programming & Debugging','Basic Mathematics'],cs:['Aptitude','C Programming','SQL & OS','DSA & Python Basics','OOPs in Java'],core:['Aptitude','C & Python','Electronics Basics','Signals & Systems','Circuit Theory']};function showSubjects(){$('#subject-list').innerHTML=subjects[$('#subjects').value].map(s=>`<span>${s}</span>`).join('')}$('#subjects').addEventListener('change',showSubjects);showSubjects();

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

let scheduleCategory='junior';const scheduleLabels={junior:'Junior category',cs:'Senior / Computer Science',core:'Senior / Core'};
function renderSchedule(){ $('#agenda-category').textContent=scheduleLabels[scheduleCategory].toUpperCase();$('#schedule-list').innerHTML=Array.from({length:5},(_,i)=>`<article class="agenda-row tone-${i%3}"><div class="agenda-round"><span>ROUND</span><b>0${i+1}</b></div><div class="agenda-main"><span>${scheduleLabels[scheduleCategory]}</span><h3>${subjects[scheduleCategory][i]}</h3><p>Assessment ${String(i+1).padStart(2,'0')} · Scope announced before the exam</p></div><div class="agenda-points"><b>100</b><span>POINTS</span></div><div class="agenda-date"><h4>DETAILS<br>TO FOLLOW</h4><p>Time & venue to be confirmed</p></div><span class="agenda-arrow" aria-hidden="true">↗</span></article>`).join('');document.querySelectorAll('[data-schedule]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.schedule===scheduleCategory)));$('#subjects').value=scheduleCategory;showSubjects();}
document.querySelectorAll('[data-schedule]').forEach(b=>b.addEventListener('click',()=>{scheduleCategory=b.dataset.schedule;renderSchedule()}));$('#subjects').addEventListener('change',e=>{scheduleCategory=e.target.value;renderSchedule()});renderSchedule();
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
document.querySelectorAll('[data-schedule]').forEach(button=>button.addEventListener('click',animateAgenda));$('#subjects').addEventListener('change',animateAgenda);
window.addEventListener('hashchange',()=>{if(location.hash==='#schedule')animateAgenda()});
const portraitRail=$('#portrait-rail');
function moveTeam(direction){const card=portraitRail.querySelector('.portrait-card');portraitRail.scrollBy({left:direction*(card.getBoundingClientRect().width+17),behavior:reduceMotion.matches?'instant':'smooth'});}
$('#team-prev').addEventListener('click',()=>moveTeam(-1));$('#team-next').addEventListener('click',()=>moveTeam(1));
function updatePortraitProgress(){const max=portraitRail.scrollWidth-portraitRail.clientWidth;const progress=max>0?portraitRail.scrollLeft/max:0;$('#portrait-progress').style.transform=`translateX(${Math.max(0,Math.min(1,progress))*300}%)`;const index=Math.min(4,1+Math.round(Math.max(0,progress)*3));$('#portrait-position').textContent=`0${index} / 04`;$('#team-prev').disabled=portraitRail.scrollLeft<2;$('#team-next').disabled=max<=2||portraitRail.scrollLeft>=max-2;}
portraitRail.addEventListener('scroll',updatePortraitProgress,{passive:true});window.addEventListener('resize',updatePortraitProgress);window.addEventListener('hashchange',()=>requestAnimationFrame(updatePortraitProgress));requestAnimationFrame(updatePortraitProgress);
document.querySelectorAll('.circle-profile,.portrait-card').forEach(el=>revealObserver.observe(el));
document.querySelector('a[href="#team-portraits"]').addEventListener('click',event=>{event.preventDefault();$('#team-portraits').scrollIntoView({behavior:reduceMotion.matches?'instant':'smooth',block:'start'});});
document.querySelectorAll('.about-story,.playbook-grid article,.about-honours,.about-closing').forEach(el=>revealObserver.observe(el));

loadLeaderboard();setInterval(()=>{if(!document.hidden)loadLeaderboard()},30000);window.addEventListener("focus",loadLeaderboard);
