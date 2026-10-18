#!/usr/bin/env python3
"""Add CLDR spoken names without changing existing aliases or stopwords.

Names distinguish an emoji's subject from a loose search association. Optional
metadata is backward compatible with version-1 clients. Sources are pinned to
Unicode CLDR release-48; existing vendored app annotations take precedence.
"""
from pathlib import Path
import concurrent.futures, hashlib, json, urllib.request, xml.etree.ElementTree as ET
root=Path(__file__).resolve().parents[1]
app=root.parents[1]
cache=app/'test-results/typing-breadth/cldr'
cache.mkdir(parents=True,exist_ok=True)
manifest={}
def read(code,derived):
 name=code+('-derived' if derived else '')+'.xml'
 local=app/'Tools/cldr-annotations'/name
 if local.exists():return local.read_bytes(),str(local.relative_to(app))
 folder='annotationsDerived' if derived else 'annotations'
 url=f'https://raw.githubusercontent.com/unicode-org/cldr/release-48/common/{folder}/{code}.xml'
 path=cache/name
 if not path.exists():
  try:
   with urllib.request.urlopen(url,timeout=30) as r:data=r.read()
  except Exception as e:return None,str(e)
  path.write_bytes(data)
 return path.read_bytes(),url
paths=[p for p in root.glob('Lexicons/*.emoji.json') if not p.name.startswith('._')]
codes=sorted({p.name.removesuffix('.emoji.json').split('_')[0] for p in paths})
def load(code):
 names={};sources=[]
 for derived in [False,True]:
  data,source=read(code,derived)
  if data is None:continue
  sources.append({'source':source,'sha256':hashlib.sha256(data).hexdigest()})
  for e in ET.fromstring(data).findall('.//annotation'):
   glyph=e.get('cp','')
   if e.get('type')!='tts' or not e.text or any(0x1f3fb<=ord(c)<=0x1f3ff for c in glyph):continue
   key=''.join(c for c in glyph if ord(c)!=0xfe0f)
   names[key]=e.text.strip()
 return code,names,sources
loaded={}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for code,names,sources in pool.map(load,codes):loaded[code]=names;manifest[code]=sources
for p in paths:
 obj=json.loads(p.read_text());code=p.name.removesuffix('.emoji.json').split('_')[0]
 if code == 'en':
  obj.pop('names', None)
  p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
  continue
 names={k:v for k,v in loaded[code].items() if k in obj['aliases']}
 if not names:
  print('No names available; retaining aliases:',code,flush=True);continue
 obj['names']=dict(sorted(names.items()))
 p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
 (app/'Resources/CorrectionContexts'/(p.name.removesuffix('.emoji.json')+'.enames')).write_text(json.dumps(names,ensure_ascii=False,separators=(',',':'))+'\n')
 print(p.name,len(names),flush=True)
(root/'emoji-name-provenance.json').write_text(json.dumps(manifest,indent=2)+'\n')
