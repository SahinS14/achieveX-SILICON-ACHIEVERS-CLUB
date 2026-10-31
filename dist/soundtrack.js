// Playback starts only after the loader; browser autoplay rules are respected.
(()=>{
 const audio=document.getElementById('arena-music'),button=document.getElementById('music-toggle');
 let enabled=true,ready=document.documentElement.dataset.arenaReady==='true',playing=false,pending=false,failed=false;
 try{enabled=localStorage.getItem('ax-music')!=='off';}catch{}
 audio.volume=.22;
 const save=()=>{try{localStorage.setItem('ax-music',enabled?'on':'off');}catch{}};
 function update(){
  button.dataset.playing=String(playing);button.setAttribute('aria-pressed',String(playing));
  const label=playing?'Mute background music':failed?'Retry background music':'Play background music';
  button.setAttribute('aria-label',label);button.title=label;
 }
 async function play(){
  if(!ready||!enabled||document.hidden||playing||pending)return;
  pending=true;
  try{
   await audio.play();failed=false;
   if(!enabled||document.hidden){audio.pause();playing=false;}else playing=true;
  }catch(error){playing=false;failed=error.name!=='NotAllowedError'&&error.name!=='AbortError';}
  finally{pending=false;update();}
 }
 button.addEventListener('click',()=>{
  if(playing||pending){enabled=false;playing=false;audio.pause();save();update();}
  else{enabled=true;failed=false;save();play();update();}
 });
 window.addEventListener('achievex:ready',()=>{ready=true;play();});
 // A click/keyboard action can unlock playback when automatic playback is blocked.
 function unlock(event){if(button.contains(event.target)||failed)return;if(ready&&enabled&&!playing)play();}
 document.addEventListener('click',unlock);
 document.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' ')unlock(event);});
 document.addEventListener('visibilitychange',()=>{
  if(document.hidden){audio.pause();playing=false;update();}else if(!failed)play();
 });
 audio.addEventListener('pause',()=>{playing=false;update();});
 audio.addEventListener('error',()=>{failed=true;playing=false;update();});
 update();if(ready)play();
})();
