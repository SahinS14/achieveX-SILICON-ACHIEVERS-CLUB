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
        with app.connection() as c:
            c.execute('delete from student_badges')
            c.execute('delete from participants')
            c.execute('update settings set published_week=0')
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

    # --- Achievement Badge Tests ---
    def test_badge_definitions_api(self):
        status, data = self.call('/api/badges')
        self.assertEqual(status, 200)
        badges = data.get('badges', [])
        self.assertEqual(len(badges), 7)
        badge_ids = {b['id'] for b in badges}
        expected = {'the-main-character', 'the-ace', 'the-glow-up', 'on-fire', 'flawless', 'the-comeback-arc', 'the-unlocked-five'}
        self.assertEqual(badge_ids, expected)

    def test_main_character_badge(self):
        # A & B have equal averages across 2 finalized exams -> both earn The Main Character
        # C has only 1 exam completed (100%), but missing week 2 -> excluded from comparison
        sA = student(sic='24beca01', week1=90, week2=90, week3=None, week4=None, week5=None)
        sB = student(sic='24beca02', week1=85, week2=95, week3=None, week4=None, week5=None)
        sC = student(sic='24beca03', week1=100, week2=None, week3=None, week4=None, week5=None)
        app.save_rows([app.validate(sA), app.validate(sB), app.validate(sC)])
        app.set_week(2)
        badges = app.get_student_badges_map()
        a_badges = [b['id'] for b in badges.get('24beca01', [])]
        b_badges = [b['id'] for b in badges.get('24beca02', [])]
        c_badges = [b['id'] for b in badges.get('24beca03', [])]
        self.assertIn('the-main-character', a_badges)
        self.assertIn('the-main-character', b_badges)
        self.assertNotIn('the-main-character', c_badges)

    def test_ace_badge_ties_and_multiple_exams(self):
        # Ties in week 1 -> both get Ace for week 1
        # Student A also tops week 2 -> gets multiple Ace awards preserved
        sA = student(sic='24beca01', week1=95, week2=98, week3=None)
        sB = student(sic='24beca02', week1=95, week2=70, week3=None)
        app.save_rows([app.validate(sA), app.validate(sB)])
        app.set_week(2)
        badges = app.get_student_badges_map()
        sA_ace = next(b for b in badges['24beca01'] if b['id'] == 'the-ace')
        sB_ace = next(b for b in badges['24beca02'] if b['id'] == 'the-ace')
        self.assertEqual(sA_ace['count'], 2) # Week 1 and Week 2
        self.assertEqual(sB_ace['count'], 1) # Week 1

    def test_ace_different_scales_and_normalization(self):
        s1 = student(sic='24beca01', week1=45) # 45 out of 50 = 90%
        s2 = student(sic='24beca02', week1=85) # 85 out of 100 = 85%
        eval_res = app.evaluate_badges([s1, s2], published_week=1, max_marks={1: 50.0})
        aces = [a for a in eval_res if a['badge_id'] == 'the-ace']
        self.assertEqual(len(aces), 1)
        self.assertEqual(aces[0]['student_sic'], '24beca01')

    def test_glow_up_badge(self):
        # sA improves by 30 (+30), sB improves by 30 (+30), sC improves by 10 (+10), sD decreases (-5)
        sA = student(sic='24beca01', week1=50, week2=80)
        sB = student(sic='24beca02', week1=60, week2=90)
        sC = student(sic='24beca03', week1=70, week2=80)
        sD = student(sic='24beca04', week1=80, week2=75)
        # sE has missing consecutive exam (week 1 to week 3 cannot be compared as consecutive)
        sE = student(sic='24beca05', week1=30, week2=None, week3=90)
        app.save_rows([app.validate(sA), app.validate(sB), app.validate(sC), app.validate(sD), app.validate(sE)])
        app.set_week(2)
        badges = app.get_student_badges_map()
        self.assertIn('the-glow-up', [b['id'] for b in badges.get('24beca01', [])])
        self.assertIn('the-glow-up', [b['id'] for b in badges.get('24beca02', [])])
        self.assertNotIn('the-glow-up', [b['id'] for b in badges.get('24beca03', [])])
        self.assertNotIn('the-glow-up', [b['id'] for b in badges.get('24beca04', [])])

    def test_glow_up_no_improvement(self):
        # If all students decrease or have 0 improvement, no Glow Up is awarded
        sA = student(sic='24beca01', week1=80, week2=80)
        sB = student(sic='24beca02', week1=90, week2=85)
        app.save_rows([app.validate(sA), app.validate(sB)])
        app.set_week(2)
        badges = app.get_student_badges_map()
        self.assertNotIn('the-glow-up', [b['id'] for b in badges.get('24beca01', [])])
        self.assertNotIn('the-glow-up', [b['id'] for b in badges.get('24beca02', [])])

    def test_on_fire_badge(self):
        # Exactly 80% qualifies across 3 consecutive exams
        s1 = student(sic='24beca01', week1=80, week2=80, week3=80)
        # Broken streak (79%) does not qualify
        s2 = student(sic='24beca02', week1=80, week2=79.9, week3=85)
        # Missing score in between does not qualify
        s3 = student(sic='24beca03', week1=85, week2=None, week3=85)
        app.save_rows([app.validate(s1), app.validate(s2), app.validate(s3)])
        app.set_week(3)
        badges = app.get_student_badges_map()
        self.assertIn('on-fire', [b['id'] for b in badges.get('24beca01', [])])
        self.assertNotIn('on-fire', [b['id'] for b in badges.get('24beca02', [])])
        self.assertNotIn('on-fire', [b['id'] for b in badges.get('24beca03', [])])

    def test_flawless_badge(self):
        # 100% in any verified weekly exam earns Flawless
        s1 = student(sic='24beca01', week1=100, week2=85)
        s2 = student(sic='24beca02', week1=99.5, week2=99.9)
        app.save_rows([app.validate(s1), app.validate(s2)])
        app.set_week(2)
        badges = app.get_student_badges_map()
        self.assertIn('flawless', [b['id'] for b in badges.get('24beca01', [])])
        self.assertNotIn('flawless', [b['id'] for b in badges.get('24beca02', [])])

    def test_comeback_arc_badge(self):
        # Previous score strictly below 50% and improves by >= 20 percentage points
        # 49% -> 69%: qualifies (prev < 50 and diff >= 20)
        s1 = student(sic='24beca01', week1=49, week2=69)
        # 50% -> 75%: does NOT qualify (previous is not strictly below 50%)
        s2 = student(sic='24beca02', week1=50, week2=75)
        # 40% -> 59%: does NOT qualify (diff 19 is < 20)
        s3 = student(sic='24beca03', week1=40, week2=59)
        app.save_rows([app.validate(s1), app.validate(s2), app.validate(s3)])
        app.set_week(2)
        badges = app.get_student_badges_map()
        self.assertIn('the-comeback-arc', [b['id'] for b in badges.get('24beca01', [])])
        self.assertNotIn('the-comeback-arc', [b['id'] for b in badges.get('24beca02', [])])
        self.assertNotIn('the-comeback-arc', [b['id'] for b in badges.get('24beca03', [])])

    def test_unlocked_five_badge(self):
        # Verified participation across all 5 exams (score 0 is valid participation; missing is not)
        s1 = student(sic='24beca01', week1=75, week2=0, week3=80, week4=85, week5=90)
        # Only 4 exams completed
        s2 = student(sic='24beca02', week1=80, week2=80, week3=80, week4=80, week5=None)
        app.save_rows([app.validate(s1), app.validate(s2)])
        app.set_week(5)
        badges = app.get_student_badges_map()
        self.assertIn('the-unlocked-five', [b['id'] for b in badges.get('24beca01', [])])
        self.assertNotIn('the-unlocked-five', [b['id'] for b in badges.get('24beca02', [])])

    def test_score_corrections_and_idempotency(self):
        # Student earned Flawless on Week 1 (100%).
        s = student(sic='24beca01', week1=100, week2=80)
        app.save_rows([app.validate(s)])
        app.set_week(2)
        self.assertIn('flawless', [b['id'] for b in app.get_student_badges_map().get('24beca01', [])])
        # Score correction: Week 1 score corrected to 98%
        s['week1'] = 98
        s['editing'] = True
        app.save_rows([app.validate(s)])
        # Flawless milestone badge should be invalidated/removed
        self.assertNotIn('flawless', [b['id'] for b in app.get_student_badges_map().get('24beca01', [])])
        # Running evaluator repeatedly produces identical result without duplicate records
        app.evaluate_and_save_badges()
        app.evaluate_and_save_badges()
        with app.connection() as c:
            count = c.execute('select count(*) from student_badges where student_sic="24beca01" and badge_id="flawless" and is_active=1').fetchone()[0]
        self.assertEqual(count, 0)

    def test_leaderboard_projection_includes_badges(self):
        s = student(sic='24beca01', week1=100, week2=100)
        app.save_rows([app.validate(s)])
        app.set_week(2)
        status, data = self.call('/api/leaderboard')
        self.assertEqual(status, 200)
        p = data['participants'][0]
        self.assertIn('badges', p)
        earned_ids = {b['id'] for b in p['badges']}
        self.assertIn('flawless', earned_ids)
        self.assertIn('badge_definitions', data)

if __name__=='__main__':unittest.main()
