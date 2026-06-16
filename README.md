# Jeux de lettres — Le Coq Francis

## Structure
```
Jeux de lettres/
├── Dictionnaires/
│   ├── dict_fr.js      ← dictionnaire unifié FR (window.DICT_FR)
│   └── dict_en.js      ← dictionnaire unifié EN (window.DICT_EN)
├── Visuels/
│   ├── coq_coeur.png
│   ├── coq_pilote.png
│   ├── coq_stupefait.png
│   └── coq_triste.png
├── Motus/
│   └── index.html
├── Mots fléchés/
│   └── index.html
└── Mots mêlés/
    └── index.html
```

## Dictionnaire unifié
Chaque langue = 1 seul fichier. Chargé localement par chaque jeu via :
```html
<script src="../Dictionnaires/dict_fr.js"></script>
<script src="../Dictionnaires/dict_en.js"></script>
```

Format : `window.DICT_FR` / `window.DICT_EN`, avec :
- `answers` : mots jouables (communs), 3–9 lettres
- `valid`   : mots acceptés comme tentatives (triés A→Z, recherche binaire)
- `defs`    : { MOT: "définition" } pour les jeux à indices

Helpers fournis :
- `DICT.pick(len)`          → mot-réponse aléatoire de longueur `len`
- `DICT.isValid(word)`      → mot accepté ?
- `DICT.clue(word)`         → définition ou null
- `DICT.byLength(len,kind)` → liste filtrée (kind = "answers" | "valid")

## Comment chaque jeu utilise la base
- **Motus**       : `DICT.pick(len)` + `DICT.isValid()` (n'utilise pas les définitions)
- **Mots mêlés**  : `DICT.answers` (liste de mots, pas de définitions)
- **Mots fléchés**: construit sa banque à partir de `DICT.defs` (mots + indices)

## Ajouter un nouveau jeu (ex. Pendu)
1. Créer un dossier `Pendu/` avec son `index.html`.
2. Ajouter les deux balises `<script src="../Dictionnaires/dict_*.js">`.
3. Piocher dans `DICT.answers` (mot à deviner) et `DICT.clue(mot)` (indice).
Aucun mot à recopier dans le jeu : tout vient du dictionnaire unique.
