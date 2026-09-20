import hashlib,json,time
from pathlib import Path
import httpx
root=Path('/Users/iant1359/Develop/amis-review')
golden=json.loads((root/'outputs/01a04de8-3702-72e2-93b3-7da56b5c90fa/psi-2026-09-03/psi_20260903_data.json').read_text())
roles={'crm':'CRM Sales Order','product':'Product Master','revenue':'Revenue','inventory':'Inventory'}
with httpx.Client(base_url='http://127.0.0.1:18787',timeout=600) as client:
 config=client.get('/api/config').json()
 assert config['report_storage']=={'enabled':True,'provider':'neon'}
 assert len(config['saved_sources'])==4
 data={'as_of':'2026-09-03'}
 for role,metadata in config['saved_sources'].items():
  data[role]=metadata['id']
 files={}
 for role,label in roles.items():
  path=Path(golden['sources'][label]);content=path.read_bytes()
  assert hashlib.sha256(content).hexdigest()==golden['source_hashes'][label]
  files[role]=(path.name,content,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
 started=time.monotonic()
 response=client.post('/api/drafts',data=data,files=files,headers={'X-PSI-Preview':config['preview_token']})
 if response.status_code!=200:
  print('Save failed',response.status_code,response.text[:500]);raise SystemExit(1)
 report=response.json()
 assert report['storage']=='neon' and report['state']=='draft' and report['sheet_count']==17
 assert report['workbook_sha256']=='c8bb2fac04f254aaf32aef04249df314297e68e182363bf5602a73bc2c98ac44'
 evidence={'save_seconds':round(time.monotonic()-started,2),'report':report}
 history=client.get('/api/reports').json()
 assert any(item['id']==report['id'] for item in history['reports'])
 sheets=client.get('/api/reports/'+report['id']+'/sheets').json()['sheets']
 assert len(sheets)==17
 evidence['sheets']=sheets
 out=root/'.agents/psi-online-persistence-live.json';out.write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
 print(json.dumps({'saved_online':True,'id':report['id'],'sheet_count':len(sheets),'cells':sum(s['cell_count'] for s in sheets),'seconds':evidence['save_seconds'],'workbook_sha256':report['workbook_sha256']}))
