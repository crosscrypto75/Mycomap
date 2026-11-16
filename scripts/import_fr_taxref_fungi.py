#!/usr/bin/env python3
"""Import the French TAXREF fungal checklist from the published v18 archive.

This is a taxonomy checklist, NOT occurrence data or evidence of edibility.
"""
import csv
import io
import json
import os
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SOURCE = os.getenv("MYCOMAP_TAXREF_URL", "https://geonature.fr/data/inpn/taxonomie/TAXREF_v18_2025.zip")
OUTPUT = Path("data/mycology/france-taxref-fungi.json")
FUNGAL_KINGDOMS = {"Fungi"}

def main():
    req = urllib.request.Request(SOURCE, headers={"User-Agent": "MycoMap-TAXREF-import/1.0"})
    with urllib.request.urlopen(req, timeout=180) as response:
        archive = response.read(120_000_001)
    if len(archive) > 120_000_000:
        raise RuntimeError("Archive exceeds the 120 MB safety limit")
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        candidates = [n for n in z.namelist() if n.lower().endswith(".txt") and "taxref" in n.lower() and "change" not in n.lower() and "liens" not in n.lower()]
        if not candidates:
            raise RuntimeError("No TAXREF main TXT found in archive")
        name = min(candidates, key=len)
        with z.open(name) as fh:
            content = io.TextIOWrapper(fh, encoding="utf-8-sig", errors="replace", newline="")
            reader = csv.DictReader(content, delimiter="\t")
            fields = set(reader.fieldnames or [])
            required = {"REGNE", "RANG", "CD_NOM", "CD_REF", "LB_NOM", "FR"}
            if not required.issubset(fields):
                raise RuntimeError("Unexpected TAXREF columns: " + str(sorted(fields)))
            records = []
            statuses = Counter()
            for row in reader:
                if row["REGNE"].strip() not in FUNGAL_KINGDOMS or row["RANG"].strip() != "ES":
                    continue
                if row["CD_NOM"].strip() != row["CD_REF"].strip():
                    continue
                status = row["FR"].strip()
                statuses[status or "(blank)"] += 1
                records.append({"cdNom": int(row["CD_NOM"]), "name": row["LB_NOM"].strip(),
                                "family": row.get("FAMILLE", "").strip(), "frStatus": status})
    if len(records) < 1000:
        raise RuntimeError("Too few accepted fungal species: refusing to overwrite existing reference")
    records.sort(key=lambda r: (r["name"].casefold(), r["cdNom"]))
    payload = {"schemaVersion": 1, "source": "TAXREF v18 (MNHN/PatriNat), GeoNature distribution mirror",
               "sourceUrl": SOURCE, "generatedAt": datetime.now(timezone.utc).isoformat(),
               "scope": "Accepted Fungi species in TAXREF; FR field preserved without inferring presence from blanks",
               "caveats": ["Checklist is not occurrence data.", "FR status codes must be interpreted using TAXREF's status legend.",
                           "No identification, toxicity or edibility claim is implied.", "French overseas taxa are not excluded by this checklist."],
               "frStatusCounts": dict(statuses), "taxa": records}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUTPUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    tmp.replace(OUTPUT)
    print("TAXREF imported:", len(records), "accepted fungal species; status counts:", dict(statuses), flush=True)

if __name__ == "__main__":
    main()
