#!/usr/bin/env python3
"""Télécharge des photos Wikimedia Commons libres, avec attribution vérifiable."""
import json, os, re, time, urllib.parse, urllib.request
from pathlib import Path

SPECIES = {
 "cepe-de-bordeaux": "Boletus edulis",
 "girolle": "Cantharellus cibarius",
 "trompette-de-la-mort": "Craterellus cornucopioides",
 "pied-de-mouton": "Hydnum repandum",
 "chanterelle-en-tube": "Craterellus tubaeformis",
 "coulemelle": "Macrolepiota procera",
 "meunier": "Clitopilus prunulus",
 "amanite-phalloide": "Amanita phalloides",
 "russules": "Russula",
 "lactaire-delicieux": "Lactarius deliciosus",
 "lactaire-tranquille": "Lactarius quietus",
}
ROOT=Path("assets/champignons")
API="https://commons.wikimedia.org/w/api.php"
HEADERS={"User-Agent":"MycoMap/0.1 (open-license scientific photo catalogue; contact via GitHub crosscrypto75/Mycomap)"}
def request(url):
 req=urllib.request.Request(url,headers=HEADERS)
 with urllib.request.urlopen(req,timeout=35) as resp:return resp.read()
def api(params):
 params["format"]="json"
 return json.loads(request(API+"?"+urllib.parse.urlencode(params)))
def plain(html):
 return re.sub(r"<[^>]*>","",html or "").strip()
def allowed(license_name):
 return bool(re.match(r"^(CC0|CC BY(?:-SA)?(?: |$)|Public domain|PD(?:-|$))",license_name,re.I))
def main():
 ROOT.mkdir(parents=True,exist_ok=True)
 manifest={}
 for slug,name in SPECIES.items():
  print("Espèce",name,flush=True)
  manifest[name]=[]
  try:
   search=api({"action":"query","generator":"categorymembers","gcmtitle":"Category:"+name,"gcmtype":"file","gcmlimit":100,"prop":"imageinfo","iiprop":"url|extmetadata","iiurlwidth":720})
   pages=list(search.get("query",{}).get("pages",{}).values())
   if not pages:
    search=api({"action":"query","generator":"search","gsrsearch":"filetype:bitmap "+name,"gsrnamespace":6,"gsrlimit":40,"prop":"imageinfo","iiprop":"url|extmetadata","iiurlwidth":720})
    pages=list(search.get("query",{}).get("pages",{}).values())
   candidates=[]
   for page in pages:
    info=(page.get("imageinfo") or [{}])[0];meta=info.get("extmetadata") or {}
    license_name=plain(meta.get("LicenseShortName",{}).get("value"))
    title=page.get("title","")
    if not allowed(license_name) or not re.search(r"\.(jpg|jpeg|png)$",title,re.I):continue
    if name.lower() not in (title+" "+plain(meta.get("ImageDescription",{}).get("value"))).lower():continue
    url=info.get("thumburl")
    if not url:continue
    t=title.lower()
    score=3*bool(re.search(r"cut|cross.section|section|schnitt|coupe",t))+2*bool(re.search(r"gill|lamell|pore|stem|stipe|underside",t))+bool(re.search(r"habitat|forest|wood",t))-5*bool(re.search(r"stamp|illustration|drawing|plate",t))
    candidates.append((score,title,url,info,meta,license_name))
   candidates.sort(key=lambda x:(-x[0],x[1]))
   directory=ROOT/slug;directory.mkdir(exist_ok=True)
   for _,title,url,info,meta,license_name in candidates:
    if len(manifest[name])>=4:break
    number=len(manifest[name])+1
    ext=".png" if title.lower().endswith(".png") else ".jpg"
    filename=f"{slug}_{number:02d}{ext}"
    try:
     data=request(url)
     if len(data)<8000 or len(data)>3500000:continue
     if not (data.startswith(b"\xff\xd8\xff") or data.startswith(b"\x89PNG")):continue
     (directory/filename).write_bytes(data)
     manifest[name].append({"file":f"assets/champignons/{slug}/{filename}","scientificName":name,"commonsTitle":title,"source":info.get("descriptionurl"),"license":license_name,"licenseUrl":plain(meta.get("LicenseUrl",{}).get("value")),"author":plain(meta.get("Artist",{}).get("value"))[:400],"attribution":plain(meta.get("Attribution",{}).get("value"))[:400]})
     print(" OK",filename,len(data),flush=True)
    except Exception as e:print(" image error",str(e),flush=True)
   time.sleep(.3)
  except Exception as e:print(" category error",name,str(e),flush=True)
 (ROOT/"credits.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("Total images",sum(map(len,manifest.values())),flush=True)
if __name__=="__main__":main()
