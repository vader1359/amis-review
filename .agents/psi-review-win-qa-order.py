import asyncio, os, json, shutil, time, uuid, hashlib, faulthandler
faulthandler.dump_traceback_later(45, repeat=True)
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
import certifi,httpx
root=Path.cwd();qa=root/'outputs/psi-review-qa-20260906';qa.mkdir(parents=True,exist_ok=True,mode=0o700)
values={k:v.strip().strip('\"').strip("'") for line in Path('/home/iant1359/.local/share/psi-preview/private/runtime.env').read_text().splitlines() if '=' in line and not line.startswith('#') for k,v in [line.split('=',1)]}
u=urlsplit(values['PSI_REPORT_DATABASE_URL']);q=dict(parse_qsl(u.query));q['sslrootcert']=certifi.where();url=urlunsplit(u._replace(netloc=u.netloc.replace(u.hostname,'ep-floral-shadow-b3vc3mrv-pooler.c-4.ap-southeast-1.aws.neon.tech'),query=urlencode(q)))
os.environ['PSI_REPORT_DATABASE_URL']=url
os.environ['PSI_REPORT_ARTIFACT_DIR']=str(qa/'artifacts');os.environ['PSI_REPORT_SOURCE_DIR']=str(qa/'sources')
(qa/'artifacts').mkdir(mode=0o700,exist_ok=True)
sha='c8bb2fac04f254aaf32aef04249df314297e68e182363bf5602a73bc2c98ac44';dst=qa/'artifacts'/f'{sha}.xlsx';shutil.copyfile(Path('/home/iant1359/.local/share/psi-preview/artifacts')/f'{sha}.xlsx',dst);dst.chmod(0o600)
from web.review_sources import SourceBundleStore
from web.online_report_store import OnlineReportStore
from web.preview import create_app
rid='7676496e89804e12b4e7896aec8192c1';src,prior=SourceBundleStore(Path('/home/iant1359/.local/share/psi-preview/qa-review-20260906/bundles')).load(rid);SourceBundleStore(qa/'sources').save(rid,src,prior)
app=create_app(storage_dir=qa/'saved');store=OnlineReportStore(url)
rid='dc2ff67a82764cf99644722bc2afd961'
async def run():
 async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,client=('127.0.0.1',1234)),base_url='http://localhost',timeout=600) as c:
  config=(await c.get('/api/config')).json();c.headers['X-PSI-Preview']=config['preview_token']
  r=await c.get(f'/api/reports/{rid}/review');assert r.status_code==200,r.text[:300];review=r.json();assert review['can_rebuild'] and review['baseline']['status']=='available';print('Review PASS',review['summary'],flush=True)
  before=store.payload(rid); original=store.payload('7676496e89804e12b4e7896aec8192c1'); carried={(x[12],x[2]) for x in original['preorder_rows']} - {(x[12],x[2]) for x in before['preorder_rows']}; assert carried; target=next(x for x in review['preorder_checks'] if x['order_id'] and x['sku']); rev=review['proposals']['revision']
  data={'order_id':target['order_id'],'sku':target['sku'],'action':'exclude_order','note':'QA isolated branch: scoped exclusion validator','author':'QA isolated','expected_revision':rev,'request_id':uuid.uuid4().hex}
  r=await c.post(f'/api/reports/{rid}/proposals',json=data);assert r.status_code==200,r.text;proposal=r.json();assert (await c.post(f'/api/reports/{rid}/proposals',json=data)).json()==proposal
  conflict=await c.post(f'/api/reports/{rid}/proposals',json={**data,'note':'changed','request_id':uuid.uuid4().hex});assert conflict.status_code==409
  apply={'proposal_ids':[proposal['id']],'expected_revision':proposal['revision'],'author':'QA isolated','request_id':uuid.uuid4().hex}
  started=time.monotonic();r=await c.post(f'/api/reports/{rid}/apply',json=apply);assert r.status_code==202,r.text[:500];job=r.json()['job_id'];print('Job started',job,flush=True)
  while True:
   status=(await c.get('/api/review-jobs/'+job)).json()
   if status['status']!='running':break
   await asyncio.sleep(2)
  assert status['status']=='completed',status
  new=status['report'];elapsed=time.monotonic()-started;print('Rebuild PASS',round(elapsed,2),new['id'],flush=True)
  retry=await c.post(f'/api/reports/{rid}/apply',json=apply);assert retry.status_code==202 and retry.json()['job_id']==job,retry.text[:300]
  payload=store.payload(new['id']);assert not any(x[12]==target['order_id'] and x[2]==target['sku'] for x in payload['preorder_rows'])
  assert store.get('7676496e89804e12b4e7896aec8192c1')['workbook_sha256']==sha
  assert not any(x[12]==target['order_id'] for x in payload['preorder_rows'])
  assert not any(x[11]==target['order_id'] for x in payload['revenue_rows'])
  assert not any(x[0]==target['order_id'] for x in payload['crm_final_rows'])
  assert not ({(x[12],x[2]) for x in payload['preorder_rows']} & carried)
  assert store.get(rid)['workbook_sha256']=='2d2d56b9e4fd0c89fae1ca505af2fdff5810e154211121fa2cc2b81c0a2d19df'
  download=await c.get(new['download_url']);assert download.status_code==200;assert hashlib.sha256(download.content).hexdigest()==new['workbook_sha256']
  output={'review_summary':review['summary'],'rebuild_seconds':round(elapsed,2),'new_report':new,'retry':'PASS','scope_excluded':'PASS','carryforward_preorder_exclusions':'PASS','whole_order_absent_crm_revenue_preorder':'PASS','previous_report_immutable':'PASS','original_immutable':'PASS','download_sha':'PASS','proposal_revision_conflict':'PASS'}
  Path('.agents/psi-review-win-qa-order.json').write_text(json.dumps(output,indent=2));faulthandler.cancel_dump_traceback_later();print('All integrated QA PASS',flush=True)
asyncio.run(run())
