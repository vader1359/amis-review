from pathlib import Path
import os,certifi
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
values={k:v.strip().strip('\"').strip("'") for line in Path('.env').read_text().splitlines() if '=' in line and not line.startswith('#') for k,v in [line.split('=',1)]}
u=urlsplit(values['PSI_REPORT_DATABASE_URL']);q=dict(parse_qsl(u.query));q['sslrootcert']=certifi.where();os.environ['PSI_REPORT_DATABASE_URL']=urlunsplit(u._replace(netloc=u.netloc.replace(u.hostname,'ep-floral-shadow-b3vc3mrv-pooler.c-4.ap-southeast-1.aws.neon.tech'),query=urlencode(q)))
qa=Path.cwd()/'outputs/psi-review-qa-20260906';os.environ['PSI_REPORT_ARTIFACT_DIR']=str(qa/'artifacts');os.environ['PSI_REPORT_SOURCE_DIR']=str(qa/'sources')
from web.preview import create_app
import uvicorn
uvicorn.run(create_app(storage_dir=qa/'saved'),host='127.0.0.1',port=18789,access_log=False)
