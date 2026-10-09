import scribus, json, traceback
from pathlib import Path
w=Path('/Users/wandl/.local/share/designcraft-validation/run-20261009')
r={'stage':'start'}
def record(): (w/'scribus-import.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
try:
 r['openResult']=scribus.openDoc('/Users/wandl/workspaces/workspace-agent-skills/full-aigc-skills-repositories/designcraft-skills/evidence/native/designcraft-cli-0.2.1/format-export-20261008/export.idml')
 r['stage']='opened';r['pages']=scribus.pageCount();r['pageData']=[];record()
 for page in range(1,r['pages']+1):
  scribus.gotoPage(page);items=[]
  for name,kind,order in scribus.getPageItems():
   item={'name':name,'kind':kind,'order':order}
   if kind==4: item['text']=scribus.getAllText(name);item['font']=scribus.getFont(name);item['overflow']=scribus.textOverflows(name)
   if kind==2: item['image']=scribus.getImageFile(name)
   items.append(item)
  r['pageData'].append({'page':page,'size':scribus.getPageSize(),'items':items})
 scribus.saveDocAs(str(w/'imported.sla'));r['stage']='saved';record()
 pdf=scribus.PDFfile();pdf.file=str(w/'scribus-import.pdf');pdf.pages=list(range(1,r['pages']+1));pdf.save()
 r['stage']='exported';record()
except Exception as error:
 r['error']=str(error);r['traceback']=traceback.format_exc();record()
