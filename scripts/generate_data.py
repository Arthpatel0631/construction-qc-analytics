import random, sqlite3, csv, json, datetime as dt
random.seed(26)
base=dt.date(2026,5,1); ASOF=183
D=lambda n: (base+dt.timedelta(days=n)).isoformat()
projects=[(1,'Riverfront Data Center, Phase 2','Data center','St. Louis, MO'),(2,'Midtown Medical Pavilion','Healthcare','St. Louis, MO'),(3,'Clayton Office Interior Renovation','Interior renovation','Clayton, MO'),(4,'North County Biotech Lab','Mission-critical lab','Florissant, MO'),(5,'Southside Distribution Hub','Industrial','St. Louis, MO')]
subs=[(1,'Gateway Concrete','Concrete',1.0),(2,'Arch City Steel','Structural steel',.7),(3,'Midwest Drywall & Framing','Drywall',1.6),(4,'Lindell Mechanical','HVAC',1.2),(5,'Mississippi Electric','Electrical',.8),(6,'Cardinal Plumbing','Plumbing',1.0),(7,'Brickline Masonry','Masonry',1.3),(8,'Summit Fire Protection','Fire protection',.9),(9,'Prairie Roofing','Roofing',1.5),(10,'Metro Finishes','Finishes',.9)]
phases=['Preparatory','Initial','Follow-up']; res=['Pass','Pass with comments','Fail']
cats=['Workmanship','Material nonconformance','Safety','Documentation']; sevs=['Minor','Major','Critical']
sev_due={'Minor':14,'Major':7,'Critical':3}; sev_mean={'Minor':10,'Major':6,'Critical':3}
insp_names=['R. Alvarez','T. Brooks','S. Nguyen','M. Patel']
pairs=[(p,s) for s in subs for p in random.sample(projects,3)]
insp=[];defs=[]
for (p,s) in pairs:
    for _ in range(22):
        ph=random.choices([0,1,2],[.3,.35,.35])[0]
        pf=min(.45,[.08,.17,.12][ph]*s[3]); r=random.choices([0,1,2],[1-pf-.18,.18,pf])[0]
        d=random.randint(0,ASOF)
        insp.append([len(insp)+1,p[0],s[0],phases[ph],d,res[r],random.choice(insp_names),ph,r])
for i in insp:
    iid,pid,sid,_,d,_,_,ph,r=i; f=subs[sid-1][3]
    n=0
    if r==2: n=1+(random.random()<.4)
    elif r==1 and random.random()<.35: n=1
    for _ in range(n):
        sv=random.choices(sevs,[.5,.38,.12] if r==2 else [1,0,0])[0]
        found=min(ASOF,d+random.randint(0,1)); due=found+sev_due[sv]
        close=found+max(1,int(random.gauss(sev_mean[sv]*f,3)))
        if close>ASOF or (found<=ASOF-20 and random.random()<.07*f): close=None
        defs.append([len(defs)+1,iid,pid,sid,random.choices(cats,[.45,.2,.15,.2])[0],sv,found,due,close])
mats=['Rebar','Structural steel','Gypsum board','Ductwork','Conduit and wire','Piping','Masonry units','Fire-rated assemblies','Roofing membrane','Flooring']
reasons=['Does not match approved submittal','Improper storage','Damaged on delivery','Missing certification']
mat=[]
for k in range(330):
    p,s=random.choice(pairs); d=random.randint(0,ASOF); bad=random.random()<min(.3,.07*s[3])
    rs=random.choices(reasons,[.4,.25,.2,.15])[0] if bad else ''
    mat.append([k+1,p[0],s[0],mats[s[0]-1],d,'N' if rs.startswith('Does') else 'Y','N' if rs.startswith('Improper') else 'Y','N' if bad else 'Y',rs])
tt=['Concrete cylinder break','Fireproofing thickness','Duct leakage','Pressure test','Grounding and megger']
tests=[[k+1,random.choice(projects)[0],random.choice(tt),random.randint(0,ASOF),'Pass' if random.random()<.93 else 'Fail'] for k in range(170)]
def w(name,hdr,rows):
    with open(f'data/{name}.csv','w',newline='') as fh:
        c=csv.writer(fh); c.writerow(hdr); c.writerows(rows)
w('projects',['project_id','project_name','project_type','location'],projects)
w('subcontractors',['sub_id','sub_name','trade'],[s[:3] for s in subs])
w('inspections',['inspection_id','project_id','sub_id','phase','inspection_date','result','inspector'],[[i[0],i[1],i[2],i[3],D(i[4]),i[5],i[6]] for i in insp])
w('deficiencies',['deficiency_id','inspection_id','project_id','sub_id','category','severity','date_found','due_date','date_closed','verified_by_qc'],[[x[0],x[1],x[2],x[3],x[4],x[5],D(x[6]),D(x[7]),D(x[8]) if x[8] is not None else '','Y' if x[8] is not None and random.random()<.93 else ('N' if x[8] is not None else '')] for x in defs])
w('material_receipts',['receipt_id','project_id','sub_id','material','receipt_date','matches_submittal','stored_properly','accepted','rejection_reason'],[m[:4]+[D(m[4])]+m[5:] for m in mat])
w('test_results',['test_id','project_id','test_type','test_date','result'],[[t[0],t[1],t[2],D(t[3]),t[4]] for t in tests])
db=sqlite3.connect('data/qc.db')
for n in ['projects','subcontractors','inspections','deficiencies','material_receipts','test_results']:
    rows=list(csv.reader(open(f'data/{n}.csv'))); h=rows[0]
    db.execute(f'drop table if exists {n}'); db.execute(f'create table {n} ({",".join(h)})')
    db.executemany(f'insert into {n} values ({",".join("?"*len(h))})',[[v if v!='' else None for v in r] for r in rows[1:]])
db.commit()
json.dump({'asof':ASOF,'proj':[p[1] for p in projects],'sub':[[s[1],s[2]] for s in subs],'phases':phases,'cats':cats,'reasons':reasons,'tests':tt,
 'insp':[[i[1]-1,i[2]-1,i[7],(base+dt.timedelta(days=i[4])).month-5,i[8]] for i in insp],
 'def':[[x[2]-1,x[3]-1,sevs.index(x[5]),cats.index(x[4]),x[6],x[7],-1 if x[8] is None else x[8]] for x in defs],
 'mat':[[m[1]-1,m[2]-1,1 if m[7]=='Y' else 0,reasons.index(m[8]) if m[8] else -1] for m in mat],
 'test':[[t[1]-1,tt.index(t[2]),1 if t[4]=='Pass' else 0] for t in tests]},open('data/dashboard_data.json','w'),separators=(',',':'))
print(len(insp),len(defs),len(mat),len(tests))
