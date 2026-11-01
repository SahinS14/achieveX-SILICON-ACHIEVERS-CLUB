const $=s=>document.querySelector(s),form=$('#participant-form');let records=[],editing=false,csvContent='',noticeTimer;
let adminSchedule=null,savedAdminSchedule=null,syllabusPresets=[],scheduleRevision='',scheduleDirty=false,scheduleSaving=false,displayedScheduleTrack='junior';
const safe=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number=n=>Number(n).toLocaleString('en-IN',{maximumFractionDigits:2});
async function api(path,body){const response=await fetch('/api/admin/'+path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});const data=await response.json();if(!response.ok){if(response.status===401&&path!=='login')locked();throw Error(data.error||'Request failed.');}return data;}
function notify(message,error=false){clearTimeout(noticeTimer);$('#notice').textContent=message;$('#notice').classList.toggle('error',error);$('#notice').hidden=false;noticeTimer=setTimeout(()=>$('#notice').hidden=true,7000);}
function locked(){$('#gate').hidden=false;$('#workspace').hidden=true;$('#logout').hidden=true;records=[];$('#roster').replaceChildren();adminSchedule=null;savedAdminSchedule=null;scheduleDirty=false;scheduleRevision='';$('#schedule-admin-rows').replaceChildren();}
async function load(){const session=await api('session');$('#published-week').value=session.published_week;$('#storage').textContent=session.storage==='supabase'?'SUPABASE CONNECTED':'LOCAL SQLITE · SUPABASE NOT CONFIGURED';records=(await api('participants')).participants;$('#gate').hidden=true;$('#workspace').hidden=false;$('#logout').hidden=false;$('#stat-count').textContent=records.length;$('#stat-categories').textContent=records.filter(r=>r.year===1).length+' / '+records.filter(r=>r.year>1).length;renderRoster();await loadAdminSchedule();}
$('#login').addEventListener('submit',async e=>{e.preventDefault();const button=e.submitter;button.disabled=true;$('#login-error').textContent='';try{await api('login',{pin:$('#pin').value});$('#pin').value='';await load();}catch(error){$('#login-error').textContent=error.message;}finally{button.disabled=false;}});
$('#logout').addEventListener('click',async()=>{try{await api('logout',{});locked();}catch(e){notify(e.message,true);}});
function trackOptions(){const junior=form.elements.year.value==='1';[...form.elements.track.options].forEach(o=>o.disabled=junior?o.value!=='junior':o.value==='junior');if(junior)form.elements.track.value='junior';else if(form.elements.track.value==='junior')form.elements.track.value='cs';}
form.elements.year.addEventListener('change',trackOptions);trackOptions();
function recalculate(){let total=0,count=0;for(let i=1;i<=5;i++){const v=form.elements['week'+i].value;if(v!==''){total+=Number(v)||0;count++;}}$('#total').textContent=number(total);$('#graded-count').textContent=`${count} / 5 weeks graded`;}
form.addEventListener('input',recalculate);
function reset(){editing=false;form.reset();form.elements.sic.readOnly=false;$('#form-heading').textContent='Add a participant';trackOptions();recalculate();}
$('#reset-form').addEventListener('click',reset);
form.addEventListener('submit',async e=>{e.preventDefault();const button=e.submitter;button.disabled=true;try{const raw=Object.fromEntries(new FormData(form));raw.editing=editing;const result=await api('participant',raw);await load();reset();notify(`Saved. Overall total: ${number(result.total)} / 500.`);}catch(error){notify(error.message,true);}finally{button.disabled=false;}});
function renderRoster(){const q=$('#roster-search').value.trim().toLowerCase();const visible=records.filter(r=>(r.full_name+' '+r.sic).toLowerCase().includes(q));$('#roster').innerHTML=visible.length?visible.map(r=>`<tr><td><b>${safe(r.full_name)}</b><small>${safe(r.sic)} · ${r.year}${({1:'st',2:'nd',3:'rd',4:'th'})[r.year]} yr · ${safe(r.branch)}</small></td><td>${r.track==='junior'?'Junior':r.track==='cs'?'Senior · CS':'Senior · Core'}</td>${[1,2,3,4,5].map(i=>`<td>${r['week'+i]===null?'—':number(r['week'+i])}</td>`).join('')}<td class="sum">${number(r.total)}</td><td><div class="row-actions"><button class="edit" data-sic="${safe(r.sic)}">Edit ↗</button><button class="delete" data-delete="${safe(r.sic)}">Delete</button></div></td></tr>`).join(''):'<tr><td colspan="9" class="empty">No participants found. Add a student or import your roster.</td></tr>';}
$('#roster-search').addEventListener('input',renderRoster);
$('#roster').addEventListener('click',e=>{const b=e.target.closest('[data-sic]');if(!b)return;const r=records.find(x=>x.sic===b.dataset.sic);if(!r)return;reset();editing=true;for(const [key,value]of Object.entries(r)){if(form.elements[key])form.elements[key].value=value??'';}trackOptions();form.elements.sic.readOnly=true;$('#form-heading').textContent='Edit participant';recalculate();form.scrollIntoView({behavior:'smooth',block:'start'});form.elements.full_name.focus({preventScroll:true});});
$('#publish-form').addEventListener('submit',async e=>{e.preventDefault();e.submitter.disabled=true;try{await api('settings',{published_week:Number($('#published-week').value)});notify('Public leaderboard updated.');}catch(error){notify(error.message,true);}finally{e.submitter.disabled=false;}});
$('#csv-file').addEventListener('change',()=>{$('#import-preview').hidden=true;csvContent='';});
$('#import-form').addEventListener('submit',async e=>{e.preventDefault();e.submitter.disabled=true;try{const file=$('#csv-file').files[0];if(!file||file.size>2_000_000)throw Error('Choose a CSV smaller than 2 MB.');csvContent=await file.text();const result=await api('import',{csv:csvContent,commit:false});$('#import-summary').textContent=`${result.count} valid participants: ${result.new} new, ${result.updates} updates.`;$('#import-preview').hidden=false;}catch(error){csvContent='';$('#import-preview').hidden=true;notify(error.message,true);}finally{e.submitter.disabled=false;}});
$('#commit-import').addEventListener('click',async e=>{e.target.disabled=true;try{const result=await api('import',{csv:csvContent,commit:true});$('#import-preview').hidden=true;csvContent='';$('#import-form').reset();await load();notify(`Imported ${result.count} participants successfully.`);}catch(error){notify(error.message,true);}finally{e.target.disabled=false;}});
load().catch(e=>{locked();if(e.message!=='Unlock the admin panel first.')$('#login-error').textContent=e.message;});

$('#roster').addEventListener('click',async e=>{const button=e.target.closest('[data-delete]');if(!button)return;const record=records.find(r=>r.sic===button.dataset.delete);if(!record)return;if(!confirm(`Delete ${record.full_name} (${record.sic}) and all five weekly scores? This cannot be undone.`))return;button.disabled=true;try{await api('delete',{sic:record.sic,confirm:true});if(form.elements.sic.value===record.sic)reset();await load();notify('Participant and scores deleted. Leaderboard updated.');}catch(error){button.disabled=false;notify(error.message,true);}});

const scheduleKey=value=>JSON.stringify(value,['junior','cs','core','round','subject','scope','syllabus_url','date','revealed']);
function scheduleStatus(){
 $('#schedule-admin-status').textContent=scheduleDirty?'Unsaved changes. Reveal switches take effect only after Save schedule & reveals.':'Saved schedule loaded. Hidden subjects stay private; exam dates can be visible before subject reveal.';
 document.querySelectorAll('.schedule-edit-card').forEach((card,i)=>{
  const current=adminSchedule?.[displayedScheduleTrack]?.[i],saved=savedAdminSchedule?.[displayedScheduleTrack]?.[i];
  const changed=scheduleKey(current)!==scheduleKey(saved);
  card.querySelector('.schedule-row-status').textContent=changed?(current.revealed?'Unsaved · will be visible after saving':'Unsaved · will be hidden after saving'):(saved?.revealed?'Saved · visible to students':'Saved · subject hidden');
 });
}
async function loadAdminSchedule(force=false){
 if(scheduleSaving)return;
 if(scheduleDirty&&!force){scheduleStatus();return;}
 try{
  const data=await api('schedule');adminSchedule=data.schedule;savedAdminSchedule=JSON.parse(JSON.stringify(data.schedule));scheduleRevision=data.revision;syllabusPresets=data.presets;scheduleDirty=false;
  displayedScheduleTrack=$('#schedule-admin-track').value;renderAdminSchedule();scheduleStatus();
 }catch(error){$('#schedule-admin-status').textContent=error.message;}
 $('#schedule-admin-form button[type="submit"]').disabled=!adminSchedule;
}
function captureSchedule(){
 if(!adminSchedule||scheduleSaving)return;
 document.querySelectorAll('.schedule-edit-card').forEach((el,i)=>{adminSchedule[displayedScheduleTrack][i]={round:i+1,subject:el.querySelector('[name="subject"]').value,scope:el.querySelector('[name="scope"]').value,syllabus_url:el.querySelector('[name="syllabus_url"]').value,date:el.querySelector('[name="date"]').value,revealed:el.querySelector('[name="revealed"]').checked};});
 scheduleDirty=scheduleKey(adminSchedule)!==scheduleKey(savedAdminSchedule);scheduleStatus();
}
function renderAdminSchedule(){
 if(!adminSchedule)return;
 displayedScheduleTrack=$('#schedule-admin-track').value;
 $('#schedule-admin-rows').innerHTML=adminSchedule[displayedScheduleTrack].map((item,i)=>`<article class="schedule-edit-card"><div class="schedule-edit-heading"><h3>Round 0${i+1}</h3><label class="reveal-switch"><input type="checkbox" name="revealed" ${item.revealed?'checked':''}>Reveal after saving</label></div><p class="schedule-row-status" role="status"></p><div class="form-grid"><label>Assessment subject<input name="subject" maxlength="160" value="${safe(item.subject)}" placeholder="Keep as draft until ready"></label><label>Date (optional, public even before reveal)<input type="date" name="date" value="${safe(item.date)}"></label><label>Curriculum reference preset<select class="syllabus-preset"><option value="">Choose a reference…</option>${syllabusPresets.map(p=>`<option value="${safe(p.url)}">${safe(p.name)}</option>`).join('')}</select></label><label>Syllabus URL<input name="syllabus_url" type="url" value="${safe(item.syllabus_url)}" placeholder="https://…#page=37"></label></div><label class="scope-label">Assessment scope / topics<textarea name="scope" maxlength="6000" rows="4" placeholder="Add the exact assessment topics or a syllabus URL before revealing">${safe(item.scope)}</textarea></label></article>`).join('');
 scheduleStatus();
}
$('#schedule-admin-track').addEventListener('change',()=>{captureSchedule();renderAdminSchedule();});
$('#schedule-admin-rows').addEventListener('input',captureSchedule);
$('#schedule-admin-rows').addEventListener('change',event=>{
 if(event.target.matches('.syllabus-preset')&&event.target.value)event.target.closest('.schedule-edit-card').querySelector('[name="syllabus_url"]').value=event.target.value;
 captureSchedule();
});
$('#reload-schedule').addEventListener('click',()=>{if(scheduleSaving)return;if(scheduleDirty&&!confirm('Discard unsaved schedule edits and reload the saved version?'))return;loadAdminSchedule(true);});
window.addEventListener('beforeunload',event=>{if(scheduleDirty){event.preventDefault();event.returnValue='';}});
$('#schedule-admin-form').addEventListener('submit',async event=>{
 event.preventDefault();if(!adminSchedule||scheduleSaving)return;captureSchedule();scheduleSaving=true;
 const controls=[...document.querySelectorAll('#schedule-admin-form input,#schedule-admin-form select,#schedule-admin-form textarea,#schedule-admin-form button,#schedule-admin-track,#reload-schedule')];controls.forEach(control=>control.disabled=true);
 try{
  const data=await api('schedule',{schedule:adminSchedule,revision:scheduleRevision});
  adminSchedule=data.schedule;savedAdminSchedule=JSON.parse(JSON.stringify(data.schedule));scheduleRevision=data.revision;scheduleDirty=false;renderAdminSchedule();
  notify('Schedule saved. Students see only revealed subjects; result publication is unchanged.');
 }catch(error){$('#schedule-admin-status').textContent=error.message;notify(error.message,true);}
 finally{scheduleSaving=false;controls.forEach(control=>{if(control.isConnected)control.disabled=false;});}
});
