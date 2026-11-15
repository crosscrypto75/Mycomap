#!/usr/bin/env python3
"""Recherche de photos candidates Commons pour le catalogue publié MycoMap.

Ne publie aucune image. Produit un inventaire et un rapport de couverture/erreurs.
"""
import html
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "index.html"
OUTPUT = ROOT / "data/encyclopedia/commons-candidates.json"
REPORT = ROOT / "data/encyclopedia/commons-coverage.json"
API = "https://commons.wikimedia.org/w/api.php"
LICENSE_RE = re.compile(r"^(?:CC0(?: 1\\.0)?|Public domain|PD(?:-[\\w.]+)?|CC BY(?:-[\\w.]+)?|CC BY-SA(?:-[\\w.]+)?)$", re.I)
IMAGE_RE = re.compile(r"\\.(?:jpe?g|png|webp)$", re.I)
HEADERS = {"User-Agent": "MycoMap/0.2 (educational photo candidate research; GitHub crosscrypto75/Mycomap)"}


def catalog_names():
    source = CATALOG.read_text(encoding="utf-8")
    start = source.index("const catalog=") + len("const catalog=")
    end = source.index("];", start) + 1
    initial = json.loads(source[start:end])
    match = re.search(r"catalog\.push\(\.\.\.([\s\S]*?)\);", source)
    extra = json.loads(match.group(1)) if match else []
    names = list(dict.fromkeys(row[1] for row in initial + extra))
    if len(names) < 70:
        raise RuntimeError(f"Catalogue incomplet : {len(names)} noms trouvés (minimum attendu : 70)")
    return names


def query(params, attempts=3):
    args = dict(params, action="query", format="json", formatversion=2)
    url = API + "?" + urlencode(args)
    for attempt in range(attempts):
        try:
            with urlopen(Request(url, headers=HEADERS), timeout=25) as response:
                data = json.load(response)
            if "error" in data:
                raise RuntimeError(str(data["error"]))
            return data
        except (HTTPError, URLError, TimeoutError, ValueError, RuntimeError) as exc:
            if attempt == attempts - 1:
                raise
            time.sleep(2 ** attempt)


def clean(value):
    return html.unescape(re.sub(r"<[^>]*>", "", value or "")).strip()


def images_from_response(response, scientific_name, species_id, seen):
    candidates = []
    for page in response.get("query", {}).get("pages", []):
        title = page.get("title", "")
        if not IMAGE_RE.search(title):
            continue
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        license_name = clean(meta.get("LicenseShortName", {}).get("value", ""))
        if not LICENSE_RE.fullmatch(license_name):
            continue
        file_url = info.get("descriptionurl")
        if not file_url or file_url in seen:
            continue
        seen.add(file_url)
        candidates.append({
            "species_id": species_id, "scientific_name": scientific_name,
            "file_title": title, "description_url": file_url,
            "image_url": info.get("url"), "thumbnail_url": info.get("thumburl"),
            "license": license_name, "license_url": meta.get("LicenseUrl", {}).get("value", ""),
            "artist_html": meta.get("Artist", {}).get("value", ""),
            "credit_html": meta.get("Credit", {}).get("value", ""),
            "review_status": "CANDIDATE_ONLY_NOT_VERIFIED",
            "note": "Identification, droits, auteur et attribution à vérifier avant publication."
        })
    return candidates


def main():
    names = catalog_names()
    results, coverage = [], []
    print(f"Catalogue : {len(names)} noms scientifiques distincts.", flush=True)
    for index, name in enumerate(names, 1):
        species_id = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        search_name = re.sub(r"\\s+(?:agg\\.|spp\\.)$", "", name).strip()
        found, errors, seen = [], [], set()
        # Deux approches complémentaires : catégorie taxonomique puis recherche de fichiers.
        searches = [
            {"generator": "categorymembers", "gcmtitle": "Category:" + search_name,
             "gcmtype": "file", "gcmlimit": 35},
            {"generator": "search", "gsrsearch": 'intitle:"' + search_name + '"',
             "gsrnamespace": 6, "gsrlimit": 30}
        ]
        for params in searches:
            try:
                response = query(dict(params, prop="imageinfo",
                                      iiprop="url|extmetadata", iiurlwidth=640))
                found.extend(images_from_response(response, name, species_id, seen))
            except Exception as exc:
                errors.append(f"{type(exc).__name__}: {exc}")
            if len(found) >= 8:
                break
            time.sleep(0.1)
        results.extend(found[:12])
        coverage.append({"scientific_name": name, "candidate_count": min(len(found), 12),
                         "errors": errors, "status": "error" if errors and not found else
                         ("found" if found else "no_candidate")})
        print(f"[{index}/{len(names)}] {name}: {len(found)} candidates; {len(errors)} erreurs", flush=True)
    counts = Counter(item["status"] for item in coverage)
    report = {"species_total": len(names), "species_with_candidates": counts["found"],
              "species_without_candidates": counts["no_candidate"],
              "species_with_errors": counts["error"],
              "image_candidates_total": len(results), "species": coverage}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({"status": "candidates_only", "images": results},
                                 ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "species"}, ensure_ascii=False), flush=True)
    # Des échecs réseau isolés sont enregistrés, pas masqués par un succès sans rapport.
    if counts["error"] == len(names):
        sys.exit("Toutes les recherches ont échoué : voir commons-coverage.json")


if __name__ == "__main__":
    main()
