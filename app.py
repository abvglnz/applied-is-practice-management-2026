#!/usr/bin/env python3
"""Praktika: stdlib-only local web application. Python 3.10+."""
import csv, hashlib, hmac, io, json, mimetypes, os, secrets, sqlite3, time
from datetime import date
from email.parser import BytesParser
from email.policy import default as email_policy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse
from assistant import answer

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get('PRAKTIKA_DB', str(ROOT / 'data' / 'praktika.sqlite3')))
UPLOAD_DIR = Path(os.environ.get('PRAKTIKA_UPLOAD_DIR', str(DB_PATH.parent / 'uploads')))
MAX_UPLOAD_SIZE = 10 * 1024 * 1024
ALLOWED_UPLOAD_EXTENSIONS = {'.pdf','.doc','.docx','.xls','.xlsx','.jpg','.jpeg','.png'}
DOCUMENT_TYPES = {'diary':'Күнделік файлы','certificate':'Практика анықтамасы','contract':'Жалпы шарт','report':'Практика есебі'}
SESSIONS = {}
LOGIN_ATTEMPTS = {}
FIELDS = {
 'students': ['name','group_name','email'],
 'bases': ['name','address','contact','capacity'],
 'supervisors': ['name','position','email'],
 'contracts': ['number','base_id','start_date','end_date'],
 'placements': ['student_id','base_id','supervisor_id','contract_id','kind','start_date','end_date'],
 'diaries': ['placement_id','date','content','hours','status','feedback'],
 'reports': ['placement_id','title','content','status','feedback'],
 'grades': ['placement_id','discipline','diary','report','defense','comment']}

def connect():
    con=sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory=sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    return con

def password_hash(password,salt):
    return hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),200000).hex()

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as con:
        con.executescript((ROOT/'schema.sql').read_text())
        if con.execute('SELECT COUNT(*) FROM users').fetchone()[0]: return
        # The FastAPI/SQLModel coursework stack may have already seeded the
        # shared tables. Do not insert those rows a second time when this
        # original server is started afterwards.
        if con.execute('SELECT COUNT(*) FROM students').fetchone()[0] == 0:
            seed=json.loads((ROOT/'dist'/'seed.json').read_text())
            for entity, records in seed.items():
                if entity not in FIELDS: continue
                for record in records:
                    keys=['id']+FIELDS[entity]
                    con.execute(f"INSERT INTO {entity} ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)})", [record.get(k,'') for k in keys])
        for username,pw,role,name,sid,vid in [
            ('admin','Admin2026!','admin','Практика үйлестірушісі',None,None),
            ('leader','Leader2026!','supervisor','Айдана Сәрсенова',None,1),
            ('student','Student2026!','student','Әлия Нұрлан',1,None)]:
            salt=secrets.token_hex(16)
            con.execute('INSERT INTO users(username,password,salt,role,name,student_id,supervisor_id) VALUES (?,?,?,?,?,?,?)',(username,password_hash(pw,salt),salt,role,name,sid,vid))

def visible_placements(con,user):
    if user['role']=='admin': return [r['id'] for r in con.execute('SELECT id FROM placements')]
    key='student_id' if user['role']=='student' else 'supervisor_id'
    return [r['id'] for r in con.execute(f'SELECT id FROM placements WHERE {key}=?',(user[key],))]

def can_access_placement(user,placement):
    if not placement: return False
    if user['role']=='admin': return True
    if user['role']=='student': return placement['student_id']==user['student_id']
    return placement['supervisor_id']==user['supervisor_id']

def document_metadata(con,user,placement_id=None):
    query='''SELECT d.id,d.placement_id,d.user_id,d.document_type,d.original_name,d.mime_type,
                    d.file_size,d.status,d.created_at,u.name AS uploaded_by
             FROM documents d JOIN placements p ON p.id=d.placement_id
             JOIN users u ON u.id=d.user_id'''
    clauses=[]; args=[]
    if user['role']=='student': clauses.append('p.student_id=?'); args.append(user['student_id'])
    elif user['role']=='supervisor': clauses.append('p.supervisor_id=?'); args.append(user['supervisor_id'])
    if placement_id is not None: clauses.append('d.placement_id=?'); args.append(placement_id)
    if clauses: query+=' WHERE '+' AND '.join(clauses)
    query+=' ORDER BY d.created_at DESC,d.id DESC'
    return [dict(row) for row in con.execute(query,args)]

def dataset(con,user):
    result={k:[dict(r) for r in con.execute(f'SELECT * FROM {k} ORDER BY id DESC')] for k in FIELDS}
    if user['role']!='admin':
        ids=set(visible_placements(con,user))
        result['placements']=[r for r in result['placements'] if r['id'] in ids]
        for k in ['diaries','reports','grades']: result[k]=[r for r in result[k] if r['placement_id'] in ids]
        student_ids={r['student_id'] for r in result['placements']}
        if user['role']=='student': student_ids.add(user['student_id'])
        result['students']=[r for r in result['students'] if r['id'] in student_ids]
        # References visible only for assigned practice; no unrelated contacts.
        for table,key in [('bases','base_id'),('supervisors','supervisor_id'),('contracts','contract_id')]:
            allowed={r[key] for r in result['placements']}
            result[table]=[r for r in result[table] if r['id'] in allowed]
    return result

def check_permission(con,user,entity,record_id,data,method):
    if user['role']=='admin': return
    if entity not in ('diaries','reports','grades'): raise PermissionError('Бұл әрекетке құқығыңыз жоқ.')
    old=con.execute(f'SELECT * FROM {entity} WHERE id=?',(record_id,)).fetchone() if record_id else None
    pid=int(data.get('placement_id', old['placement_id'] if old else 0))
    allowed=visible_placements(con,user)
    if pid not in allowed or (old and old['placement_id'] not in allowed): raise PermissionError('Өз практикаңызға қатысты жазбаны ғана өзгерте аласыз.')
    if user['role']=='student':
        if entity=='grades': raise PermissionError('Бағаны жетекші қояды.')
        if old and old['status']=='Қабылданды': raise PermissionError('Қабылданған құжатты өзгертуге болмайды.')
        data['status']='Ұсынылды'; data['feedback']=''
    elif entity in ('diaries','reports'):
        if method!='PUT' or not old: raise PermissionError('Жетекші ұсынылған құжатқа тек пікір мен мәртебе енгізеді.')
        for k in FIELDS[entity]:
            if k not in ('status','feedback'): data[k]=old[k]

def validate(con,entity,data,rid=None):
    cleaned={}
    for key in FIELDS[entity]:
        val=data.get(key,'')
        if key.endswith('_id') or key in ('capacity','hours','discipline','diary','report','defense'):
            if isinstance(val,bool): raise ValueError('Сан дұрыс емес.')
            try: val=int(str(val))
            except (TypeError,ValueError): raise ValueError('Сандық өрісті дұрыс толтырыңыз.')
        else:
            val=str(val).strip()
            if not val and key not in ('feedback','comment'): raise ValueError('Міндетті өрістерді толтырыңыз.')
            if len(val)>20000: raise ValueError('Мәтін тым ұзын.')
        if key.endswith('_date') or key=='date':
            try: date.fromisoformat(val)
            except ValueError: raise ValueError('Күн пішімі YYYY-MM-DD болуы керек.')
        cleaned[key]=val
    d=cleaned
    if 'start_date' in d and d['start_date']>d['end_date']: raise ValueError('Басталу күні аяқталу күнінен кеш болмауы керек.')
    if entity=='bases' and not 1<=d['capacity']<=10000: raise ValueError('Орын саны 1–10000 аралығында болуы керек.')
    if entity=='placements':
        c=con.execute('SELECT * FROM contracts WHERE id=?',(d['contract_id'],)).fetchone()
        if not c or c['base_id']!=d['base_id']: raise ValueError('Келісімшарт таңдалған базаға тиесілі емес.')
        if d['start_date']<c['start_date'] or d['end_date']>c['end_date']: raise ValueError('Практика келісімшарт мерзіміне сыймайды.')
        overlap='start_date<=? AND end_date>=? AND id<>?'
        args=(d['end_date'],d['start_date'],rid or -1)
        if con.execute('SELECT id FROM placements WHERE student_id=? AND '+overlap,(d['student_id'],)+args).fetchone(): raise ValueError('Студентте осы мерзімде басқа практика бар.')
        cap=con.execute('SELECT capacity FROM bases WHERE id=?',(d['base_id'],)).fetchone()
        if not cap: raise ValueError('Практика базасы табылмады.')
        # Sweep all intersecting intervals to calculate peak occupancy, rather than count every overlap.
        events=[(d['start_date'],1),(d['end_date'],-1)]
        rows=con.execute('SELECT start_date,end_date FROM placements WHERE base_id=? AND '+overlap,(d['base_id'],)+args)
        for r in rows: events.extend([(max(r['start_date'],d['start_date']),1),(min(r['end_date'],d['end_date']),-1)])
        occupancy=0
        for day,delta in sorted(events,key=lambda x:(x[0],-x[1])):
            occupancy+=delta
            if occupancy>cap['capacity']: raise ValueError('Базада осы мерзімге бос орын жоқ.')
        # Do not invalidate existing dated diaries when moving practice boundaries.
        if rid and con.execute('SELECT id FROM diaries WHERE placement_id=? AND (date<? OR date>?)',(rid,d['start_date'],d['end_date'])).fetchone(): raise ValueError('Жаңа мерзім бар күнделік күндерін қамтымайды.')
    if entity=='contracts' and rid:
        if con.execute('SELECT id FROM placements WHERE contract_id=? AND (base_id<>? OR start_date<? OR end_date>?)',(rid,d['base_id'],d['start_date'],d['end_date'])).fetchone(): raise ValueError('Бұл өзгеріс қолданыстағы практикаға қайшы келеді.')
    if entity=='bases' and rid:
        events=[]
        for p in con.execute('SELECT start_date,end_date FROM placements WHERE base_id=?',(rid,)): events.extend([(p[0],1),(p[1],-1)])
        count=0
        for _,delta in sorted(events,key=lambda x:(x[0],-x[1])):
            count+=delta
            if count>d['capacity']: raise ValueError('Орын санын қолданыстағы жүктемеден азайтуға болмайды.')
    if entity=='diaries':
        p=con.execute('SELECT * FROM placements WHERE id=?',(d['placement_id'],)).fetchone()
        if not p or not p['start_date']<=d['date']<=p['end_date']: raise ValueError('Күнделік күні практика мерзіміне кірмейді.')
        if not 1<=d['hours']<=12: raise ValueError('Жұмыс уақыты 1–12 сағат болуы керек.')
    if entity in ('diaries','reports') and d['status'] not in ('Ұсынылды','Қабылданды','Түзету қажет'): raise ValueError('Мәртебе дұрыс емес.')
    if entity=='grades':
        if any(not 0<=d[k]<=100 for k in ('discipline','diary','report','defense')): raise ValueError('Бағалар 0–100 аралығында болуы керек.')
        if not con.execute("SELECT id FROM reports WHERE placement_id=? AND status='Қабылданды'",(d['placement_id'],)).fetchone(): raise ValueError('Бағалау үшін практика есебі қабылдануы керек.')
    return cleaned

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt,*args): pass
    def send(self,status,body,content_type='application/json; charset=utf-8',extra=None):
        if isinstance(body,(dict,list)): body=json.dumps(body,ensure_ascii=False).encode()
        elif isinstance(body,str): body=body.encode()
        self.send_response(status); self.send_header('Content-Type',content_type); self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'")
        for k,v in (extra or {}).items(): self.send_header(k,v)
        self.end_headers(); self.wfile.write(body)
    def body(self):
        size=int(self.headers.get('Content-Length','0'))
        if size>120000: raise ValueError('Сұрау көлемі тым үлкен.')
        return json.loads(self.rfile.read(size) or b'{}')
    def multipart(self):
        size=int(self.headers.get('Content-Length','0'))
        if size<=0 or size>MAX_UPLOAD_SIZE+128*1024: raise ValueError('Файл бос немесе 10 МБ шегінен үлкен.')
        content_type=self.headers.get('Content-Type','')
        if not content_type.lower().startswith('multipart/form-data;'): raise ValueError('Файл multipart/form-data пішімінде жіберілуі керек.')
        raw=self.rfile.read(size)
        envelope=(b'MIME-Version: 1.0\r\nContent-Type: '+content_type.encode('ascii')+b'\r\n\r\n'+raw)
        message=BytesParser(policy=email_policy).parsebytes(envelope)
        if not message.is_multipart(): raise ValueError('Жүктелген файлдың пішімі дұрыс емес.')
        fields={}; uploaded=None
        for part in message.iter_parts():
            name=part.get_param('name',header='content-disposition')
            if not name: continue
            filename=part.get_filename()
            payload=part.get_payload(decode=True) or b''
            if filename is not None:
                if name!='file' or uploaded is not None: raise ValueError('Бір ретте бір файл ғана таңдаңыз.')
                uploaded=(filename,payload)
            else:
                fields[name]=payload.decode('utf-8','replace').strip()
        if uploaded is None: raise ValueError('Жүктеу үшін файл таңдаңыз.')
        return fields,uploaded
    def user(self):
        cookies=dict(x.strip().split('=',1) for x in self.headers.get('Cookie','').split(';') if '=' in x)
        session=SESSIONS.get(cookies.get('session',''))
        if not session or session['expires']<time.time(): raise PermissionError('Жүйеге кіріңіз.')
        self.session=session
        with connect() as con: return dict(con.execute('SELECT id,username,role,name,student_id,supervisor_id FROM users WHERE id=?',(session['id'],)).fetchone())
    def do_GET(self): self.handle_request('GET')
    def do_POST(self): self.handle_request('POST')
    def do_PUT(self): self.handle_request('PUT')
    def do_DELETE(self): self.handle_request('DELETE')
    def handle_request(self,method):
        path=urlparse(self.path).path
        try:
            if method=='GET' and path in ('/','/index.html','/style.css','/app.js'):
                f=ROOT/'dist'/('index.html' if path=='/' else path[1:])
                return self.send(200,f.read_bytes(),{'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8'}[f.suffix])
            if path=='/api/login' and method=='POST':
                data=self.body(); ip=self.client_address[0]; recent=[t for t in LOGIN_ATTEMPTS.get(ip,[]) if time.time()-t<60]
                if len(recent)>=10: return self.send(429,{'error':'Бір минуттан кейін қайталаңыз.'})
                with connect() as con: u=con.execute('SELECT * FROM users WHERE username=?',(data.get('username',''),)).fetchone()
                if not u or not hmac.compare_digest(u['password'],password_hash(str(data.get('password','')),u['salt'])):
                    LOGIN_ATTEMPTS[ip]=recent+[time.time()]; return self.send(401,{'error':'Логин немесе құпиясөз қате.'})
                LOGIN_ATTEMPTS.pop(ip,None)
                token=secrets.token_urlsafe(32); csrf=secrets.token_urlsafe(24)
                SESSIONS[token]={'id':u['id'],'expires':time.time()+28800,'csrf':csrf,'last_ai':0}
                return self.send(200,{'ok':True},extra={'Set-Cookie':f'session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800'})
            user=self.user()
            if method!='GET' and not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),self.session['csrf']): raise PermissionError('Қауіпсіздік токені дұрыс емес. Бетті жаңартыңыз.')
            if path=='/api/me': return self.send(200,{'user':user,'csrf':self.session['csrf'],'ai_online':bool(os.environ.get('OPENAI_API_KEY'))})
            if path=='/api/logout' and method=='POST':
                for key in list(SESSIONS):
                    if SESSIONS[key] is self.session: SESSIONS.pop(key)
                return self.send(200,{'ok':True},extra={'Set-Cookie':'session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'})
            with connect() as con:
                if path=='/api/documents' and method=='GET':
                    query=parse_qs(urlparse(self.path).query); raw_id=query.get('placement_id',[None])[0]
                    placement_id=int(raw_id) if raw_id else None
                    return self.send(200,document_metadata(con,user,placement_id))
                if path=='/api/documents' and method=='POST':
                    fields,(filename,payload)=self.multipart()
                    try: placement_id=int(fields.get('placement_id',''))
                    except ValueError: raise ValueError('Практиканы таңдаңыз.')
                    document_type=fields.get('document_type','')
                    if document_type not in DOCUMENT_TYPES: raise ValueError('Құжат түрін таңдаңыз.')
                    placement=con.execute('SELECT * FROM placements WHERE id=?',(placement_id,)).fetchone()
                    if not can_access_placement(user,placement): raise PermissionError('Бұл практикаға құжат жүктеуге құқығыңыз жоқ.')
                    original_name=Path(filename.replace('\\','/')).name.strip()
                    extension=Path(original_name).suffix.lower()
                    if not original_name or len(original_name)>255: raise ValueError('Файл атауы 255 таңбадан аспауы керек.')
                    if extension not in ALLOWED_UPLOAD_EXTENSIONS: raise ValueError('PDF, DOC, DOCX, XLS, XLSX, JPG немесе PNG файлын таңдаңыз.')
                    if not payload or len(payload)>MAX_UPLOAD_SIZE: raise ValueError('Файл бос немесе 10 МБ шегінен үлкен.')
                    stored_name=secrets.token_hex(24)+extension
                    UPLOAD_DIR.mkdir(parents=True,exist_ok=True)
                    file_path=UPLOAD_DIR/stored_name
                    mime_type=mimetypes.guess_type(original_name)[0] or 'application/octet-stream'
                    with file_path.open('xb') as uploaded_file: uploaded_file.write(payload)
                    try:
                        cur=con.execute('''INSERT INTO documents
                            (placement_id,user_id,document_type,original_name,stored_name,mime_type,file_size)
                            VALUES (?,?,?,?,?,?,?)''',
                            (placement_id,user['id'],document_type,original_name,stored_name,mime_type,len(payload)))
                        document_id=cur.lastrowid
                        con.execute('INSERT INTO audit(user_id,action,entity,record_id) VALUES (?,?,?,?)',
                                    (user['id'],'UPLOAD','documents',document_id))
                        con.commit()
                    except Exception:
                        file_path.unlink(missing_ok=True)
                        raise
                    return self.send(201,{'ok':True,'id':document_id,'original_name':original_name,'document_type':document_type})
                parts=path.strip('/').split('/')
                if len(parts)==4 and parts[:2]==['api','documents'] and parts[3]=='download' and method=='GET':
                    try: document_id=int(parts[2])
                    except ValueError: return self.send(404,{'error':'Құжат табылмады.'})
                    row=con.execute('''SELECT d.*,p.student_id,p.supervisor_id FROM documents d
                                      JOIN placements p ON p.id=d.placement_id WHERE d.id=?''',(document_id,)).fetchone()
                    if not row or not can_access_placement(user,row): return self.send(404,{'error':'Құжат табылмады.'})
                    stored_name=Path(row['stored_name']).name
                    file_path=UPLOAD_DIR/stored_name
                    if not file_path.is_file(): return self.send(404,{'error':'Файл серверден табылмады.'})
                    return self.send(200,file_path.read_bytes(),row['mime_type'],
                                     {'Content-Disposition':"attachment; filename*=UTF-8''"+quote(row['original_name'],safe='')})
                if len(parts)==3 and parts[:2]==['api','documents'] and method=='DELETE':
                    try: document_id=int(parts[2])
                    except ValueError: return self.send(404,{'error':'Құжат табылмады.'})
                    row=con.execute('''SELECT d.*,p.student_id,p.supervisor_id FROM documents d
                                      JOIN placements p ON p.id=d.placement_id WHERE d.id=?''',(document_id,)).fetchone()
                    if not row: return self.send(404,{'error':'Құжат табылмады.'})
                    allowed=user['role']=='admin' or (user['role']=='student' and row['user_id']==user['id'] and row['status']=='Ұсынылды')
                    if not allowed: raise PermissionError('Бұл құжатты жоюға құқығыңыз жоқ.')
                    con.execute('DELETE FROM documents WHERE id=?',(document_id,))
                    con.execute('INSERT INTO audit(user_id,action,entity,record_id) VALUES (?,?,?,?)',
                                (user['id'],'DELETE','documents',document_id))
                    con.commit()
                    (UPLOAD_DIR/Path(row['stored_name']).name).unlink(missing_ok=True)
                    return self.send(200,{'ok':True,'id':document_id})
                if path in ('/api/data','/api/export') and method=='GET':
                    data=dataset(con,user)
                    if path=='/api/data': return self.send(200,data)
                    output=io.StringIO(); w=csv.writer(output); w.writerow(['Студент','Топ','База','Жетекші','Басталуы','Аяқталуы','Есеп мәртебесі','Қорытынды балл'])
                    refs=lambda table,rid: next((r for r in data[table] if r['id']==rid),{})
                    for p in data['placements']:
                        st=refs('students',p['student_id']); base=refs('bases',p['base_id']); sup=refs('supervisors',p['supervisor_id'])
                        report=next((r for r in data['reports'] if r['placement_id']==p['id']),{}); g=next((r for r in data['grades'] if r['placement_id']==p['id']),None)
                        cells=[st.get('name'),st.get('group_name'),base.get('name'),sup.get('name'),p['start_date'],p['end_date'],report.get('status','Ұсынылмаған'),round(.1*g['discipline']+.2*g['diary']+.4*g['report']+.3*g['defense'],1) if g else '']
                        w.writerow([("'"+str(v)) if str(v).startswith(('=','+','-','@','\t','\r')) else v for v in cells])
                    return self.send(200,'\ufeff'+output.getvalue(),'text/csv; charset=utf-8',{'Content-Disposition':'attachment; filename="praktika-report.csv"'})
                if path=='/api/assistant' and method=='POST':
                    if time.time()-self.session['last_ai']<3: return self.send(429,{'error':'Бірнеше секунд күтіңіз.'})
                    self.session['last_ai']=time.time(); msg=str(self.body().get('message','')).strip()
                    if not msg or len(msg)>4000: raise ValueError('Сұрақ 1–4000 таңба аралығында болуы керек.')
                    d=dataset(con,user)
                    context=f"Көрінетін студенттер: {len(d['students'])}; практика: {len(d['placements'])}; күнделік: {len(d['diaries'])}; есеп: {len(d['reports'])}; қабылданған есеп: {sum(r['status']=='Қабылданды' for r in d['reports'])}; бағаланған практика: {len(d['grades'])}."
                    return self.send(200,answer(msg,context))
                parts=path.strip('/').split('/')
                if len(parts) not in (2,3) or parts[0]!='api' or parts[1] not in FIELDS: return self.send(404,{'error':'Бөлім табылмады.'})
                entity=parts[1]; rid=int(parts[2]) if len(parts)==3 else None
                if method not in ('POST','PUT','DELETE') or (method in ('PUT','DELETE') and not rid): return self.send(405,{'error':'Әдіс қолдау таппайды.'})
                con.execute('BEGIN IMMEDIATE')
                if rid and not con.execute(f'SELECT id FROM {entity} WHERE id=?',(rid,)).fetchone(): return self.send(404,{'error':'Жазба табылмады.'})
                data=self.body() if method!='DELETE' else {}
                check_permission(con,user,entity,rid,data,method)
                if method=='DELETE': con.execute(f'DELETE FROM {entity} WHERE id=?',(rid,))
                else:
                    clean=validate(con,entity,data,rid); keys=list(clean)
                    if method=='POST':
                        cur=con.execute(f"INSERT INTO {entity} ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)})",list(clean.values())); rid=cur.lastrowid
                    else: con.execute(f"UPDATE {entity} SET {','.join(k+'=?' for k in keys)} WHERE id=?",list(clean.values())+[rid])
                con.execute('INSERT INTO audit(user_id,action,entity,record_id) VALUES (?,?,?,?)',(user['id'],method,entity,rid))
                con.commit()
                return self.send(200,{'ok':True,'id':rid})
        except PermissionError as exc: self.send(401 if str(exc)=='Жүйеге кіріңіз.' else 403,{'error':str(exc)})
        except sqlite3.IntegrityError: self.send(409,{'error':'Байланысқан жазба бар немесе бірегей мән қайталанған. Алдымен тәуелді жазбаларды тексеріңіз.'})
        except (ValueError,TypeError,KeyError,json.JSONDecodeError) as exc: self.send(400,{'error':str(exc) or 'Деректер дұрыс емес.'})
        except Exception as exc:
            print('Server error:',type(exc).__name__)
            self.send(500,{'error':'Сервер қатесі. Қайта әрекет жасаңыз.'})

if __name__=='__main__':
    init_db(); port=int(os.environ.get('PORT','8765')); host=os.environ.get('HOST','127.0.0.1')
    print(f'Praktika іске қосылды: http://127.0.0.1:{port}',flush=True)
    ThreadingHTTPServer((host,port),Handler).serve_forever()
