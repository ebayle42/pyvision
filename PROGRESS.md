# PROGRESS — pyvision

Fichier de suivi pour reprendre le travail dans une nouvelle session.

## Architecture

- `pyvision.py` : CLI (détection du module, options, rapport).
- `core/harness.py` : exécuté dans le sous-processus (`python -I -B`) ; faux
  `input()` qui enregistre les prompts, stdin avec écho, sondes (`load`,
  `capture`, `run_main(record=True)` qui enregistre les instances créées).
- `core/runner.py` : bac à sable (copie du rendu dans un dossier temporaire),
  timeout, limites mémoire/taille de sortie, flake8/mypy.
- `core/base.py` : `Exercise`, `Module`, `Ctx` + vérifications génériques
  (fichiers, fichiers en trop, flake8, type hints, mypy, fonctions et imports
  autorisés, bloc `__main__`).
- `core/analysis.py` : helpers `ast`. `core/compare.py` : diff ligne à ligne.
- `modules/module_XX.py` : un fichier par module, variable `MODULE`.
- `tests/run_tests.py` : jeux de test (`good/` + cas fautifs avec
  `expect.json`). Lancer : `.venv/bin/python tests/run_tests.py [module_XX]`.

## État des modules

| Module | État | Jeux de test |
|--------|------|--------------|
| 00 | terminé | 15/15 |
| 01 | terminé | 16/16 |
| 02 | terminé | 10/10 |
| 03 | terminé | 10/10 |
| 04 | terminé | 9/9 |
| 05bis | terminé | 13/13 |
| 06bis | terminé | 9/9 |
| 09 | terminé | 5/5 |
| 10 | terminé | 6/6 |

## Points vérifiés

### Module 00
- Fichiers/fonctions exacts, une seule fonction par fichier (ex6 : helpers
  autorisés pour la récursion), aucun import, pas de `__main__` ni de code
  hors fonction.
- Prompts comparés caractère par caractère, `input()` réellement appelé,
  sorties comparées ligne à ligne avec les exemples ET d'autres valeurs
  (détection des sorties en dur), cas limites (60 jours, 2 jours).
- ex6 : version itérative avec boucle, version récursive réellement
  récursive. ex7 : signature exacte, type hints + mypy obligatoires.
- Type hints / mypy ex0-6 : AVERTISSEMENT seulement (recommandés).

### Module 01
- Sorties comparées à l'exemple en AVERTISSEMENT (ex0 « no strict output
  check », ex2 « the way you want », données libres ailleurs).
- KO : classes/méthodes demandées (vraies méthodes, pas d'attribut qui les
  écrase), calcul en dur entre constantes, grow()/age() qui modifient la
  plante, ≥3 / ≥5 plantes, constructeur (name, height, age), attributs
  protégés `_x` (ni publics, ni `__x`), setters qui refusent les négatifs
  sans modifier la valeur et avec le nom de la plante dans le message,
  constructeur qui refuse une valeur négative, `super()` dans les
  sous-classes, `show()` redéfinie, noms/narration écrits en dur dans les
  méthodes (test en renommant la plante), valeur nutritionnelle 0 puis
  croissante, staticmethod/classmethod testées, classe imbriquée de stats
  (attributs protégés + affichage), compteurs mis à jour, fonction hors
  classe.

### Module 02
- try/except obligatoire, programme qui ne plante jamais, sorties comparées
  strictement (exemples déterministes).
- Appels directs : input_temperature (bornes 0 et 40 incluses, messages
  avec d'autres valeurs), garden_operations(0..3) lève la bonne exception,
  4+ ne lève rien, `except (A, B)` présent, type() interdit, exceptions
  personnalisées (héritage, message par défaut, message fourni),
  water_plant lève PlantError, try/except/finally dans
  test_watering_system. Erreur mypy volontaire de l'ex2 acceptée.
- super() non listé dans « Authorized » : AVERTISSEMENT seulement.

### Module 03
- Sorties comparées (ex0 strict, ex1 « mimic » → avertissement), ex2 prompt
  exact + nouvelle tentative + tuple renvoyé, autres valeurs pour détecter
  le code en dur, ex3 ensembles recalculés à partir des lignes Player,
  ex4 inventaire vérifié avec d'autres paramètres (doublons, erreurs,
  pourcentages, égalité → premier), ex5 générateurs (yield, infini,
  consume_event vide la liste, utilisé dans un for), 1000 événements,
  ex6 compréhensions (≥2 list, ≥2 dict) et valeurs recalculées.
- open() interdit (pas d'I/O fichier) ; dict/set avant leur exercice :
  avertissement.

### Module 04
- with interdit avant l'ex3 ; usage sans argument, fichier inexistant,
  inaccessible (chmod 000), dossier : pas de plantage + message ; contenu
  affiché tel quel ; ex1/ex2 : fichier créé/remplacé avec « # » en fin de
  ligne, réponse vide = rien créé, dossier protégé ; ex2 : input() interdit,
  lecture sur sys.stdin, erreurs sur stderr avec préfixe ; ex3 :
  secure_archive avec with, retour (bool, str) dans tous les cas, action
  d'écriture détectée automatiquement.
- Messages personnalisables (« essential information is preserved ») :
  différences de format = avertissement.

### Module 05bis
- sys.path jamais modifié, eval/exec interdits, imports déclarés.
- ex0 : construct.py lancé hors venv (Python système) et dans un venv créé
  par pyvision (`venv --without-pip`, VIRTUAL_ENV positionné) → sorties
  différentes, instructions venv/activate ; loading.py sans bibliothèques
  (ne plante pas, commandes pip ET Poetry) puis avec de faux paquets
  pandas/numpy installés localement (versions affichées) ;
  requirements.txt et pyproject.toml (TOML valide, mêmes dépendances) ;
  venv commité → KO (via `git ls-files`).
- ex1 : python-dotenv dans requirements.txt, `.env` ignoré par .gitignore,
  `.env.example` complet, `.env` commité → KO ; oracle.py lancé depuis la
  racine : `.env` chargé, dev ≠ prod, variables d'environnement prioritaires.
- ex2-4 : valeurs exactes des fonctions, `alchemy` expose create_air mais
  pas create_earth, forme des imports imposée (import / from ... import /
  absolu + relatif), potions appellent les create_*, grimoire light
  importable dans les deux ordres, grimoire dark → ImportError circulaire,
  imports mutuels en haut des fichiers dark, validation insensible à la
  casse, ft_kaboom_1 explose. Erreur mypy volontaire de ft_alembic_1
  acceptée.

### Module 06bis
- ABC + @abstractmethod, signatures exactes (validate/ingest/output,
  register_processor/process_stream/print_processors_stats,
  output_pipeline, process_output), ingest typé selon les types acceptés.
- Tests directs : validate, exception sans validation, FIFO + rangs,
  conversion en chaînes, routage polymorphe (pas d'isinstance sur les
  classes concrètes), statistiques, export CSV exact et JSON valide
  (json.loads), ExportPlugin hérite de Protocol.
- ex3/ex4 : rôles détectés par structure (noms libres) ; capacité qui
  n'hérite pas de Creature ; package ex3 n'expose que les fabriques ;
  transform/revert changent attack ; stratégies avec isinstance sur la
  capacité, exception dédiée ; sorties en AVERTISSEMENT (noms libres).

### Module 09
- Pydantic 2 (pas de @validator/@root_validator), BaseModel, Field,
  @model_validator(mode='after'), enums ; chaque contrainte testée à ses
  bornes (valide/invalide → ValidationError), valeurs par défaut, types
  datetime, règles métier (AC, physical vérifié, télépathie ≥3 témoins,
  signal > 7 avec message, M..., commandant/capitaine, 50% expérimentés,
  équipage actif, modèles imbriqués).

### Module 10
- Callable depuis collections.abc, pas de global, pas d'open, imports
  functools/operator seulement où autorisés.
- ex0 : sorted/filter/map/max/min avec lambda, pas de def imbriqué,
  valeurs. ex1-2 : fonctions d'ordre supérieur et closures testées
  (compteurs et coffres indépendants). ex3 : reduce + operator, partial
  (power=50), lru_cache (cache_info, fib(300) rapide), singledispatch.
  ex4 : wraps (nom conservé), messages du timer, power_validator, retry
  (3 appels, message final), staticmethod, cast_spell décorée.

## Points impossibles à automatiser (AVERTISSEMENT ou non testés)
- Module 05bis ex0 : installation réelle avec pip / Poetry (réseau).
- Module 05bis : si le dossier n'est pas un dépôt git, la présence d'un
  `.env` / venv non commité ne peut pas être vérifiée (AVERTISSEMENT).
- Module 01 ex0 : shebang (demandé en live pendant l'évaluation).
- Explications orales demandées par les sujets.
