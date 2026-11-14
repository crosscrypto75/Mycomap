#!/usr/bin/env python3
"""Télécharge les fichiers publics du prototype Fungi (sans dépendance externe)."""
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

BASE = 'https://huggingface.co/mlgraham/species-classifier-fungi/resolve/main/'
DEST = Path(__file__).resolve().parents[1] / 'models' / 'fungi'
FILES = ('fungi_int8.tflite', 'labels.txt', 'classes.json')

def main():
    DEST.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        target = DEST / name
        if target.exists() and target.stat().st_size:
            print(f'Déjà présent : {target}')
            continue
        temp = target.with_suffix(target.suffix + '.part')
        try:
            req = Request(BASE + name, headers={'User-Agent': 'MycoMap-model-preparation/0.1'})
            with urlopen(req, timeout=60) as response, temp.open('wb') as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            if not temp.stat().st_size:
                raise ValueError('Fichier vide')
            temp.replace(target)
            print(f'Téléchargé : {target} ({target.stat().st_size} octets)')
        except (URLError, HTTPError, OSError, ValueError) as exc:
            temp.unlink(missing_ok=True)
            raise SystemExit(f'Échec du téléchargement de {name} : {exc}') from exc
    print('Fichiers prêts pour la future intégration LiteRT locale.')

if __name__ == '__main__':
    main()
