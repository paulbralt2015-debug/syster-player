# Syster Player

Lecteur vidéo expérimental qui reconstitue en temps réel les images
brouillées par permutation de lignes (type Syster / Nagravision analogique),
sans clé, par analyse de la continuité de l'image.

## Lancer
    pip install -r requirements.txt
    python player.py [fichier.mp4]

## Commandes
- Espace : lecture / pause
- D : décodage activé / désactivé
- F : inverser haut/bas
- ← / → : -5 s / +5 s
- Menu Qualité : Rapide (plus fluide) / Normal / Précis (plus lent)

## Limites
- Vidéo seulement, pas de son (OpenCV ne lit pas l'audio).
- Si l'ordinateur est trop lent, des images sont sautées pour rester en temps réel.
- Résultats partiels sur des vidéos recompressées (ex. YouTube) ou des scènes
  très sombres/unies.

## Version ligne de commande
    python descramble.py entree.mp4 sortie.mp4

## Avertissement
À utiliser uniquement sur des enregistrements dont vous détenez les droits
(archives personnelles, restauration). Ne publiez aucune vidéo dans ce dépôt.
