import csv, hashlib, json, re, uuid, zipfile
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'sites.docx'
OUT = ROOT / 'config' / 'sources'
NS = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
NAMESPACE = uuid.UUID('6ba7b811-9dad-11d1-80b4-00c04fd430c8')

def normalize_url(v):
    v=v.strip(); v=re.sub(r'^(https?)://', lambda m:m.group(1).lower()+'://', v)
    if '#' in v: v=v.split('#',1)[0]
    return v[:-1]+'/' if v.endswith('/') else v
def canonical(v, typ):
    if typ=='x_account': return v.strip().lower()
    return normalize_url(v).lower()
def main():
    sha=hashlib.sha256(SRC.read_bytes()).hexdigest().upper()
    root=ET.fromstring(zipfile.ZipFile(SRC).read('word/document.xml'))
    rows=root.findall('.//w:tbl/w:tr',NS); headers=['News','Think Tanks','x']; occ=[]
    for ri,row in enumerate(rows[1:],1):
        for ci,c in enumerate(row.findall('./w:tc',NS)):
            val=''.join(x.text or '' for x in c.findall('.//w:t',NS)).strip()
            if not val: continue
            original=headers[ci]; typ={'News':'news','Think Tanks':'think_tank','x':'x_account'}[original]
            key=canonical(val,typ); sid=str(uuid.uuid5(NAMESPACE,typ+'|'+key))
            occ.append({'source_document':'sites.docx','source_document_sha256':sha,'table_index':0,'row_index':ri,'column_index':ci,'original_column':original,'raw_value':val,'extracted_value':val,'original_order':len(occ)+1,'extraction_method':'python-docx-xml'})
    groups={}
    for o in occ:
        typ={'News':'news','Think Tanks':'think_tank','x':'x_account'}[o['original_column']]; key=canonical(o['extracted_value'],typ); groups.setdefault((typ,key),[]).append(o)
    records=[]
    for (typ,key),items in groups.items():
        display=items[0]['extracted_value']; is_http=display.lower().startswith('http://'); review=[]
        if is_http: review.append('http_scheme_review')
        if display.lower()=='https://news.usni.org/': review.append('classification_review')
        records.append({'source_id':str(uuid.uuid5(NAMESPACE,typ+'|'+key)),'source_type':typ,'original_category':items[0]['original_column'],'canonical_category':typ,'display_value':display,'canonical_key':key,'url':display if typ!='x_account' else None,'x_handle':display if typ=='x_account' else None,'scheme':('http' if is_http else 'https') if typ!='x_account' else None,'hostname':(re.sub(r'^https?://','',key).split('/')[0]) if typ!='x_account' else None,'original_order':items[0]['original_order'],'occurrence_count':len(items),'duplicate_status':'duplicate' if len(items)>1 else 'unique','enabled':False,'validation_status':'not_tested','review_status':'needs_review' if review else 'not_reviewed','review_reasons':review,'collection_method':'not_assigned','collection_status':'not_started','last_checked_at':None,'notes':None,'provenance':[{'table_index':x['table_index'],'row_index':x['row_index'],'column_index':x['column_index'],'raw_value':x['raw_value']} for x in items]})
    decisions=json.loads((OUT/'source-review-decisions.json').read_text()) if (OUT/'source-review-decisions.json').exists() else []
    for d in decisions:
        r=next(r for r in records if r['source_id']==d['source_id']); r['url']=d['approved_canonical_value']; r['canonical_key']=d['approved_canonical_value'].lower(); r['scheme']='https'; r['hostname']=re.sub(r'^https?://','',r['canonical_key']).split('/')[0]; r['canonical_category']=d.get('approved_canonical_category',r['canonical_category']); r['review_status']='resolved'; r['review_reasons']=[]
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'source-registry.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (OUT/'source-occurrences.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=occ[0].keys()); w.writeheader(); w.writerows(occ)
    with (OUT/'source-registry.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=records[0].keys()); w.writeheader(); [w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in r.items()}) for r in records]
    with (OUT/'source-review.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(['source_id','review_status','review_reasons']); [w.writerow([r['source_id'],r['review_status'],';'.join(r['review_reasons'])]) for r in records if r['review_reasons']]
    (OUT/'registry-metadata.json').write_text(json.dumps({'source_document':'sites.docx','source_document_sha256':sha,'raw_source_count':len(occ),'canonical_source_count':len(records),'generated_by':'build_source_registry.py','stable_id_algorithm':'UUIDv5 DNS namespace; source_type|canonical_key'},indent=2)+'\n')
    print(json.dumps({'raw':len(occ),'canonical':len(records),'news':sum(r['source_type']=='news' for r in records),'think_tank':sum(r['source_type']=='think_tank' for r in records),'x':sum(r['source_type']=='x_account' for r in records)},sort_keys=True))
if __name__=='__main__': main()
