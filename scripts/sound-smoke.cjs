const {JSDOM}=require('jsdom');
const fs=require('node:fs'),assert=require('node:assert/strict');
const source=fs.readFileSync('dist/soundtrack.js','utf8');
const flush=()=>new Promise(resolve=>setImmediate(resolve));
function fixture(pref){
 const dom=new JSDOM('<audio id="arena-music"></audio><button id="music-toggle"></button><button id="other">Other</button>',{url:'https://achievex.test/',runScripts:'outside-only',pretendToBeVisual:true});
 const w=dom.window,d=w.document,a=d.querySelector('audio'),b=d.querySelector('#music-toggle');let calls=0,pauses=0;
 a.play=()=>{calls++;return Promise.resolve();};a.pause=()=>{pauses++;a.dispatchEvent(new w.Event('pause'));};
 if(pref)w.localStorage.setItem('ax-music',pref);
 return {dom,w,d,a,b,calls:()=>calls,pauses:()=>pauses,init:()=>w.eval(source),ready:()=>w.dispatchEvent(new w.Event('achievex:ready'))};
}
(async()=>{
 let f=fixture();try{
  f.init();assert.equal(f.calls(),0,'no audio during loader');f.ready();await flush();assert.equal(f.calls(),1);assert.equal(f.b.getAttribute('aria-pressed'),'true');
  f.b.click();assert.equal(f.b.getAttribute('aria-pressed'),'false');assert.equal(f.w.localStorage.getItem('ax-music'),'off');
  f.d.querySelector('#other').click();await flush();assert.equal(f.calls(),1,'muted stays muted');
  f.b.click();await flush();assert.equal(f.calls(),2);assert.equal(f.b.getAttribute('aria-pressed'),'true');
  Object.defineProperty(f.d,'hidden',{configurable:true,value:true});f.d.dispatchEvent(new f.w.Event('visibilitychange'));assert.equal(f.b.getAttribute('aria-pressed'),'false');
  Object.defineProperty(f.d,'hidden',{configurable:true,value:false});f.d.dispatchEvent(new f.w.Event('visibilitychange'));await flush();assert.equal(f.calls(),3);
 }finally{f.dom.window.close();}
 f=fixture('off');try{f.init();f.ready();await flush();assert.equal(f.calls(),0,'saved off preference on next visit');f.b.click();await flush();assert.equal(f.calls(),1);}finally{f.dom.window.close();}
 f=fixture();try{
  let calls=0;f.a.play=()=>{calls++;return calls===1?Promise.reject(new f.w.DOMException('Blocked','NotAllowedError')):Promise.resolve();};
  f.init();f.ready();await flush();assert.equal(f.b.getAttribute('aria-pressed'),'false');
  f.d.querySelector('#other').click();await flush();assert.equal(calls,2);assert.equal(f.b.getAttribute('aria-pressed'),'true','gesture retries blocked autoplay');
 }finally{f.dom.window.close();}
 f=fixture();try{
  let resolve;f.a.play=()=>new Promise(done=>{resolve=done;});f.init();f.ready();f.b.click();resolve();await flush();assert.equal(f.b.getAttribute('aria-pressed'),'false','mute wins over pending playback');assert.ok(f.pauses()>0);
 }finally{f.dom.window.close();}
 console.log('Soundtrack passed: loader timing, autoplay fallback, mute persistence, hidden tab and pending-play cancellation');
})().catch(error=>{console.error(error);process.exitCode=1;});
