# MycoMap — préparation de l'IA locale (prototype)

## Modèle champignons retenu pour le premier essai

- Source : https://huggingface.co/mlgraham/species-classifier-fungi
- Fichiers : `fungi_int8.tflite`, `labels.txt`, `classes.json`.
- Poids : Apache-2.0 selon la fiche du modèle ; conserver les mentions de licence et vérifier les obligations avant distribution.
- Entrée : RGB uint8, [1,160,160,3], recadrage central carré.
- Sortie : [1,341] uint8 ; score = valeur/256. Le score **n'est pas une probabilité de comestibilité**.
- Mesure publiée : 74 % top-1 / 93,5 % top-5 sur un jeu de validation limité ; **pas une validation en forêt française**.

## Téléchargement

Exécuter `python scripts/download_fungi_model.py` depuis la racine du dépôt. Le script télécharge les fichiers dans `models/fungi/` et vérifie qu'ils sont non vides. Il ne les téléverse pas sur GitHub.

## Étapes bloquantes avant un test sur iPhone

1. Installer un moteur LiteRT/TFLite compatible avec Safari et vérifier les restrictions WebAssembly.
2. Servir le modèle depuis une URL HTTPS stable et autorisée par CORS, ou l'héberger dans le dépôt avec Git LFS / releases, puis le mettre en cache localement.
3. Implémenter le prétraitement des photos, la correspondance des labels, et un refus explicite si espèce hors des 341 classes.
4. Vérifier la reconnaissance hors ligne, sur plusieurs photographies, avec des cas d'espèces proches.
5. Intégrer les fiches de l'encyclopédie et les critères de confusion. Ne jamais certifier la comestibilité.

**État : modèle identifié, téléchargement automatisé, inférence navigateur non intégrée. L'onglet Identifier ne doit pas annoncer une IA fonctionnelle tant que ces étapes ne sont pas testées.**
