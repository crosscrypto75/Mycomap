#!/usr/bin/env python3
"""Rechercher des illustrations candidates sur Wikimedia Commons, sans publier automatiquement."""
import json, re, sys, time
import ast
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "index.html"
OUTPUT = ROOT / "data/encyclopedia/commons-candidates.json"
API = "https://commons.wikimedia.org/w/api.php"
ALLOWED = re.compile(r"^(CC0|Public domain|CC BY(?:-[0-9.]+)?|CC BY-SA(?:-[0-9.]+)?)$", re.I)

def query(params):
    url = API + "?" + urlencode(dict(params, action="query", format="json", formatversion=2))
    with urlopen(Request(url, headers={"User-Agent": "MycoMap-Encyclopedia/0.1 (image license research)"}), timeout=25) as r:
        return json.load(r)

def val(metadata, name):
    return metadata.get(name, {}).get("value", "")

def main():
    # Utiliser le catalogue réellement affiché par MycoMap (pas seulement champi2).
    html = SOURCE.read_text(encoding="utf-8")
    start = html.index("const catalog=") + len("const catalog=")
    end = html.index("];", start) + 1
    initial = ast.literal_eval(html[start:end])
    match = re.search(r"catalog\\.push\\(\\.\\.\\.(\\[\\[.*?\\]\\])\\);", html, re.S)
    extra = json.loads(match.group(1)) if match else []
    names = list(dict.fromkeys(row[1] for row in initial + extra))
    records = [{"id": re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-"),
                "scientific_name": name} for name in names]
    print(f"Recherche pour {len(records)} entrées du catalogue.")
    results = []
    for entry in records:
        name = entry["scientific_name"]
        try:
            response = query({"generator": "search", "gsrsearch": name + " filetype:bitmap", "gsrnamespace": 6, "gsrlimit": 12, "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": 640})
            for page in response.get("query", {}).get("pages", []):
                info = (page.get("imageinfo") or [{}])[0]
                meta = info.get("extmetadata") or {}
                license_name = re.sub("<[^>]+>", "", val(meta, "LicenseShortName")).strip()
                if not ALLOWED.fullmatch(license_name):
                    continue
                results.append({"species_id": entry["id"], "scientific_name": name,
                    "file_title": page.get("title"), "description_url": info.get("descriptionurl"),
                    "image_url": info.get("url"), "thumbnail_url": info.get("thumburl"),
                    "license": license_name, "license_url": val(meta, "LicenseUrl"),
                    "artist_html": val(meta, "Artist"), "credit_html": val(meta, "Credit"),
                    "review_status": "CANDIDATE_ONLY_NOT_VERIFIED",
                    "note": "Vérifier manuellement identification, licence exacte, auteurs et attribution avant usage."})
            time.sleep(0.2)
        except Exception as exc:
            print(f"Recherche impossible pour {name}: {exc}", file=sys.stderr)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({"status": "candidates_only", "images": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(results)} candidates dans {OUTPUT}. Aucune image n'est publiée.")

if __name__ == "__main__":
    main()
