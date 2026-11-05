import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import schedule_config as config
class ScheduleTests(unittest.TestCase):
    def test_reveal_is_category_and_round_specific(self):
        data=config.defaults();data['junior'][0].update(subject='Private Junior Subject',scope='Private topics',date='2026-11-10')
        data['cs'][1].update(subject='CS Exam',scope='Loops',revealed=True)
        visible=config.public(data)
        self.assertEqual(visible['junior'][0],{'round':1,'revealed':False,'date':'2026-11-10'})
        self.assertEqual(visible['cs'][1]['subject'],'CS Exam')
        self.assertNotIn('Private Junior Subject',json.dumps(visible))
        self.assertNotIn('scope',visible['core'][1])
    def test_revealed_projection_allowlist(self):
        data=config.defaults();data['cs'][0].update(scope='Loops',revealed=True,internal_notes='Never public')
        self.assertNotIn('Never public',json.dumps(config.public(data)))
    def test_round_order_and_strict_fields(self):
        for field,value in [('round',True),('round',2),('subject',None),('scope',[]),('revealed','true'),('date','20261101'),('date','2026-02-30'),('syllabus_url','https://user:password@example.com/a'),('syllabus_url','https://example.com:invalid/a')]:
            data=config.defaults();data['junior'][0][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):config.validate(data)
    def test_require_content_before_revealing(self):
        data=config.defaults();data['core'][0].update(revealed=True,subject='',scope='',syllabus_url='')
        with self.assertRaises(ValueError):config.validate(data)
        data['core'][0].update(subject='Exam',scope='Topics')
        self.assertTrue(config.validate(data)['core'][0]['revealed'])
        data['core'][0].update(scope='',syllabus_url='https://example.com/syllabus.pdf#page=1')
        self.assertTrue(config.validate(data)['core'][0]['revealed'])
    def test_save_reveal_hide_and_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);data=config.defaults();old=config.revision(data)
            data['core'][0].update(scope='Topics',revealed=True);config.save(root,'','',data)
            self.assertNotEqual(config.revision(config.read(root,'','')),old)
            self.assertIn('subject',config.public(config.read(root,'',''))['core'][0])
            data['core'][0]['revealed']=False;config.save(root,'','',data)
            self.assertNotIn('subject',config.public(config.read(root,'',''))['core'][0])
            self.assertEqual(config.read(root,'','')['core'][0]['scope'],'Topics')
    def test_invalid_stored_data_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'.data').mkdir();path=root/'.data'/'schedule.json'
            for value in ('invalid json',json.dumps({'junior':[]})):
                path.write_text(value)
                with self.assertRaises(RuntimeError):config.read(root,'','')
    def test_revision_independent_of_key_order(self):
        original=config.defaults();reversed_data=dict(reversed(list(original.items())))
        self.assertEqual(config.revision(original),config.revision(reversed_data))
    def test_exam_times_validate_and_publish(self):
        data=config.defaults();data['junior'][0].update(date='2026-11-14',start_time='11:00',end_time='12:30')
        self.assertEqual(config.public(data)['junior'][0]['start_time'],'11:00')
        for start,end in [('15:30','15:00'),('25:00','26:00'),('11:00','')]:
            data['junior'][0].update(start_time=start,end_time=end)
            with self.assertRaises(ValueError):config.validate(data)
