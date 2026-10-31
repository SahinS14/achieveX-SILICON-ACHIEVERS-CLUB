"""AchieveX local server. Standard library only; secrets never enter dist/."""
import csv, hashlib, hmac, io, json, math, os, re, secrets, sqlite3, threading, time
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
from urllib.parse import urlparse, parse_qs
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import schedule_config, security_store
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

BADGE_DEFINITIONS = [
    {
        'id': 'the-main-character',
        'name': 'The Main Character',
        'icon': '👑',
        'description': 'Current category leader by published cumulative score; final champion after Week 5.',
        'category': 'ranking',
        'criteria': 'Highest cumulative score within your category across published weeks. Missing scores count as zero; at least one graded result is required. Ties share the badge.',
        'image_url': '/assets/badges/the-main-character.png'
    },
    {
        'id': 'the-ace',
        'name': 'The Ace',
        'icon': '⚡',
        'description': 'Highest scorer in an individual weekly exam.',
        'category': 'ranking',
        'criteria': 'Highest score in your category for each published weekly exam. Ties share the badge; multiple weekly awards are retained.',
        'image_url': '/assets/badges/the-ace.png'
    },
    {
        'id': 'the-glow-up',
        'name': 'The Glow Up',
        'icon': '📈',
        'description': 'Biggest improvement compared with the previous weekly exam.',
        'category': 'ranking',
        'criteria': 'Largest positive gain in your category for each consecutive published exam pair. Both scores must be graded. Ties share the badge.',
        'image_url': '/assets/badges/the-glow-up.png'
    },
    {
        'id': 'on-fire',
        'name': 'On Fire',
        'icon': '🔥',
        'description': 'Consistently scores at least 80% across three consecutive weekly exams.',
        'category': 'milestone',
        'criteria': 'Score 80% or higher in any three consecutive finalized weekly exams.',
        'image_url': '/assets/badges/on-fire.png'
    },
    {
        'id': 'flawless',
        'name': 'Flawless',
        'icon': '💎',
        'description': 'Achieved a perfect score in a weekly exam.',
        'category': 'milestone',
        'criteria': 'Achieve a perfect 100% score in any verified weekly exam.',
        'image_url': '/assets/badges/flawless.png'
    },
    {
        'id': 'the-comeback-arc',
        'name': 'The Comeback Arc',
        'icon': '🚀',
        'description': 'Makes a remarkable recovery after a low scoring exam.',
        'category': 'milestone',
        'criteria': 'Score strictly below 50% in one exam and improve by at least 20 percentage points in the next exam.',
        'image_url': '/assets/badges/the-comeback-arc.png'
    },
    {
        'id': 'the-unlocked-five',
        'name': 'The Unlocked Five',
        'icon': '🔒',
        'description': 'Has graded results in all five published weekly exams.',
        'category': 'milestone',
        'criteria': 'All five weeks must be published and graded. A graded zero counts; a blank score does not. Scores serve as the participation record.',
        'image_url': '/assets/badges/the-unlocked-five.png'
    }
]

def connection():
    if CLOUD: raise StorageError('Connect Supabase in Vercel environment variables to enable storage.')
    DB.parent.mkdir(exist_ok=True)
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
    c.execute('create table if not exists participants (sic text primary key, data text not null)')
    c.execute('create table if not exists settings (id integer primary key, published_week integer not null)')
    c.execute('insert or ignore into settings values (1,0)')
    c.execute('''create table if not exists badge_definitions (
        id text primary key,
        name text not null,
        icon text not null,
        description text not null,
        category text not null,
        criteria text not null,
        image_url text not null
    )''')
    c.execute('''create table if not exists student_badges (
        student_sic text not null,
        badge_id text not null,
        award_date text not null,
        qualifying_exam_id text not null default '',
        evidence text not null default '',
        is_active integer not null default 1,
        primary key (student_sic, badge_id, qualifying_exam_id)
    )''')
    c.execute('create index if not exists idx_student_badges_student on student_badges(student_sic)')
    c.execute('create index if not exists idx_student_badges_badge on student_badges(badge_id)')
    for b in BADGE_DEFINITIONS:
        c.execute('insert into badge_definitions values (?,?,?,?,?,?,?) on conflict(id) do update set name=excluded.name,icon=excluded.icon,description=excluded.description,category=excluded.category,criteria=excluded.criteria,image_url=excluded.image_url',
                  (b['id'],b['name'],b['icon'],b['description'],b['category'],b['criteria'],b['image_url']))
    c.commit(); return c

def _evaluate_category_badges(rows=None, published_week=None, max_marks=None):
    if rows is None: rows = all_rows()
    if published_week is None: published_week = get_week()
    if max_marks is None: max_marks = {1:100.0, 2:100.0, 3:100.0, 4:100.0, 5:100.0}
    for m in max_marks.values():
        if m <= 0: raise ValidationError('Maximum exam score must be greater than zero.')

    # Score normalization: p_{s,i} = (x_{s,i} / m_i) * 100
    norm_scores = {}
    for r in rows:
        sic = r['sic']
        norm_scores[sic] = {}
        for i in range(1, 6):
            val = r.get('week' + str(i))
            if val is not None:
                m_i = float(max_marks.get(i, 100.0))
                norm_scores[sic][i] = (float(val) / m_i) * 100.0
            else:
                norm_scores[sic][i] = None

    awards = []
    N = int(published_week)

    # Badge 1: The Main Character 👑
    # Average percentage across the same set of eligible, finalized exams (1..N).
    # Missing published scores count as zero, matching cumulative standings.
    if N >= 1:
        averages = {}
        for r in rows:
            sic = r['sic']
            scores_n = [norm_scores[sic][i] for i in range(1, N + 1)]
            if any(s is not None for s in scores_n):
                averages[sic] = sum(s or 0 for s in scores_n) / N
        if averages:
            max_avg = max(averages.values())
            for sic, avg in averages.items():
                if math.isclose(avg, max_avg, rel_tol=1e-9, abs_tol=1e-9):
                    awards.append({
                        'student_sic': sic,
                        'badge_id': 'the-main-character',
                        'qualifying_exam_id': f'weeks1-{N}',
                        'evidence': f'Highest cumulative average: {avg:.2f}% across {N} finalized exams',
                        'category': 'ranking'
                    })

    # Badge 2: The Ace ⚡
    # Highest scorer in an individual weekly exam. Evaluate each exam independently.
    for i in range(1, N + 1):
        exam_scores = {r['sic']: norm_scores[r['sic']][i] for r in rows if norm_scores[r['sic']][i] is not None}
        if exam_scores:
            max_score = max(exam_scores.values())
            for sic, score in exam_scores.items():
                if math.isclose(score, max_score, rel_tol=1e-9, abs_tol=1e-9):
                    awards.append({
                        'student_sic': sic,
                        'badge_id': 'the-ace',
                        'qualifying_exam_id': f'week{i}',
                        'evidence': f'Top score in Week {i}: {score:.2f}%',
                        'category': 'ranking'
                    })

    # One improvement award per category and consecutive published exam pair.
    for i in range(2,N+1):
        gains=[]
        for r in rows:
            previous,current=norm_scores[r['sic']][i-1],norm_scores[r['sic']][i]
            if previous is not None and current is not None and current>previous:
                gains.append((current-previous,r['sic']))
        best=max((gain for gain,_ in gains),default=0)
        for gain,sic in gains:
            if math.isclose(gain,best,rel_tol=1e-9,abs_tol=1e-9):
                awards.append({'student_sic':sic,'badge_id':'the-glow-up','qualifying_exam_id':f'week{i}','evidence':f'Largest category improvement: +{gain:.2f} points (Week {i-1} to Week {i})','category':'ranking'})

    # Badge 4: On Fire 🔥
    # Consistently scores >= 80% across three consecutive weekly exams.
    if N >= 3:
        for r in rows:
            sic = r['sic']
            for i in range(1, N - 1):
                s1, s2, s3 = norm_scores[sic][i], norm_scores[sic][i + 1], norm_scores[sic][i + 2]
                if s1 is not None and s2 is not None and s3 is not None:
                    if s1 >= 80.0 and s2 >= 80.0 and s3 >= 80.0:
                        awards.append({
                            'student_sic': sic,
                            'badge_id': 'on-fire',
                            'qualifying_exam_id': f'week{i}-week{i+2}',
                            'evidence': f'Scored >= 80% in 3 consecutive exams (Weeks {i}–{i+2}: {s1:.1f}%, {s2:.1f}%, {s3:.1f}%)',
                            'category': 'milestone'
                        })

    # Badge 5: Flawless 💎
    # Achieved a perfect score in a weekly exam (100%).
    for r in rows:
        sic = r['sic']
        for i in range(1, N + 1):
            s = norm_scores[sic][i]
            if s is not None and math.isclose(s, 100.0, rel_tol=1e-9, abs_tol=1e-9):
                awards.append({
                    'student_sic': sic,
                    'badge_id': 'flawless',
                    'qualifying_exam_id': f'week{i}',
                    'evidence': f'Perfect 100% score in Week {i}',
                    'category': 'milestone'
                })

    # Badge 6: The Comeback Arc 🚀
    # Previous exam score strictly below 50%, and next consecutive exam improves by at least 20 percentage points.
    if N >= 2:
        for r in rows:
            sic = r['sic']
            for i in range(2, N + 1):
                prev = norm_scores[sic][i - 1]
                curr = norm_scores[sic][i]
                if prev is not None and curr is not None:
                    if prev < 50.0 and (curr - prev) >= 20.0:
                        awards.append({
                            'student_sic': sic,
                            'badge_id': 'the-comeback-arc',
                            'qualifying_exam_id': f'week{i}',
                            'evidence': f'Recovery from {prev:.1f}% in Week {i-1} to {curr:.1f}% in Week {i} (+{(curr-prev):.1f} pts)',
                            'category': 'milestone'
                        })

    # Badge 7: The Unlocked Five 🔒
    # Participated in all five required weekly exams. Score 0 can qualify if student participated; missing does not.
    for r in rows:
        sic = r['sic']
        participations = [r.get('week' + str(i)) is not None for i in range(1, 6)]
        if N == 5 and all(participations):
            awards.append({
                'student_sic': sic,
                'badge_id': 'the-unlocked-five',
                'qualifying_exam_id': 'weeks1-5',
                'evidence': 'Verified participation across all five championship exams',
                'category': 'milestone'
            })

    return awards

def evaluate_badges(rows=None,published_week=None,max_marks=None):
    rows=all_rows() if rows is None else rows
    week=get_week() if published_week is None else published_week
    if isinstance(week,bool) or not isinstance(week,int) or not 0<=week<=5:raise ValidationError('Published week must be 0–5.')
    marks=max_marks or {i:100 for i in range(1,6)}
    for i in range(1,6):
        m=marks.get(i,100)
        if isinstance(m,bool) or not isinstance(m,(int,float)) or not math.isfinite(m) or m<=0:raise ValidationError('Invalid maximum marks.')
        for row in rows:
            value=row.get('week'+str(i))
            if value is not None and (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=m):raise ValidationError('Invalid weekly score in stored data.')
    awards=[]
    for track in ('junior','cs','core'):
        group=[r for r in rows if r.get('track')==track]
        awards.extend(_evaluate_category_badges(group,week,marks))
    return awards

def evaluate_and_save_badges(max_marks=None):
    if URL or KEY: return
    rows = all_rows()
    week = get_week()
    awards = evaluate_badges(rows, week, max_marks)
    today = time.strftime('%Y-%m-%d')
    with LOCK, connection() as c:
        # Inactivate previous ranking awards; only current ranking leaders are active
        c.execute("update student_badges set is_active=0 where badge_id in ('the-main-character', 'the-ace', 'the-glow-up')")
        # For milestones, inactivate if underlying scores no longer qualify (e.g. score corrected or invalidated)
        active_keys = {(a['student_sic'], a['badge_id'], a['qualifying_exam_id']) for a in awards}
        milestones = ('on-fire', 'flawless', 'the-comeback-arc', 'the-unlocked-five')
        placeholders = ','.join('?' for _ in milestones)
        for r in c.execute(f"select student_sic, badge_id, qualifying_exam_id from student_badges where is_active=1 and badge_id in ({placeholders})", milestones).fetchall():
            if (r['student_sic'], r['badge_id'], r['qualifying_exam_id']) not in active_keys:
                c.execute('update student_badges set is_active=0 where student_sic=? and badge_id=? and qualifying_exam_id=?',
                          (r['student_sic'], r['badge_id'], r['qualifying_exam_id']))
        for a in awards:
            c.execute('''insert into student_badges (student_sic, badge_id, award_date, qualifying_exam_id, evidence, is_active)
                         values (?, ?, ?, ?, ?, 1)
                         on conflict(student_sic, badge_id, qualifying_exam_id) do update set
                             evidence=excluded.evidence,
                             is_active=1''',
                      (a['student_sic'], a['badge_id'], today, a['qualifying_exam_id'], a['evidence']))
        c.commit()

def get_student_badges_map(rows=None,published_week=None):
    definitions={b['id']:b for b in BADGE_DEFINITIONS};result={}
    for award in evaluate_badges(rows,published_week):
        sic,bid=award['student_sic'],award['badge_id'];key=award['qualifying_exam_id']
        history={'award_date':'Published '+key,'qualifying_exam_id':key,'evidence':award['evidence']}
        items=result.setdefault(sic,[]);existing=next((b for b in items if b['id']==bid),None)
        if existing:
            existing['count']+=1;existing['history'].append(history)
        else:items.append({**definitions[bid],**history,'count':1,'history':[history]})
    return result

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
    evaluate_and_save_badges()
def delete_row(sic):
    if not re.fullmatch(r'[a-z0-9]{5,24}',sic): raise ValidationError('Invalid SIC.')
    if URL or KEY:
        deleted=remote('participants?sic=eq.'+sic,'DELETE')
        return bool(deleted)
    with LOCK, connection() as c:
        c.execute('delete from student_badges where student_sic=?', (sic,))
        deleted = c.execute('delete from participants where sic=?',(sic,)).rowcount>0
    if deleted:
        evaluate_and_save_badges()
    return deleted

def set_week(week):
    if URL or KEY: remote('competition_settings?id=eq.1','PATCH',{'published_week':week}); return
    with connection() as c: c.execute('update settings set published_week=? where id=1',(week,))
    evaluate_and_save_badges()

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
        r['week'+str(i)]=float(Decimal(str(raw.get('week'+str(i)))).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP))
    return r

def total(r,week=5): return float(sum((Decimal(str(r.get('week'+str(i)) or 0)) for i in range(1,week+1)),Decimal(0)).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP))
def public_results():
    if CLOUD and not (URL or KEY): return {'published_week':0,'participants':[], 'setup_pending':True, 'badge_definitions':BADGE_DEFINITIONS}
    week=get_week(); rows=all_rows(); result=[]
    badges_map = get_student_badges_map(rows,week)
    for r in rows:
        # Personal contact details never appear in this projection.
        result.append({
            'full_name':r['full_name'],
            'sic':r['sic'],
            'year':r['year'],
            'track':r['track'],
            'scores':[r.get('week'+str(i)) if i<=week else None for i in range(1,6)],
            'total':total(r,week),
            'badges':badges_map.get(r['sic'], [])
        })
    return {'published_week':week,'participants':result, 'badge_definitions':BADGE_DEFINITIONS}

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
        if not self.path.startswith('/api/'): self.send_header('Cache-Control','no-cache')
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
                if secret and int(expires)>time.time() and hmac.compare_digest(expected,signature) and security_store.session(URL,KEY,secret,token): return token
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
        if n<0:raise ValidationError('Invalid body length.')
        if n>2_100_000:raise ValidationError('Request too large.')
        try:return json.loads(self.rfile.read(n))
        except (ValueError,UnicodeError):raise ValidationError('Invalid JSON.')
    def do_GET(self):
        path=urlparse(self.path).path
        if not path.startswith('/api/'):
            if path=='/admin':self.path='/admin.html'
            return super().do_GET()
        try:
            if path=='/api/schedule':
                return self.json_response({'schedule':schedule_config.public(schedule_config.read(ROOT,URL,KEY))})
            if path=='/api/badges':return self.json_response({'badges':BADGE_DEFINITIONS})
            if path=='/api/leaderboard':return self.json_response(public_results())
            if not self.authorized():return self.json_response({'error':'Unlock the admin panel first.'},401)
            if path=='/api/admin/schedule':
                return self.json_response({'schedule':schedule_config.read(ROOT,URL,KEY),'presets':[{'name':n,'url':schedule_config.PDF+'#page='+str(p)} for n,p in schedule_config.PRESETS]})
            if path=='/api/admin/session':return self.json_response({'authenticated':True,'storage':'supabase' if URL or KEY else 'sqlite','published_week':get_week()})
            if path=='/api/admin/participants':return self.json_response({'participants':[{**r,'total':total(r)} for r in all_rows()]})
            return self.json_response({'error':'Not found'},404)
        except (StorageError,RuntimeError) as e:return self.json_response({'error':str(e)},503)
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
                if CLOUD:
                    ip=self.headers.get('x-vercel-forwarded-for',ip).split(',')[0].strip()
                    if not security_store.allow_attempt(URL,KEY,os.environ['SESSION_SECRET'],ip,now):
                        return self.json_response({'error':'Too many attempts. Try again in 10 minutes.'},429)
                with LOCK:
                    failed=[t for t in ATTEMPTS.get(ip,[]) if now-t<600];ATTEMPTS[ip]=failed
                    if len(failed)>=6:return self.json_response({'error':'Too many attempts. Try again in 10 minutes.'},429)
                    if not hmac.compare_digest(hashlib.sha256(str(body.get('pin','')).encode()).digest(),PIN_HASH):
                        failed.append(now);return self.json_response({'error':'Incorrect PIN.'},401)
                    ATTEMPTS.pop(ip,None);token=secrets.token_urlsafe(32);SESSIONS[token]=now+28800
                    if CLOUD:
                        payload=str(int(now+28800))+'.'+secrets.token_hex(12)
                        token=payload+'.'+hmac.new(os.environ['SESSION_SECRET'].encode(),payload.encode(),hashlib.sha256).hexdigest()
                        security_store.session(URL,KEY,os.environ['SESSION_SECRET'],token,'create',now+28800)
                return self.json_response({'ok':True},cookie=f'ax_admin={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800'+('; Secure' if CLOUD else ''))
            token=self.authorized()
            if not token:return self.json_response({'error':'Session expired. Unlock the panel again.'},401)
            if path=='/api/admin/logout':
                if CLOUD:security_store.session(URL,KEY,os.environ['SESSION_SECRET'],token,'revoke')
                with LOCK:SESSIONS.pop(token,None)
                return self.json_response({'ok':True},cookie='ax_admin=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'+('; Secure' if CLOUD else ''))
            if path=='/api/admin/participant':
                if not isinstance(body.get('editing',False),bool):raise ValidationError('Invalid editing flag.')
                row=validate(body);existing={r['sic'] for r in all_rows()}
                if body.get('editing') and row['sic'] not in existing:return self.json_response({'error':'Participant no longer exists. Add a new participant instead.'},404)
                if not body.get('editing') and row['sic'] in existing:raise ValidationError('This SIC already exists. Use Edit to update it.')
                save_rows([row]);return self.json_response({'ok':True,'total':total(row)})
            if path=='/api/admin/delete':
                sic=str(body.get('sic','')).strip().lower()
                if body.get('confirm') is not True: raise ValidationError('Confirm participant deletion.')
                if not delete_row(sic): return self.json_response({'error':'Participant no longer exists.'},404)
                return self.json_response({'ok':True})
            if path=='/api/admin/import':
                rows=parse_csv(body.get('csv'));existing={r['sic'] for r in all_rows()};updates=sum(r['sic'] in existing for r in rows)
                if body.get('commit') is True:save_rows(rows)
                return self.json_response({'count':len(rows),'new':len(rows)-updates,'updates':updates,'saved':body.get('commit') is True})
            if path=='/api/admin/schedule':
                try:schedule_config.save(ROOT,URL,KEY,body.get('schedule'))
                except ValueError as e:raise ValidationError(str(e))
                return self.json_response({'ok':True})
            if path=='/api/admin/settings':
                week=body.get('published_week')
                if isinstance(week,bool) or not isinstance(week,int) or not 0<=week<=5:raise ValidationError('Published week must be 0–5.')
                set_week(week);return self.json_response({'ok':True,'published_week':week})
            return self.json_response({'error':'Not found'},404)
        except ValidationError as e:return self.json_response({'error':str(e)},400)
        except (StorageError,RuntimeError) as e:return self.json_response({'error':str(e)},503)
    def log_message(self,fmt,*args):pass
if __name__=='__main__':
    if not(URL or KEY):connection().close()
    print(f'AchieveX running at http://localhost:{os.getenv("PORT","4173")} — '+('Supabase' if URL or KEY else 'local SQLite'),flush=True)
    ThreadingHTTPServer(('127.0.0.1',int(os.getenv('PORT','4173'))),Handler).serve_forever()
