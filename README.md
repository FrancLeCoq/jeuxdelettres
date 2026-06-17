# Le Coq Francis — Jeux de lettres

Ensemble de jeux de lettres HTML (Telegram WebApp) partageant **un dictionnaire unique par langue**.

## Structure

```
Jeux de lettres/
├── Dictionnaires/
│   ├── dict_fr.js              # dictionnaire FR complet (window.DICT_FR)
│   ├── dict_en.js              # dictionnaire EN complet (window.DICT_EN)
│   ├── mots_faciles_fr.txt     # liste lisible du pool "courant" FR
│   └── mots_faciles_en.txt     # liste lisible du pool "courant" EN
├── Visuels/                    # images partagees (coq_*.png)
├── Motus/index.html
├── Motsfleches/index.html
├── Motsmeles/index.html
└── README.md
```

Chaque jeu charge le dictionnaire via `<script src="../Dictionnaires/dict_fr.js"></script>`
et les images via `../Visuels/...`. Le "cerveau" (logique du jeu) reste leger ; toute la
donnee vit dans le dictionnaire, partage par les trois jeux.

## Le dictionnaire (window.DICT_FR / window.DICT_EN)

| Cle | Contenu |
|-----|---------|
| `answers` | Mots jouables 3-9 lettres, **tous definis**, tries par frequence (courants en tete) |
| `easy`    | Pool "courant" : mots frequents pleins (hors mots-outils), ordonnes par frequence |
| `valid`   | Tous les mots acceptes a la saisie (tries A->Z, recherche binaire) |
| `defs`    | Dictionnaire {MOT: "definition"} |
| `stop`    | Mots-outils exclus des pools "courant" |

### Couverture des definitions

**100 % des mots jouables ont une definition exploitable** dans les deux langues.
Le pool Mots fleches est donc identique au pool Mots meles (plus de differentiel).

### Helpers principaux

- `pick(len)` — tire un mot d'une longueur donnee
- `isValid(word)` — mot accepte ?
- `clue(word)` — definition d'un mot
- `byLength(len, kind)` — mots d'une longueur ("answers" ou "valid")
- `easyByLength(len)` — mots courants d'une longueur
- `courantOf(pool)` — moitie la plus frequente d'un pool donne
- `poolFor(difficulte, len, basePool)` — pool selon difficulte (facile/moyen/difficile)
- `pickByDifficulty(jeu, difficulte, len, basePool)` — tirage anti-repetition + difficulte
- `pickFresh(jeu, len)` / `markSeen` / `seenList` / `resetSeen(jeu)` — anti-repetition par jeu

## Systeme de difficulte

Le pool "courant" = la **moitie la plus frequente** du pool de CHAQUE jeu, limitee aux vrais
mots frequents (jamais bourre avec des mots rares ; peut donc etre < 50 % si peu de mots
frequents sont disponibles).

- **facile** -> pool courant uniquement
- **moyen** -> 50 % courant, 50 % pool complet
- **difficile** -> pool complet

Mapping niveaux -> difficulte : Motus (3 niveaux) = 0 facile / 1 moyen / 2 difficile.
Fleches & Meles (5 niveaux) = 0-1 facile, 2-3 moyen, 4 difficile.

## Anti-repetition

Historique **par jeu** via localStorage (`flc_seen_<jeu>_<langue>`). Recyclage automatique
des plus anciens quand le pool est epuise.

## Chiffres par jeu

**Francais**

| Jeu | Total (difficile) | Courant (facile) | Part |
|-----|------------------:|-----------------:|-----:|
| Motus (4-6 lettres)            | 16 055 | 8 027  | 50,0 % |
| Mots fleches (3-9, definis)    | 61 828 | 24 745 | 40,0 % |
| Mots meles (3-9 lettres)       | 61 828 | 24 745 | 40,0 % |

**Anglais**

| Jeu | Total (difficile) | Courant (facile) | Part |
|-----|------------------:|-----------------:|-----:|
| Motus (4-6 lettres)            | 18 762 | 9 381  | 50,0 % |
| Mots fleches (3-9, definis)    | 60 274 | 27 134 | 45,0 % |
| Mots meles (3-9 lettres)       | 60 274 | 27 134 | 45,0 % |

Mots acceptes a la saisie (`valid`) : FR ~79 600 / EN ~79 300.

## Ajouter un nouveau jeu (ex. Pendu)

1. Creer `Pendu/index.html`.
2. Charger le dictionnaire : `<script src="../Dictionnaires/dict_fr.js"></script>`.
3. Tirer les mots via `DICT.pickByDifficulty("pendu", difficulte, longueur)`.
4. L'anti-repetition fonctionne automatiquement avec la cle de jeu "pendu".
