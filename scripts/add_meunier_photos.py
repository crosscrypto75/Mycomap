#!/usr/bin/env python3
import json, urllib.parse, urllib.request
from pathlib import Path
files=[("Clitopilus prunulus 1421347.jpg","meunier_05.jpg"),("Clitopilus prunulus 228129445.jpg","meunier_06.jpg")]
folder=Path("assets/champignons/meunier")
folder.mkdir(parents=True,exist_ok=True)
for title,name in files:
  url="https://commons.wikimedia.org/wiki/Special:Redirect/file/"+urllib.parse.quote(title)+"?width=900"
  req=urllib.request.Request(url,headers={"User-Agent":"MycoMap/0.1 (scientific mushroom photo gallery; GitHub crosscrypto75/Mycomap)"})
  with urllib.request.urlopen(req,timeout=60) as resp:data=resp.read()
  if not data.startswith(b"\xff\xd8\xff") or len(data)<10000:raise ValueError("Invalid JPEG: "+name)
  (folder/name).write_bytes(data)
  print("Downloaded",name,len(data))
