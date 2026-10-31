/* DOM interaction regression tests. jsdom does not measure browser layout or touch physics. */
const {JSDOM}=require('jsdom');
const fs=require('node:fs');
const assert=require('node:assert/strict');
const html=fs.readFileSync('dist/index.html','utf8');
const source=fs.readFileSync('dist/app.js','utf8');
const {resolve}=require('node:path');
const staticDOM=new JSDOM(html),staticDoc=staticDOM.window.document;
const ids=[...staticDoc.querySelectorAll('[id]')].map(el=>el.id);
assert.equal(new Set(ids).size,ids.length,'duplicate HTML IDs');
for(const el of staticDoc.querySelectorAll('[src],link[rel="stylesheet"]')){
 const asset=el.getAttribute('src')||el.getAttribute('href');
 if(asset&&!/^(https?:|data:)/.test(asset))assert.ok(fs.existsSync(resolve('dist',asset.split('?')[0])),'missing asset: '+asset);
}
const loaderScript=[...staticDoc.scripts].find(script=>script.textContent.includes("var el=document.getElementById('site-preloader')")).textContent;
staticDOM.window.close();
for(const visit of ['initial visit','refresh']){
 const loaderDOM=new JSDOM(html,{url:'https://achievex.test/',runScripts:'outside-only'});
 const window=loaderDOM.window;window.setTimeout=()=>1;
 window.eval(loaderScript);
 assert.equal(window.document.querySelector('#site-preloader').classList.contains('is-loading'),true,visit+' displays loader');
 window.document.querySelector('#skip-preloader').click();
 assert.equal(window.document.querySelector('#site-preloader').getAttribute('aria-hidden'),'true');
 loaderDOM.window.close();
}
console.log('Preloader appears on fresh visit and refresh');


const flush=()=>new Promise(resolve=>setImmediate(resolve));
async function audit(width,initialOffline=false){
 const dom=new JSDOM(html,{url:'https://achievex.test/',runScripts:'outside-only',pretendToBeVisual:true});
 const w=dom.window,d=w.document;let failures=initialOffline;
 w.matchMedia=query=>({matches:query.includes('prefers-reduced-motion')||query.includes('max-width:700px')&&width<=700,addEventListener(){},removeEventListener(){}});
 w.ResizeObserver=class{observe(){}disconnect(){}};
 w.IntersectionObserver=class{observe(){}unobserve(){}disconnect(){}};
 w.scrollTo=()=>{};
 w.HTMLElement.prototype.scrollIntoView=function(){};
 w.HTMLElement.prototype.scrollTo=function(opts){this.scrollLeft=opts.left||0;};
 w.HTMLElement.prototype.animate=()=>({cancel(){}});
 w.HTMLElement.prototype.getAnimations=()=>[];
 w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};
 w.HTMLDialogElement.prototype.close=function(){this.open=false;};
 const badge={id:'the-ace',name:'The Ace',image_url:'/assets/badges/the-ace.png',category:'ranking',description:'Top scorer',criteria:'Highest category score in a published week',evidence:'Top score in Week 1: 95%',count:1};
 const participants=Array.from({length:21},(_,i)=>({full_name:i===0?'Demo Student (Demo)':'Student '+i,sic:'demo'+String(i).padStart(5,'0'),year:1,track:'junior',scores:[95-i,90,85,null,null],badges:i===0?[badge]:[]}));
 participants[1].scores=[94,99,99,null,null];
 participants[20].scores=[null,90,85,null,null];
 participants[19].scores=[0,90,85,null,null];
 participants.push({full_name:'Registered Student',sic:'24beca53',year:3,track:'cs',scores:[88,91,97,null,null],badges:[]});
 const schedule=Object.fromEntries(['junior','cs','core'].map(track=>[track,Array.from({length:5},(_,i)=>({round:i+1,revealed:i===0&&track==='cs',subject:'C Programming',scope:'Loops and functions',syllabus_url:'https://silicon.ac.in/example.pdf',date:''}))]));
 w.fetch=async url=>{if(failures)throw Error('Simulated offline');return {ok:true,json:async()=>url==='/api/schedule'?{schedule}:{published_week:3,participants,badge_definitions:[]}};};
 w.console.error=()=>{};
 try{
  w.eval(source);await flush();await flush();
  if(initialOffline){
   assert.ok(d.querySelector('#retry-results'));assert.ok(d.querySelector('#retry-schedule'));
   d.querySelector('[data-cat="senior"]').click();assert.equal(d.querySelectorAll('.rank-row').length,0);assert.match(d.querySelector('#count').textContent,/unavailable/);
   failures=false;await w.loadLeaderboard();await w.loadSchedule();assert.equal(d.querySelectorAll('.rank-row').length,1);assert.equal(d.querySelector('#results-status').textContent,'');
   console.log('Initial offline state and retry recovery passed');return;
  }
  assert.equal(d.querySelectorAll('.rank-row').length,15,'first page');
  assert.match(d.querySelector('.demo-pill').textContent,/INCLUDES DEMO DATA/,'mixed demo label');
  assert.equal(d.querySelector('#rows').getAttribute('aria-busy'),'false');
  assert.match(d.querySelector('.rank-row').textContent,/Student 1/,'cumulative leader uses every published week');
  assert.equal(d.querySelector('.rank-row .score-value').textContent,'292');
  assert.equal(d.querySelector('#max').textContent,'300');
  const week=d.querySelector('#week');week.value='0';week.dispatchEvent(new w.Event('change'));
  assert.match(d.querySelector('.rank-row').textContent,/Demo Student/,'Week 1 has a different leader');
  assert.equal(d.querySelector('.rank-row .score-value').textContent,'95');
  assert.equal(d.querySelector('#max').textContent,'100');
  const scoreSearch=d.querySelector('#search');scoreSearch.value='demo00020';scoreSearch.dispatchEvent(new w.Event('input'));assert.equal(d.querySelectorAll('.rank-row').length,0,'ungraded week excluded');
  scoreSearch.value='demo00019';scoreSearch.dispatchEvent(new w.Event('input'));assert.equal(d.querySelector('.rank-row .score-value').textContent,'0','graded zero remains eligible');
  scoreSearch.value='';week.value='all';week.dispatchEvent(new w.Event('change'));
  assert.equal(d.querySelector('.rank-row .score-value').textContent,'292');

  d.querySelector('[data-board-page="2"]').click();
  assert.equal(d.querySelectorAll('.rank-row').length,6,'second page');
  d.querySelector('.standings-jump').click();assert.equal(d.activeElement.id,'search');
  const search=d.querySelector('#search');search.value='demo00000';search.dispatchEvent(new w.Event('input'));
  assert.equal(d.querySelectorAll('.rank-row').length,1,'SIC lookup');
  d.querySelector('.badge-chip').click();assert.equal(d.querySelector('#badge-detail-dialog').open,true);assert.match(d.querySelector('#badge-detail-body').textContent,/Top score in Week 1/);
  d.querySelector('#close-badge-detail').click();assert.equal(d.querySelector('#badge-detail-dialog').open,false);
  search.value='';search.dispatchEvent(new w.Event('input'));
  d.querySelector('[data-cat="senior"]').click();assert.equal(d.querySelectorAll('.rank-row').length,1);assert.equal(d.querySelector('#track').hidden,false);
  d.querySelector('[data-schedule="cs"]').click();d.querySelector('.agenda-row.revealed').click();assert.equal(d.querySelector('#syllabus-dialog').open,true);assert.equal(d.querySelector('#syllabus-title').textContent,'C Programming');
  d.querySelector('#close-syllabus').click();
  d.querySelector('#island-trigger').click();assert.equal(d.querySelector('#island-links').hidden,false);
  d.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Escape'}));assert.equal(d.querySelector('#island-links').hidden,true);
  d.querySelector('#island-theme').click();assert.equal(d.documentElement.dataset.theme,'light');assert.equal(d.querySelector('#island-theme').getAttribute('aria-label'),'Switch to dark mode');
  w.location.hash='#badges';w.renderRoute(true);assert.equal(d.querySelector('#badges').hidden,false);assert.equal(d.activeElement.tagName,'H1');
  assert.equal(d.querySelectorAll('#badges-grid .minimal-badge').length,7);
  d.querySelector('[data-badge-slide="6"]').click();assert.equal(d.querySelector('.badge-carousel-status').textContent,'7 / 7');assert.equal(d.querySelector('[data-badge-step="1"]').disabled,true);
  failures=true;await w.loadLeaderboard();assert.equal(d.querySelectorAll('.rank-row').length,1,'retain last results');assert.match(d.querySelector('#results-status').textContent,/last loaded results/);
  failures=false;await w.loadLeaderboard();assert.equal(d.querySelector('#results-status').textContent,'');
  failures=true;await w.loadSchedule();assert.ok(d.querySelector('#retry-schedule'));
  d.querySelector('[data-schedule="junior"]').click();assert.ok(d.querySelector('#retry-schedule'),'category change must not hide network errors');
  console.log(`DOM interactions passed at ${width}px configuration`);
 }finally{dom.window.close();}
}
(async()=>{for(const width of [320,390,768,1440])await audit(width);await audit(390,true);})().catch(error=>{console.error(error);process.exitCode=1;});
