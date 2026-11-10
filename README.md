# pyvision

Testeur pour les modules Python de 42 (parcours 00, 01, 02, 03, 04, 05bis,
06bis, 09, 10) qui vérifie **vraiment** le respect du sujet : structure,
style, analyse du code (`ast`), prompts exacts, sorties ligne à ligne,
comportement des fonctions et classes appelées directement, robustesse.

## Installation

```sh
./install.sh
```

Installe flake8, mypy, rich, pydantic et python-dotenv dans un venv isolé
(`.venv/`, compatible Python « externally managed ») et crée la commande
`~/.local/bin/pyvision` (le `PATH` est complété si besoin).

## Utilisation

Placez-vous à la racine d'un module (le dossier qui contient `ex0/`,
`ex1/`, ... ou, pour 05bis/06bis, les fichiers à la racine) :

```sh
pyvision            # détecte le module et teste tout
pyvision ex2        # un seul exercice (ou: pyvision 2)
pyvision -m 05bis   # forcer le module
pyvision -v         # détail de chaque vérification réussie
pyvision -u         # mise à jour (git pull + réinstallation)
```

Chaque exercice est noté **OK** (vert), **KO** (rouge) ou
**AVERTISSEMENT** (jaune), puis un rapport détaille chaque problème :
sortie attendue / obtenue et phrase du sujet concernée.

Pas de KO en cascade : quand une cause principale explique les erreurs
suivantes (ex : `input()` jamais appelé, programme qui plante), un seul KO
est affiché pour le fichier ; les comparaisons de sortie qui en découlent
sont listées dans ce même bloc (détail attendu / obtenu avec `-v`).

## Règles suivies

- Un **KO** s'appuie toujours sur une phrase du PDF (citée dans le rapport).
- Quand le sujet autorise une sortie libre (« no strict output check »,
  « the way you want », messages personnalisables...), une différence de
  forme donne seulement un **AVERTISSEMENT**.
- Ce qui demande Internet (pip/Poetry réels du 05bis) donne un
  **AVERTISSEMENT** avec la marche à suivre à la main.

## Sécurité et propreté

- Vos fichiers ne sont jamais modifiés : tout s'exécute dans une copie
  temporaire, avec `python3 -I`, un délai maximum, une limite de mémoire et
  de taille de sortie (boucle ou récursion infinie = KO propre).
- `input()` est remplacé par une fonction qui enregistre le prompt ;
  stdin, `sys.argv` et les fichiers de test sont préparés automatiquement.
- Les dossiers temporaires et les `__pycache__` créés pendant le test sont
  supprimés. Seul un cache mypy est conservé dans `~/.cache/pyvision/`
  (accélère les lancements suivants).

## Développement

- `core/` : base commune (exécution isolée, harness, analyse `ast`,
  comparaison, rapport).
- `modules/module_XX.py` : un fichier par module. **Ajouter un module =
  ajouter un fichier** définissant `MODULE` (détecté automatiquement).
- `tests/module_XX/good/` : rendu correct ; `tests/module_XX/bad_*/` :
  erreurs réalistes (fichiers remplaçant ceux de `good/` + `expect.json`).

```sh
.venv/bin/python tests/run_tests.py            # tous les jeux de test
.venv/bin/python tests/run_tests.py module_01  # un module
```

Voir `PROGRESS.md` pour le détail des points vérifiés.
