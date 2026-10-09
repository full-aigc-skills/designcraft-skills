import scribus, json, traceback, hashlib
from pathlib import Path
w=Path('/Users/wandl/.local/share/designcraft-validation/run-20261009/qualified');w.mkdir(exist_ok=True)
r={'stage':'started','fontEnvironment':'project SourceSans3 and SourceSerif4 installed with OFL licenses'}
def record(): (w/'report.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
def inspect():
 pages=[]
 for p in range(1,scribus.pageCount()+1):
  scribus.gotoPage(p);items=[]
  for name,kind,order in scribus.getPageItems():
   item={'name':name,'kind':kind,'order':order}
   if kind==4:item.update(text=scribus.getAllText(name),font=scribus.getFont(name),overflow=scribus.textOverflows(name))
   if kind==2:item['image']=scribus.getImageFile(name)
   items.append(item)
  pages.append({'page':p,'size':scribus.getPageSize(),'items':items})
 return pages
def images(prefix):
 result=[]
 for p in range(1,scribus.pageCount()+1):
  scribus.gotoPage(p);out=w/(prefix+'-'+str(p)+'.png');im=scribus.ImageExport();im.type='PNG';im.dpi=72;im.scale=100
  value=im.saveAs(str(out));result.append({'page':p,'returned':value,'exists':out.exists(),'path':str(out)})
 return result
record()
try:
 r['availableSourceFonts']=[x for x in scribus.getFontNames() if x.startswith(('Source Sans 3','Source Serif 4'))];record()
 r['openResult']=scribus.openDoc('/Users/wandl/workspaces/workspace-agent-skills/full-aigc-skills-repositories/designcraft-skills/evidence/native/designcraft-cli-0.2.1/format-export-20261008/export.idml')
 scribus.setUnit(scribus.UNIT_POINTS);r['imported']=inspect();r['stage']='imported';record()
 r['beforeImages']=images('before');record()
 scribus.saveDocAs(str(w/'imported.sla'));scribus.closeDoc();scribus.openDoc(str(w/'imported.sla'));r['reopened']=inspect();r['stage']='reopened';record()
 targets=[i for p in r['reopened'] for i in p['items'] if i.get('text','').strip()=='A Better Grid']
 if len(targets)!=1:raise ValueError('expected exactly one third-page heading')
 name=targets[0]['name'];scribus.setText('A Better Grid — IDML edit check',name)
 scribus.saveDocAs(str(w/'edited.sla'));scribus.closeDoc();scribus.openDoc(str(w/'edited.sla'));r['editedReopened']=inspect();r['afterImages']=images('after');r['stage']='complete';record()
except Exception as e:
 r['error']=str(e);r['traceback']=traceback.format_exc();record()
