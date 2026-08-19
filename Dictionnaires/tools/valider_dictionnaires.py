#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validation et nettoyage des dictionnaires de jeu (dict_fr.js / dict_en.js).

Pourquoi : les pools ont ete generes en supprimant accents, traits d'union,
apostrophes et espaces. Des locutions se sont retrouvees collees en un seul
"mot" inexistant (mort-ne -> MORTNE, c'est ca -> CESTCA, ice cream -> ICECREAM),
la ligature "oe" a ete effacee au lieu d'etre transcrite (coeur -> CUR,
oeuvre -> UVRE) et un gros bloc de mots inventes a ete ajoute en fin de liste.

Regle appliquee : un mot n'est conserve que s'il figure, en tant que mot
simple (sans trait d'union, apostrophe ni espace), dans au moins un lexique
de reference. Les formes mutilees par la ligature "oe" sont retablies quand
la bonne graphie manque au pool.

Usage :  python3 Dictionnaires/tools/valider_dictionnaires.py [--check]

  --check  n'ecrit rien, affiche seulement le rapport.

Les lexiques de reference sont telecharges puis mis en cache dans
Dictionnaires/tools/.cache/ (non versionne).
"""

import argparse
import json
import os
import re
import sys
import unicodedata
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.cache')

MINLEN, MAXLEN = 3, 9          # longueurs jouables annoncees par les pools

# Lexiques de reference. Le dictionnaire Hunspell est deplie avec ses regles
# d'affixes : c'est lui qui fournit l'essentiel des formes flechies.
SOURCES = {
    'fr': [
        ('hunspell.dic', 'https://raw.githubusercontent.com/wooorm/dictionaries/main/dictionaries/fr/index.dic'),
        ('hunspell.aff', 'https://raw.githubusercontent.com/wooorm/dictionaries/main/dictionaries/fr/index.aff'),
        ('frwords.json', 'https://raw.githubusercontent.com/words/an-array-of-french-words/master/index.json'),
        ('frforms.csv', 'https://raw.githubusercontent.com/hbenbel/French-Dictionary/master/dictionary/dictionary.csv'),
    ],
    'en': [
        ('enwords.txt', 'https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt'),
        ('enwords.json', 'https://raw.githubusercontent.com/words/an-array-of-english-words/master/index.json'),
        ('en.dic', 'https://raw.githubusercontent.com/wooorm/dictionaries/main/dictionaries/en/index.dic'),
    ],
}


def fetch(name, url):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name)
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        sys.stderr.write('telechargement %s ...\n' % name)
        urllib.request.urlretrieve(url, path)
    return path


def norm(word):
    """Graphie du jeu : majuscules ASCII, sans accent, ligatures developpees."""
    word = (word.replace('œ', 'oe').replace('Œ', 'OE')
                .replace('æ', 'ae').replace('Æ', 'AE'))
    word = unicodedata.normalize('NFD', word)
    return ''.join(c for c in word if unicodedata.category(c) != 'Mn').upper()


def read_lines(path):
    with open(path, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            yield line.strip()


# --------------------------------------------------------------------------
# Depliage Hunspell (FLAG long : drapeaux de 2 caracteres)
# --------------------------------------------------------------------------
def parse_aff(path):
    pfx, sfx = {}, {}
    lines = list(read_lines(path))
    i = 0
    while i < len(lines):
        parts = lines[i].split()
        if len(parts) >= 4 and parts[0] in ('PFX', 'SFX') and parts[2] in ('Y', 'N'):
            kind, flag, cross, count = parts[0], parts[1], parts[2] == 'Y', int(parts[3])
            rules = []
            for j in range(1, count + 1):
                r = lines[i + j].split()
                strip = '' if r[2] == '0' else r[2]
                affix = r[3].split('/')[0]          # l'affixe peut porter ses propres drapeaux
                affix = '' if affix == '0' else affix
                cond = r[4] if len(r) > 4 else '.'
                rules.append((strip, affix, cond))
            table = pfx if kind == 'PFX' else sfx
            table.setdefault(flag, [cross, []])[1].extend(rules)
            i += count + 1
        else:
            i += 1
    return pfx, sfx


def expand_hunspell(dic_path, aff_path):
    pfx, sfx = parse_aff(aff_path)

    def add_suffix(word, strip, affix, cond):
        if strip and not word.endswith(strip):
            return None
        if cond != '.' and not re.search(cond + '$', word):
            return None
        return (word[:len(word) - len(strip)] if strip else word) + affix

    def add_prefix(word, strip, affix, cond):
        if strip and not word.startswith(strip):
            return None
        if cond != '.' and not re.match('^' + cond, word):
            return None
        return affix + (word[len(strip):] if strip else word)

    forms = set()
    for line in read_lines(dic_path):
        if not line:
            continue
        word, _, flagstr = line.partition('/')
        flagstr = flagstr.split()[0] if flagstr else ''
        if not word:
            continue
        flags = [flagstr[k:k + 2] for k in range(0, len(flagstr) - 1, 2)]
        if '()' not in flags:          # NEEDAFFIX : la forme nue n'existe pas
            forms.add(word)
        suffixed = []
        for flag in flags:
            for rule in sfx.get(flag, (False, []))[1]:
                out = add_suffix(word, *rule)
                if out:
                    suffixed.append((out, sfx[flag][0]))
                    forms.add(out)
        for flag in flags:
            if flag not in pfx:
                continue
            cross, rules = pfx[flag]
            for rule in rules:
                out = add_prefix(word, *rule)
                if out:
                    forms.add(out)
                if cross:
                    for stem, stem_cross in suffixed:
                        if stem_cross:
                            out2 = add_prefix(stem, *rule)
                            if out2:
                                forms.add(out2)
    return forms


# --------------------------------------------------------------------------
# Lexiques de reference
# --------------------------------------------------------------------------
def build_reference(lang):
    """-> (mots simples, {forme collee: graphie d'origine}, {forme sans oe: bonne forme})"""
    paths = {name: fetch(name, url) for name, url in SOURCES[lang]}
    words = []
    if lang == 'fr':
        words.append(expand_hunspell(paths['hunspell.dic'], paths['hunspell.aff']))
        with open(paths['frwords.json'], encoding='utf-8') as fh:
            words.append(json.load(fh))
        words.append(list(read_lines(paths['frforms.csv'])))
    else:
        words.append(list(read_lines(paths['enwords.txt'])))
        with open(paths['enwords.json'], encoding='utf-8') as fh:
            words.append(json.load(fh))
        words.append([l.split('/')[0] for l in read_lines(paths['en.dic'])])

    simple, glued, ligature = set(), {}, {}
    for group in words:
        for raw in group:
            raw = raw.strip()
            if not raw:
                continue
            n = norm(raw)
            if re.fullmatch(r'[A-Z]+', n):
                simple.add(n)
            elif re.fullmatch(r"[A-Z][A-Z' \-]*", n):   # locution, mot compose, elision
                key = re.sub(r'[^A-Z]', '', n)
                if key and key not in glued:
                    glued[key] = raw
            if 'œ' in raw or 'Œ' in raw:
                # graphie mutilee : la ligature avait ete effacee, pas transcrite
                mangled = norm(re.sub('[œŒ]', '', raw))
                if re.fullmatch(r'[A-Z]+', mangled) and mangled != n:
                    ligature.setdefault(mangled, n)
    return simple, glued, ligature


# --------------------------------------------------------------------------
# Lecture / ecriture des dictionnaires du jeu
# --------------------------------------------------------------------------
def load_dict(path):
    with open(path, encoding='utf-8') as fh:
        src = fh.read()
    pools = {}
    for key in ('stop', 'easy', 'answers'):
        m = re.search(r'\n  %s: (\[.*?\]),?\n' % key, src, re.S)
        pools[key] = json.loads(m.group(1))
    return src, pools


def dump_array(words):
    return json.dumps(words, ensure_ascii=False, separators=(',', ':'))


def save_dict(path, src, pools):
    for key in ('easy', 'answers'):
        src = re.sub(r'(\n  %s: )\[.*?\](,?\n)' % key,
                     lambda m: m.group(1) + dump_array(pools[key]) + m.group(2),
                     src, count=1, flags=re.S)
    src = re.sub(r'\n   \d+ mots jouables\n',
                 '\n   %d mots jouables\n' % len(pools['answers']), src, count=1)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(src)


def save_easy_txt(path, words, lang):
    by_len = {}
    for w in words:                      # l'ordre du pool = ordre de frequence
        by_len.setdefault(len(w), []).append(w)
    label = 'FR' if lang == 'fr' else 'EN'
    out = ['# Liste des mots COURANTS %s (pool facile) — %d mots' % (label, len(words)),
           '# Mots frequents, pleins (hors mots-outils), ordonnes par frequence dans chaque longueur',
           '# Verbes exclusivement a l\'infinitif (formes conjuguees supprimees)']
    for length in sorted(by_len):
        out.append('')
        out.append('## %d lettres (%d mots)' % (length, len(by_len[length])))
        out.append(', '.join(by_len[length]))
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(out) + '\n')


# --------------------------------------------------------------------------
def clean(lang, check_only):
    js_path = os.path.join(ROOT, 'dict_%s.js' % lang)
    txt_path = os.path.join(ROOT, 'mots_faciles_%s.txt' % lang)
    src, pools = load_dict(js_path)
    simple, glued, ligature = build_reference(lang)

    stats = {'glued': [], 'ligature': [], 'unknown': [], 'repaired': []}
    known = set(pools['answers'])

    def keep(word):
        if word in simple:
            return word
        if word in ligature:                 # CUR -> COEUR, UVRE -> OEUVRE
            fixed = ligature[word]
            stats['ligature'].append((word, fixed))
            # le pool est contractuellement limite a 3-9 lettres : retablir la
            # ligature rallonge le mot de deux lettres et peut l'en faire sortir
            if fixed in simple and fixed not in known and MINLEN <= len(fixed) <= MAXLEN:
                stats['repaired'].append((word, fixed))
                known.add(fixed)
                return fixed
            return None
        if word in glued:
            stats['glued'].append((word, glued[word]))
        else:
            stats['unknown'].append(word)
        return None

    cleaned = {}
    for key in ('answers', 'easy'):
        out, seen = [], set()
        for word in pools[key]:
            fixed = keep(word)
            if fixed and fixed not in seen:
                seen.add(fixed)
                out.append(fixed)
        cleaned[key] = out

    # easy doit rester un sous-ensemble de answers
    answers_set = set(cleaned['answers'])
    cleaned['easy'] = [w for w in cleaned['easy'] if w in answers_set]

    print('--- %s ---' % lang.upper())
    for key in ('answers', 'easy'):
        before, after = len(pools[key]), len(cleaned[key])
        print('  %-8s %6d -> %6d  (%d retires, %.1f%%)'
              % (key, before, after, before - after, 100.0 * (before - after) / before))
    print('  dont locutions collees : %d   ligature oe mutilee : %d (%d graphies retablies)   inconnus : %d'
          % (len(stats['glued']), len(stats['ligature']), len(stats['repaired']), len(stats['unknown'])))
    for length in range(3, 10):
        n = sum(1 for w in cleaned['answers'] if len(w) == length)
        e = sum(1 for w in cleaned['easy'] if len(w) == length)
        print('    %d lettres : %5d jouables / %4d courants' % (length, n, e))

    if not check_only:
        pools.update(cleaned)
        save_dict(js_path, src, pools)
        save_easy_txt(txt_path, cleaned['easy'], lang)
        print('  ecrit : %s, %s' % (os.path.basename(js_path), os.path.basename(txt_path)))
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true', help='rapport seul, aucune ecriture')
    ap.add_argument('--lang', default='fr,en')
    args = ap.parse_args()
    for lang in args.lang.split(','):
        clean(lang.strip(), args.check)


if __name__ == '__main__':
    main()
