import importlib.util, json, tempfile, threading, unittest
from pathlib import Path
from urllib.request import Request, urlopen, build_opener, HTTPCookieProcessor
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
from http.cookiejar import CookieJar
spec=importlib.util.spec_from_file_location('appserver',Path(__file__).resolve().parents[1]/'server.py');app=importlib.util.module_from_spec(spec);spec.loader.exec_module(app)

def student(sic='24beca53',**kwargs):
    return dict(full_name='Test Student',sic=sic,email='student@silicon.ac.in',contact='9876543210',gender='',year=3,branch='CSE',track='cs',week1=88,week2=91,week3=97,week4=None,week5=None,**kwargs)
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();app.DB=Path(cls.tmp.name)/'test.sqlite3';app.URL='';app.KEY=''
        cls.http=ThreadingHTTPServer(('127.0.0.1',0),app.Handler);cls.base='http://127.0.0.1:'+str(cls.http.server_port)
        threading.Thread(target=cls.http.serve_forever,daemon=True).start()
    @classmethod
    def tearDownClass(cls):cls.http.shutdown();cls.http.server_close();cls.tmp.cleanup()
    def setUp(self):
        app.SESSIONS.clear();app.ATTEMPTS.clear()
        with app.connection() as c:c.execute('delete from participants');c.execute('update settings set published_week=0')
        self.client=build_opener(HTTPCookieProcessor(CookieJar()))
    def call(self,path,body=None,client=None,headers=None):
        req=Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json',**(headers or {})})
        try:
            with (client or self.client).open(req) as r:return r.status,json.load(r)
        except HTTPError as e:return e.code,json.load(e)
    def login(self):self.assertEqual(self.call('/api/admin/login',{'pin':'135790'})[0],200)
    def test_pin_and_private_routes(self):
        self.assertEqual(self.call('/api/admin/participants')[0],401)
        self.assertEqual(self.call('/api/admin/participant',student())[0],401)
        self.assertEqual(self.call('/api/admin/login',{'pin':'000000'})[0],401)
        self.login();self.assertEqual(self.call('/api/admin/participants')[0],200)
        self.call('/api/admin/logout',{});self.assertEqual(self.call('/api/admin/participants')[0],401)
    def test_rate_limit(self):
        for _ in range(6):self.call('/api/admin/login',{'pin':'bad'})
        self.assertEqual(self.call('/api/admin/login',{'pin':'135790'})[0],429)
    def test_cross_origin(self):
        self.assertEqual(self.call('/api/admin/login',{'pin':'135790'},headers={'Origin':'https://outside.example'})[0],403)
    def test_score_bounds(self):
        for bad in [-1,100.01,'NaN','Infinity',True]:
            r=student();r['week1']=bad
            with self.assertRaises(app.ValidationError):app.validate(r)
        r=student();r['week1']='0';r['week2']='';v=app.validate(r);self.assertEqual(v['week1'],0);self.assertIsNone(v['week2'])
    def test_totals_and_duplicates(self):
        self.login();r=student()
        self.assertEqual(self.call('/api/admin/participant',r)[1]['total'],276)
        self.assertEqual(self.call('/api/admin/participant',r)[0],400)
        r.update(editing=True,week4=100,week5=100);self.assertEqual(self.call('/api/admin/participant',r)[1]['total'],476)
        r.update(week1=100,week2=100,week3=100);self.assertEqual(self.call('/api/admin/participant',r)[1]['total'],500)
    def test_public_projection_and_publish(self):
        app.save_rows([app.validate(student())]);app.set_week(2)
        status,data=self.call('/api/leaderboard');self.assertEqual(status,200);r=data['participants'][0]
        self.assertEqual(r['total'],179);self.assertEqual(r['scores'],[88,91,None,None,None])
        for field in ('email','contact','gender'):self.assertNotIn(field,r)
    def test_csv_preview_atomic_and_update(self):
        self.login();header='Full Name,SIC,Silicon Mail Id,Contact Number,Current Year of Study,Branch,Track,Week 1,Week 2,Week 3,Week 4,Week 5\n'
        valid='Test,24beca53,t@silicon.ac.in,9876543210,3,CSE,cs,90,0,,,\n'
        text=header+valid
        self.assertEqual(self.call('/api/admin/import',{'csv':text,'commit':False})[1]['count'],1);self.assertEqual(len(app.all_rows()),0)
        invalid=text+'Bad,24beca54,b@silicon.ac.in,9876543210,3,CSE,cs,101,,,,\n'
        self.assertEqual(self.call('/api/admin/import',{'csv':invalid,'commit':True})[0],400);self.assertEqual(len(app.all_rows()),0)
        self.assertEqual(self.call('/api/admin/import',{'csv':text,'commit':True})[0],200)
        self.assertEqual(self.call('/api/admin/import',{'csv':text,'commit':False})[1]['updates'],1)
    def test_junior_and_track(self):
        r=student();r['year']=1;r['track']='cs';self.assertEqual(app.validate(r)['track'],'junior')
        r['year']=3;r['track']='junior'
        with self.assertRaises(app.ValidationError):app.validate(r)
    def test_settings(self):
        self.login()
        for bad in (-1,6,2.5,True):self.assertEqual(self.call('/api/admin/settings',{'published_week':bad})[0],400)
        self.assertEqual(self.call('/api/admin/settings',{'published_week':5})[0],200)
    def test_delete_requires_auth_and_confirmation(self):
        row=app.validate(student());app.save_rows([row])
        self.assertEqual(self.call('/api/admin/delete',{'sic':row['sic'],'confirm':True})[0],401)
        self.login()
        self.assertEqual(self.call('/api/admin/delete',{'sic':row['sic']})[0],400)
        self.assertEqual(len(app.all_rows()),1)
        self.assertEqual(self.call('/api/admin/delete',{'sic':row['sic'],'confirm':True})[0],200)
        self.assertEqual(len(app.all_rows()),0)
        self.assertEqual(self.call('/api/admin/delete',{'sic':row['sic'],'confirm':True})[0],404)
    def test_schedule_visibility_and_validation(self):
        import schedule_config
        schedule=schedule_config.defaults()
        hidden=schedule_config.public(schedule)
        self.assertNotIn('subject',hidden['junior'][0])
        schedule['junior'][0].update(subject='C Programming',scope='Loops and functions',revealed=True)
        checked=schedule_config.validate(schedule)
        self.assertEqual(schedule_config.public(checked)['junior'][0]['subject'],'C Programming')
        schedule['junior'][0]['syllabus_url']='javascript:alert(1)'
        with self.assertRaises(ValueError):schedule_config.validate(schedule)
    def test_schedule_routes_are_private(self):
        self.assertEqual(self.call('/api/admin/schedule')[0],401)
        self.assertEqual(self.call('/api/admin/schedule',{'schedule':{}})[0],401)
        self.login()
        self.assertEqual(self.call('/api/admin/schedule',{'schedule':{}})[0],400)
    def test_csv_duplicate(self):
        csv='full_name,sic,email,contact,year,branch,track\nA,24beca53,a@silicon.ac.in,9876543210,3,CSE,cs\nB,24beca53,b@silicon.ac.in,9876543210,3,CSE,cs\n'
        with self.assertRaises(app.ValidationError):app.parse_csv(csv)
if __name__=='__main__':unittest.main()
