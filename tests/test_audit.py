import unittest
from unittest.mock import patch
from test_server import app,student
import security_store
class AuditTests(unittest.TestCase):
    def test_category_isolation(self):
        rows=[student('test001',week1=100),student('test002',track='core',week1=70)]
        awards=app.evaluate_badges(rows,1)
        self.assertEqual({a['student_sic'] for a in awards if a['badge_id']=='the-ace'},{'test001','test002'})
    def test_no_unpublished_awards(self):
        row=student(week1=80,week2=90,week3=100,week4=100,week5=100)
        self.assertEqual(app.evaluate_badges([row],0),[])
        self.assertFalse(any(a['badge_id'] in ('flawless','the-unlocked-five') for a in app.evaluate_badges([row],2)))
        self.assertTrue(any(a['badge_id']=='the-unlocked-five' for a in app.evaluate_badges([row],5)))
    def test_each_improvement_pair(self):
        rows=[student('test001',week1=10,week2=50,week3=51),student('test002',week1=60,week2=61,week3=90)]
        awards=app.evaluate_badges(rows,3)
        self.assertEqual({a['student_sic'] for a in awards if a['badge_id']=='the-glow-up'},{'test001','test002'})
    def test_rounding_half_up(self):
        self.assertEqual(app.validate(student(week1='80.125'))['week1'],80.13)
    def test_cloud_badges_derived_and_retracted(self):
        with patch.object(app,'URL','https://example.test'),patch.object(app,'all_rows',return_value=[student(week1=100)]),patch.object(app,'get_week',return_value=1):
            result=app.public_results()
            self.assertTrue(result['participants'][0]['badges'])
            with patch.object(app,'get_week',return_value=0):
                self.assertEqual(app.public_results()['participants'][0]['badges'],[])
    def test_atomic_attempt_slots(self):
        with patch.object(security_store,'request',side_effect=[False]*6):
            self.assertFalse(security_store.allow_attempt('url','key','secret','ip',100))
        with patch.object(security_store,'request',side_effect=[False,{}]):
            self.assertTrue(security_store.allow_attempt('url','key','secret','ip',100))
    def test_revoked_session(self):
        with patch.object(security_store,'request',return_value={'expires':0}):
            self.assertFalse(security_store.session('url','key','secret','token'))
    def test_invalid_stored_scores_fail_closed(self):
        for value in (True,float('nan'),101,-1):
            with self.assertRaises(app.ValidationError):app.evaluate_badges([student(week1=value)],1)
    def test_missing_scores_count_zero_for_leader(self):
        rows=[student('test001',week1=100,week2=None),student('test002',week1=60,week2=60)]
        awards=app.evaluate_badges(rows,2)
        self.assertEqual([a['student_sic'] for a in awards if a['badge_id']=='the-main-character'],['test002'])
    def test_zero_is_participation_blank_is_not(self):
        row=student(week1=0,week2=0,week3=0,week4=0,week5=0)
        self.assertTrue(any(a['badge_id']=='the-unlocked-five' for a in app.evaluate_badges([row],5)))
        row['week5']=None
        self.assertFalse(any(a['badge_id']=='the-unlocked-five' for a in app.evaluate_badges([row],5)))
