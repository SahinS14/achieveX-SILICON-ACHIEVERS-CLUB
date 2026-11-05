"""Private draft schedule configuration; only revealed entries are returned publicly."""
import json,re,hashlib
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from urllib.parse import urlparse
PDF='https://silicon.ac.in/wp-content/uploads/2026/02/UG-BTECH-CSE-2025.pdf'
# These are curriculum references, not the assessment's final scope or exam order.
PRESETS=[('C Programming',37),('Basic Electronics',28),('Basic Electrical Engineering',31),('Basic Mathematics',21),('English',54),('DSA',45),('OOPs in Java',69),('Operating Systems',78),('Python',93),('SQL / Databases',98),('Circuit Theory',112)]
def defaults():
    subjects={'junior':['Aptitude','BEE / Basic Electronics','English','C Programming & Debugging','Basic Mathematics'],'cs':['Aptitude','C Programming','SQL & OS','DSA & Python Basics','OOPs in Java'],'core':['Aptitude','C & Python','Electronics Basics','Signals & Systems','Circuit Theory']}
    pages={'Aptitude':None,'BEE / Basic Electronics':28,'English':54,'C Programming & Debugging':37,'Basic Mathematics':21,'C Programming':37,'SQL & OS':98,'DSA & Python Basics':45,'OOPs in Java':69,'C & Python':37,'Electronics Basics':28,'Signals & Systems':None,'Circuit Theory':112}
    return {track:[{'round':i+1,'subject':subject,'scope':'','syllabus_url':PDF+'#page='+str(pages[subject]) if pages[subject] else '', 'revealed':False,'date':''} for i,subject in enumerate(names)] for track,names in subjects.items()}
def revision(data):
    return hashlib.sha256(json.dumps(validate(data),sort_keys=True,separators=(',',':')).encode()).hexdigest()

def read(root,url,key):
    try:
        if url or key:
            if not url.startswith('https://') or not key:raise RuntimeError('Complete the Supabase schedule connection settings.')
            try:
                with urlopen(Request(url+'/storage/v1/object/achievex-config/schedule.json',headers={'apikey':key,'Cache-Control':'no-cache'}),timeout=20) as r:data=json.load(r)
            except HTTPError as e:
                try:detail=json.loads(e.read())
                except ValueError:detail={}
                if e.code==404 or str(detail.get('statusCode'))=='404':return defaults()
                raise RuntimeError('Unable to read schedule from Supabase Storage.') from e
        else:
            path=root/'.data'/'schedule.json'
            data=json.loads(path.read_text()) if path.exists() else defaults()
        return validate(data)
    except (URLError,TimeoutError,OSError) as e:raise RuntimeError('Schedule connection unavailable.') from e
    except (ValueError,TypeError) as e:raise RuntimeError('Saved schedule is invalid. Restore a valid schedule before publishing.') from e
def validate(data):
    if not isinstance(data,dict) or set(data)!= {'junior','cs','core'}:raise ValueError('Provide all three schedule categories.')
    result={}
    for track in ('junior','cs','core'):
        entries=data[track]
        if not isinstance(entries,list) or len(entries)!=5:raise ValueError('Each category must have five rounds.')
        result[track]=[]
        for i,entry in enumerate(entries):
            if not isinstance(entry,dict):raise ValueError('Invalid schedule entry.')
            if type(entry.get('round')) is not int or entry['round']!=i+1:raise ValueError('Rounds must be numbered 1 to 5 in order.')
            for field in ('subject','scope','syllabus_url','date'):
                if not isinstance(entry.get(field,''),str):raise ValueError(f'{field} must be text.')
            subject=entry.get('subject','').strip();scope=entry.get('scope','').strip();link=entry.get('syllabus_url','').strip();date=entry.get('date','').strip()
            if any(ord(c)<32 for c in subject+link+date) or any(ord(c)<32 and c not in '\n\r\t' for c in scope):raise ValueError('Invalid control characters in schedule.')
            if len(subject)>160 or len(scope)>6000:raise ValueError('Subject or syllabus scope is too long.')
            if link:
                try:
                    parsed=urlparse(link);port=parsed.port
                    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or any(c.isspace() for c in link) or len(link)>1000:raise ValueError()
                except ValueError:raise ValueError('Syllabus link must be a valid HTTPS URL without embedded credentials.')
            if date:
                import datetime
                try:
                    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',date):raise ValueError()
                    datetime.date.fromisoformat(date)
                except ValueError:raise ValueError('Use a valid examination date.')
            start=entry.get('start_time','');end=entry.get('end_time','')
            if not isinstance(start,str) or not isinstance(end,str):raise ValueError('Exam times must be text.')
            if bool(start)!=bool(end):raise ValueError('Provide both start and end times.')
            if start and (not date or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',start) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',end) or end<=start):raise ValueError('Provide a date and valid start/end times, with end after start (IST).')
            reveal=entry.get('revealed',False)
            if not isinstance(reveal,bool):raise ValueError('Invalid reveal option.')
            if reveal and (not subject or not(scope or link)):raise ValueError(f'{track} round {i+1}: add a subject and scope or syllabus link before revealing.')
            result[track].append({'round':i+1,'subject':subject,'scope':scope,'syllabus_url':link,'revealed':reveal,'date':date})
            if start:result[track][-1].update(start_time=start,end_time=end)
    return result
def save(root,url,key,data):
    data=validate(data)
    if url or key:
        try:
            req=Request(url+'/storage/v1/object/achievex-config/schedule.json',data=json.dumps(data).encode(),headers={'apikey':key,'Content-Type':'application/json','x-upsert':'true'},method='POST')
            with urlopen(req,timeout=20) as r:r.read()
        except (HTTPError,URLError,TimeoutError) as e:raise RuntimeError('Unable to save schedule. Check the private achievex-config bucket in Supabase Storage.') from e
    else:
        root.joinpath('.data').mkdir(exist_ok=True);path=root/'.data'/'schedule.json';tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data));tmp.replace(path)
def public(data):
    # Explicit allowlist: private draft fields never pass through accidentally.
    result={}
    for track,entries in validate(data).items():
        result[track]=[]
        for entry in entries:
            visible={k:entry[k] for k in ('round','revealed','date')}
            if entry.get('start_time'):visible.update(start_time=entry['start_time'],end_time=entry['end_time'])
            if entry['revealed']:visible.update({k:entry[k] for k in ('subject','scope','syllabus_url')})
            result[track].append(visible)
    return result
