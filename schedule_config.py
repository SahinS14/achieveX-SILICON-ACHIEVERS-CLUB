"""Private draft schedule configuration; only revealed entries are returned publicly."""
import json,re
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
def read(root,url,key):
    if url or key:
        try:
            with urlopen(Request(url+'/storage/v1/object/achievex-config/schedule.json',headers={'apikey':key}),timeout=20) as r:return json.load(r)
        except HTTPError as e:
            try:detail=json.loads(e.read())
            except ValueError:detail={}
            if e.code==404 or str(detail.get('statusCode'))=='404':return defaults()
            raise RuntimeError('Unable to read schedule from Supabase Storage.') from e
        except URLError as e:raise RuntimeError('Schedule connection unavailable.') from e
    path=root/'.data'/'schedule.json'
    return json.loads(path.read_text()) if path.exists() else defaults()
def validate(data):
    if not isinstance(data,dict) or set(data)!= {'junior','cs','core'}:raise ValueError('Provide all three schedule categories.')
    result={}
    for track in ('junior','cs','core'):
        entries=data[track]
        if not isinstance(entries,list) or len(entries)!=5:raise ValueError('Each category must have five rounds.')
        result[track]=[]
        for i,entry in enumerate(entries):
            if not isinstance(entry,dict):raise ValueError('Invalid schedule entry.')
            subject=str(entry.get('subject','')).strip();scope=str(entry.get('scope','')).strip();link=str(entry.get('syllabus_url','')).strip();date=str(entry.get('date','')).strip()
            if len(subject)>160 or len(scope)>6000:raise ValueError('Subject or syllabus scope is too long.')
            if link and (urlparse(link).scheme!='https' or not urlparse(link).netloc or len(link)>1000):raise ValueError('Syllabus link must be an HTTPS URL.')
            if date:
                import datetime
                try:datetime.date.fromisoformat(date)
                except ValueError:raise ValueError('Use a valid examination date.')
            reveal=entry.get('revealed',False)
            if not isinstance(reveal,bool):raise ValueError('Invalid reveal option.')
            if reveal and (not subject or not(scope or link)):raise ValueError(f'{track} round {i+1}: add a subject and scope or syllabus link before revealing.')
            result[track].append({'round':i+1,'subject':subject,'scope':scope,'syllabus_url':link,'revealed':reveal,'date':date})
    return result
def save(root,url,key,data):
    data=validate(data)
    if url or key:
        try:
            req=Request(url+'/storage/v1/object/achievex-config/schedule.json',data=json.dumps(data).encode(),headers={'apikey':key,'Content-Type':'application/json','x-upsert':'true'},method='POST')
            with urlopen(req,timeout=20) as r:r.read()
        except (HTTPError,URLError) as e:raise RuntimeError('Unable to save schedule. Check the private achievex-config bucket in Supabase Storage.') from e
    else:
        root.joinpath('.data').mkdir(exist_ok=True);path=root/'.data'/'schedule.json';tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data));tmp.replace(path)
def public(data):
    return {track:[entry if entry['revealed'] else {'round':entry['round'],'revealed':False,'date':entry.get('date','')} for entry in entries] for track,entries in data.items()}
