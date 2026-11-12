#!/usr/bin/env python3
"""Récupère deux photographies de Clitopilus prunulus via l'API Wikimedia Commons."""
import json, urllib.parse, urllib.request
from pathlib import Path

FILES=[
 ("File:Clitopilus prunulus 1421347.jpg","meunier_05.jpg"),
 ("File:Clitopilus prunulus 433076197.jpg","meunier_06.jpg"),
]
HEADERS={"User-Agent":"MycoMap/1.0 (mycological open-license photo collection; https://github.com/crosscrypto75/Mycomap)"}
folder=Path("assets/champignons/meunier")
folder.mkdir(parents=True,exist_ok=True)
for title,name in FILES:
  params=urllib.parse.urlencode({"action":"query","titles":title,"prop":"imageinfo","iiprop":"url|extmetadata","iiurlwidth":"900","format":"json"})
  req=urllib.request.Request("https://commons.wikimedia.org/w/api.php?"+params,headers=HEADERS)
  with urllib.request.urlopen(req,timeout=40) as response:
    payload=json.load(response)
  page=next(iter(payload["query"]["pages"].values()))
  info=page["imageinfo"][0]
  license=info["extmetadata"].get("LicenseShortName",{}).get("value","")
  if not (license.startswith("CC BY") or license.startswith("CC0")):raise ValueError("Licence inattendue "+license)
  url=info.get("thumburl") or info["url"]
  req=urllib.request.Request(url,headers=HEADERS)
  with urllib.request.urlopen(req,timeout=60) as response:data=response.read()
  if not data.startswith(b"\xff\xd8\xff") or len(data)<10000:raise ValueError("JPEG invalide "+name)
  (folder/name).write_bytes(data)
  print("Téléchargé",name,len(data),"octets",license,flush=True)
