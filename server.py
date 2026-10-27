"""AchieveX local server. Standard library only; secrets never enter dist/."""
import csv, hashlib, hmac, io, json, math, os, re, secrets, sqlite3, threading, time
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
from urllib.parse import urlparse, parse_qs
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
ROOT = Path(__file__).resolve().parent
for line in (ROOT / '.env').read_text().splitlines() if (ROOT / '.env').exists() else []:
    if '=' in line and not line.lstrip().startswith('#'):
        k, v = line.split('=', 1); os.environ.setdefault(k.strip(), v.strip().strip('"\''))
CLOUD = os.getenv('VERCEL') == '1'
URL = os.getenv('SUPABASE_URL', '').rstrip('/')
KEY = os.getenv('SUPABASE_SECRET_KEY', '')
PIN_HASH = hashlib.sha256(os.getenv('ADMIN_PIN', '135790').encode()).digest()
DB = ROOT / '.data' / 'achievex.sqlite3'
LOCK = threading.RLock()
SESSIONS, ATTEMPTS = {}, {}
class ValidationError(Exception): pass
class StorageError(Exception): pass

def connection():
    if CLOUD: raise StorageError('Connect Supabase in Vercel environment variables to enable storage.')
    DB.parent.mkdir(exist_ok=True)
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
    c.execute('create table if not exists participants (sic text primary key, data text not null)')
    c.execute('create table if not exists settings (id integer primary key, published_week integer not null)')
    c.execute('insert or ignore into settings values (1,0)'); c.commit(); return c

def remote(path, method='GET', body=None):
    if not URL.startswith('https://') or not KEY: raise StorageError('Complete both Supabase settings in .env, then restart.')
    headers = {'apikey': KEY, 'Content-Type': 'application/json', 'Prefer':'return=representation'}
    if KEY.startswith('eyJ'): headers['Authorization'] = 'Bearer ' + KEY
    try:
        with urlopen(Request(URL+'/rest/v1/'+path, data=json.dumps(body).encode() if body is not None else None, headers=headers, method=method), timeout=20) as r:
            data=r.read(); return json.loads(data) if data else None
    except (HTTPError, URLError, TimeoutError) as e:
        raise StorageError('Supabase request failed. Check credentials and run supabase/schema.sql. No local fallback was used.') from e

def all_rows():
    if URL or KEY:
        rows=[]; offset=0
        while True:
            page=remote(f'participants?select=*&order=sic&limit=1000&offset={offset}'); rows.extend(page)
            if len(page)<1000: return rows
            offset+=1000
    with connection() as c: return [json.loads(r['data']) for r in c.execute('select data from participants order by sic')]
def get_week():
    if URL or KEY:
        r=remote('competition_settings?id=eq.1&select=published_week'); return r[0]['published_week'] if r else 0
    with connection() as c: return c.execute('select published_week from settings where id=1').fetchone()[0]
def save_rows(rows):
    if URL or KEY: remote('rpc/import_participants', 'POST', {'records':rows}); return
    with LOCK, connection() as c:
        c.executemany('insert into participants values (?,?) on conflict(sic) do update set data=excluded.data', [(r['sic'],json.dumps(r)) for r in rows])
def set_week(week):
    if URL or KEY: remote('competition_settings?id=eq.1','PATCH',{'published_week':week}); return
    with connection() as c: c.execute('update settings set published_week=? where id=1',(week,))

def validate(raw):
    def text(key, required=True, maxlen=120):
        v=str(raw.get(key,'') or '').strip()
        if required and not v: raise ValidationError(key.replace('_',' ').title()+' is required.')
        if len(v)>maxlen or any(ord(x)<32 for x in v): raise ValidationError('Invalid '+key+'.')
        return v
    r={'full_name':text('full_name'), 'sic':text('sic').lower(), 'email':text('email').lower(), 'contact':text('contact',maxlen=24), 'gender':text('gender',False,40),'branch':text('branch',maxlen=80)}
    if not re.fullmatch(r'[a-z0-9]{5,24}',r['sic']): raise ValidationError('SIC must contain 5–24 letters or numbers.')
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',r['email']): raise ValidationError('Enter a valid Silicon email address.')
    if not re.fullmatch(r'\+?[0-9 ()-]{7,24}',r['contact']) or not 7<=len(re.sub(r'\D','',r['contact']))<=15: raise ValidationError('Enter a valid contact number.')
    try: r['year']=int(str(raw.get('year','')))
    except (ValueError,TypeError): raise ValidationError('Year must be 1, 2, 3 or 4.')
    if r['year'] not in (1,2,3,4): raise ValidationError('Year must be 1, 2, 3 or 4.')
    r['track']='junior' if r['year']==1 else str(raw.get('track','')).strip().lower()
    if r['track'] not in ('junior','cs','core') or (r['year']>1 and r['track']=='junior'): raise ValidationError('Choose CS or Core for a senior student.')
    for i in range(1,6):
        value=raw.get('week'+str(i))
        if value is None or str(value).strip()=='': r['week'+str(i)]=None; continue
        if isinstance(value,bool): raise ValidationError('Invalid weekly score.')
        try: value=float(value)
        except (TypeError,ValueError): raise ValidationError('Weekly scores must be numbers from 0 to 100.')
        if not math.isfinite(value) or not 0<=value<=100: raise ValidationError('Weekly scores must be from 0 to 100.')
        r['week'+str(i)]=round(value,2)
    return r

def total(r,week=5): return round(sum(r.get('week'+str(i)) or 0 for i in range(1,week+1)),2)
def public_results():
    if CLOUD and not (URL or KEY): return {'published_week':0,'participants':[], 'setup_pending':True}
    week=get_week(); rows=all_rows(); result=[]
    for r in rows:
        # Personal contact details never appear in this projection.
        result.append({'full_name':r['full_name'],'sic':r['sic'],'year':r['year'],'track':r['track'],'scores':[r.get('week'+str(i)) if i<=week else None for i in range(1,6)],'total':total(r,week)})
    return {'published_week':week,'participants':result}

ALIASES={'full name':'full_name','silicon mail id':'email','silicon mail':'email','contact number':'contact','current year of study':'year','current year':'year','branch':'branch','sic':'sic','gender':'gender','track':'track'}
def parse_csv(content):
    if not isinstance(content,str) or len(content)>2_000_000: raise ValidationError('CSV is missing or exceeds 2 MB.')
    reader=csv.DictReader(io.StringIO(content.lstrip('\ufeff')))
    if not reader.fieldnames: raise ValidationError('CSV needs a header row.')
    headers=[]
    for h in reader.fieldnames:
        label=h.strip().lower().replace('*','').strip(); compact=re.sub(r'[ _-]','',label)
        headers.append('week'+compact[-1] if re.fullmatch(r'(week|w)[1-5]',compact) else ALIASES.get(label,label))
    if len(headers)!=len(set(headers)): raise ValidationError('Duplicate CSV columns.')
    required={'full_name','sic','email','contact','year','branch'}
    if not required.issubset(headers): raise ValidationError('Missing columns: '+', '.join(sorted(required-set(headers))))
    rows=[]; seen=set()
    for line,item in enumerate(reader,2):
        if line>1001: raise ValidationError('Import at most 1,000 students per file.')
        if None in item: raise ValidationError(f'Row {line}: extra CSV columns.')
        raw=dict(zip(headers,item.values()))
        if not any(v and str(v).strip() for v in raw.values()): continue
        try: r=validate(raw)
        except ValidationError as e: raise ValidationError(f'Row {line}: {e}')
        if r['sic'] in seen: raise ValidationError(f'Row {line}: duplicate SIC {r["sic"]}.')
        seen.add(r['sic']); rows.append(r)
    if not rows: raise ValidationError('CSV contains no participants.')
    return rows

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT/'dist'),**kwargs)
    def end_headers(self):
        self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Referrer-Policy','same-origin');super().end_headers()
    def json_response(self,data,status=200,cookie=None):
        self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store')
        if cookie:self.send_header('Set-Cookie',cookie)
        self.end_headers();self.wfile.write(json.dumps(data).encode())
    def authorized(self):
        if CLOUD:
            try:
                cookie=SimpleCookie(self.headers.get('Cookie',''));token=cookie['ax_admin'].value
                expires,nonce,signature=token.split('.')
                secret=os.getenv('SESSION_SECRET','')
                expected=hmac.new(secret.encode(),(expires+'.'+nonce).encode(),hashlib.sha256).hexdigest()
                if secret and int(expires)>time.time() and hmac.compare_digest(expected,signature): return token
            except (KeyError,ValueError): pass
            return None
        try:
            cookie=SimpleCookie(self.headers.get('Cookie','')); token=cookie['ax_admin'].value
            with LOCK:
                expires=SESSIONS.get(token,0)
                if expires>time.time(): return token
                SESSIONS.pop(token,None)
        except (KeyError,ValueError):pass
        return None
    def read_body(self):
        try:n=int(self.headers.get('Content-Length','0'))
        except ValueError:raise ValidationError('Invalid body.')
        if n>2_100_000:raise ValidationError('Request too large.')
        try:return json.loads(self.rfile.read(n))
        except (ValueError,UnicodeError):raise ValidationError('Invalid JSON.')
    def do_GET(self):
        path=urlparse(self.path).path
        if not path.startswith('/api/'):
            if path=='/admin':self.path='/admin.html'
            return super().do_GET()
        try:
            if path=='/api/leaderboard':return self.json_response(public_results())
            if not self.authorized():return self.json_response({'error':'Unlock the admin panel first.'},401)
            if path=='/api/admin/session':return self.json_response({'authenticated':True,'storage':'supabase' if URL or KEY else 'sqlite','published_week':get_week()})
            if path=='/api/admin/participants':return self.json_response({'participants':[{**r,'total':total(r)} for r in all_rows()]})
            return self.json_response({'error':'Not found'},404)
        except StorageError as e:return self.json_response({'error':str(e)},503)
    def do_POST(self):self.mutate()
    def do_PUT(self):self.mutate()
    def mutate(self):
        origin=self.headers.get('Origin')
        if origin and urlparse(origin).netloc!=self.headers.get('Host'):return self.json_response({'error':'Invalid origin.'},403)
        if self.headers.get('Sec-Fetch-Site')=='cross-site':return self.json_response({'error':'Invalid origin.'},403)
        path=urlparse(self.path).path
        try:
            body=self.read_body()
            if not isinstance(body,dict):raise ValidationError('Expected JSON object.')
            if path=='/api/admin/login':
                if CLOUD and not (URL and KEY and os.getenv('ADMIN_PIN') and os.getenv('SESSION_SECRET')):
                    return self.json_response({'error':'Admin setup pending. Configure Supabase, ADMIN_PIN and SESSION_SECRET in Vercel, then redeploy.'},503)
                ip=self.client_address[0];now=time.time()
                with LOCK:
                    failed=[t for t in ATTEMPTS.get(ip,[]) if now-t<600];ATTEMPTS[ip]=failed
                    if len(failed)>=6:return self.json_response({'error':'Too many attempts. Try again in 10 minutes.'},429)
                    if not hmac.compare_digest(hashlib.sha256(str(body.get('pin','')).encode()).digest(),PIN_HASH):
                        failed.append(now);return self.json_response({'error':'Incorrect PIN.'},401)
                    ATTEMPTS.pop(ip,None);token=secrets.token_urlsafe(32);SESSIONS[token]=now+28800
                    if CLOUD:
                        payload=str(int(now+28800))+'.'+secrets.token_hex(12)
                        token=payload+'.'+hmac.new(os.environ['SESSION_SECRET'].encode(),payload.encode(),hashlib.sha256).hexdigest()
                return self.json_response({'ok':True},cookie=f'ax_admin={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800'+('; Secure' if CLOUD else ''))
            token=self.authorized()
            if not token:return self.json_response({'error':'Session expired. Unlock the panel again.'},401)
            if path=='/api/admin/logout':
                with LOCK:SESSIONS.pop(token,None)
                return self.json_response({'ok':True},cookie='ax_admin=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'+('; Secure' if CLOUD else ''))
            if path=='/api/admin/participant':
                row=validate(body);existing={r['sic'] for r in all_rows()}
                if not body.get('editing') and row['sic'] in existing:raise ValidationError('This SIC already exists. Use Edit to update it.')
                save_rows([row]);return self.json_response({'ok':True,'total':total(row)})
            if path=='/api/admin/import':
                rows=parse_csv(body.get('csv'));existing={r['sic'] for r in all_rows()};updates=sum(r['sic'] in existing for r in rows)
                if body.get('commit') is True:save_rows(rows)
                return self.json_response({'count':len(rows),'new':len(rows)-updates,'updates':updates,'saved':body.get('commit') is True})
            if path=='/api/admin/settings':
                week=body.get('published_week')
                if isinstance(week,bool) or not isinstance(week,int) or not 0<=week<=5:raise ValidationError('Published week must be 0–5.')
                set_week(week);return self.json_response({'ok':True,'published_week':week})
            return self.json_response({'error':'Not found'},404)
        except ValidationError as e:return self.json_response({'error':str(e)},400)
        except StorageError as e:return self.json_response({'error':str(e)},503)
    def log_message(self,fmt,*args):pass
if __name__=='__main__':
    if not(URL or KEY):connection().close()
    print(f'AchieveX running at http://localhost:{os.getenv("PORT","4173")} — '+('Supabase' if URL or KEY else 'local SQLite'),flush=True)
    ThreadingHTTPServer(('127.0.0.1',int(os.getenv('PORT','4173'))),Handler).serve_forever()
