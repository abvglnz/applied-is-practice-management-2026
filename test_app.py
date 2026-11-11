"""Integration checks against an isolated SQLite database. python3 -m unittest -v"""
import http.cookiejar, json, os, subprocess, sys, tempfile, time, unittest, urllib.request, urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parent
class AppTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.port=18765
  cls.process=subprocess.Popen([sys.executable,str(ROOT/'app.py')],env={**os.environ,'PRAKTIKA_DB':cls.temp.name+'/test.sqlite3','PORT':str(cls.port),'OPENAI_API_KEY':''},stdout=subprocess.DEVNULL)
  for _ in range(60):
   try: urllib.request.urlopen(f'http://127.0.0.1:{cls.port}/');break
   except urllib.error.URLError: time.sleep(.1)
  else: raise RuntimeError('Server did not start')
 @classmethod
 def tearDownClass(cls): cls.process.terminate();cls.process.wait(timeout=5);cls.temp.cleanup()
 def client(self,user='admin',pw='Admin2026!'):
  op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
  self.call(op,'login','POST',{'username':user,'password':pw},expected=200)
  me=self.call(op,'me');return op,me['csrf']
 def call(self,op,path,method='GET',body=None,token='',expected=200):
  req=urllib.request.Request(f'http://127.0.0.1:{self.port}/api/'+path,data=json.dumps(body).encode() if body is not None else None,method=method,headers={'Content-Type':'application/json','X-CSRF-Token':token})
  try: r=op.open(req)
  except urllib.error.HTTPError as err:r=err
  self.assertEqual(r.status,expected,r.read().decode() if r.status!=expected else '')
  raw=r.read();return json.loads(raw) if 'application/json' in r.headers.get('Content-Type','') else raw.decode('utf-8-sig')
 def test_01_auth_and_csrf(self):
  op=urllib.request.build_opener();self.call(op,'data',expected=401)
  self.call(op,'login','POST',{'username':'admin','password':'wrong'},expected=401)
  op,t=self.client();self.call(op,'students','POST',{'name':'X'},expected=403)
 def test_02_crud_persistence_and_fk(self):
  op,t=self.client();data={'name':'Сынақ студент','group_name':'Т-01','email':'test@example.edu'}
  r=self.call(op,'students','POST',data,t);rid=r['id'];self.assertTrue(any(s['id']==rid for s in self.call(op,'data')['students']))
  self.call(op,f'students/{rid}','PUT',{**data,'name':'Өзгертілді'},t)
  op2,t2=self.client();self.assertEqual(next(s for s in self.call(op2,'data')['students'] if s['id']==rid)['name'],'Өзгертілді')
  self.call(op,f'students/{rid}','DELETE',token=t);self.call(op,'bases/1','DELETE',token=t,expected=409)
 def test_03_placement_rules(self):
  op,t=self.client();p={'student_id':1,'base_id':1,'supervisor_id':1,'contract_id':1,'kind':'Өндірістік','start_date':'2026-10-05','end_date':'2026-10-30'}
  self.call(op,'placements','POST',p,t,400)
  self.call(op,'placements','POST',{**p,'student_id':7,'contract_id':2},t,400)
  self.call(op,'placements','POST',{**p,'student_id':7,'end_date':'2027-01-01'},t,400)
  self.call(op,'bases/1','PUT',{'name':'Qadam Digital','address':'A','contact':'B','capacity':1},t,400)
  r=self.call(op,'placements','POST',{**p,'student_id':7},t);rid=r['id']
  self.call(op,'placements','POST',{**p,'student_id':8},t)
  self.call(op,'placements','POST',{**p,'student_id':7,'start_date':'2026-10-31','end_date':'2026-11-10'},t) # adjacent non-overlap accepted
  # student 7 already assigned in October; use another period and capacity test separately below
  self.call(op,f'placements/{rid}','DELETE',token=t)
 def test_04_student_permissions(self):
  op,t=self.client('student','Student2026!');d=self.call(op,'data');self.assertEqual(len(d['students']),1);self.assertTrue(all(p['student_id']==1 for p in d['placements']))
  self.call(op,'grades','POST',{'placement_id':1},t,403)
  self.call(op,'reports/2','PUT',{'placement_id':1,'title':'x','content':'x','status':'Қабылданды','feedback':'x'},t,403)
  r=self.call(op,'reports','POST',{'placement_id':1,'title':'Есеп','content':'Өз жұмысым','status':'Қабылданды','feedback':'fake'},t)
  report=next(x for x in self.call(op,'data')['reports'] if x['id']==r['id'])
  self.assertEqual(report['status'],'Ұсынылды');self.assertEqual(report['feedback'],'')
  self.call(op,'diaries','POST',{'placement_id':1,'date':'2026-12-01','content':'x','hours':6},t,400)
 def test_05_supervisor_scope_and_review(self):
  op,t=self.client('leader','Leader2026!');d=self.call(op,'data');self.assertTrue(all(p['supervisor_id']==1 for p in d['placements']))
  self.call(op,'diaries/3','PUT',{'placement_id':2,'content':'HACK','status':'Қабылданды','feedback':'Тексерілді'},t)
  self.assertNotEqual(next(r for r in self.call(op,'data')['diaries'] if r['id']==3)['content'],'HACK')
  self.call(op,'diaries/4','PUT',{'placement_id':3,'status':'Қабылданды'},t,403)
 def test_06_grade_constraints_and_csv(self):
  op,t=self.client();g={'placement_id':6,'discipline':90,'diary':90,'report':90,'defense':90,'comment':''}
  self.call(op,'grades','POST',g,t,400)
  self.call(op,'grades/1','PUT',{**g,'placement_id':2,'report':101},t,400)
  csv=self.call(op,'export');self.assertIn('90.3',csv);self.assertIn('Студент',csv)
 def test_07_offline_assistant(self):
  op,t=self.client();r=self.call(op,'assistant','POST',{'message':'Күнделік үлгісін бер'},t);self.assertEqual(r['mode'],'offline');self.assertIn('Күнделік',r['answer'])
  self.call(op,'assistant','POST',{'message':'Есеп'},t,429)
 def test_08_capacity_peak_and_contract_update(self):
  op,t=self.client();base=self.call(op,'bases','POST',{'name':'Test','address':'A','contact':'B','capacity':1},t)['id'];c=self.call(op,'contracts','POST',{'number':'TEST-1','base_id':base,'start_date':'2026-01-01','end_date':'2026-12-31'},t)['id']
  p={'student_id':7,'base_id':base,'supervisor_id':1,'contract_id':c,'kind':'Test','start_date':'2026-12-01','end_date':'2026-12-10'}
  self.call(op,'placements','POST',p,t)
  self.call(op,'placements','POST',{**p,'student_id':8},t,400)
  self.call(op,'placements','POST',{**p,'student_id':8,'start_date':'2026-12-11','end_date':'2026-12-20'},t)
  self.call(op,f'contracts/{c}','PUT',{'number':'TEST-1','base_id':base,'start_date':'2026-12-15','end_date':'2026-12-31'},t,400)
if __name__=='__main__':unittest.main(verbosity=2)
