# Tavern Card Database

Stores SillyTavern character cards (`chara_card_v3`) in a SQLite database,
including the **world book** (`character_book`), **regex scripts**, and
**TavernHelper scripts / variables** — not just the basic persona fields.

## Contents

| File | Purpose |
| --- | --- |
| `schema.sql` | SQLite schema (characters + child tables) |
| `import_card.py` | Parses a card JSON and imports it into the database |
| `MVU_PRINCIPLE.md` | Technical explanation of the MVU (MagVarUpdate) framework |
| `tavern_cards.db` | The populated SQLite database |

## Usage

```bash
python3 import_card.py path/to/card.json --db tavern_cards.db
```

Re-importing the same card (matched by `name` + `avatar`) replaces the previous
copy instead of duplicating it. The schema is created automatically on first run.

## Schema overview

- **characters** — one row per card: persona fields (`description`,
  `personality`, `scenario`, `first_mes`, `mes_example`, `system_prompt`,
  `post_history_instructions`), metadata (`creator`, `tags`, `world_name`,
  depth prompt), the TavernHelper `variables` blob, and the complete original
  JSON in `raw_json` for lossless recovery.
- **greetings** — `alternate_greetings` and `group_only_greetings`.
- **world_book_entries** — every `character_book` entry: `keys`,
  `secondary_keys`, `content`, `position`, flags (`enabled`, `constant`,
  `selective`, `use_regex`), and the full `extensions` object as JSON.
- **regex_scripts** — `findRegex`, `replaceString`, `placement`, and flags.
- **helper_scripts** — TavernHelper scripts: `name`, `type`, `content`,
  `button`, `data`, etc.

All child tables cascade-delete with their parent character.

## Imported card

The database currently holds **秦璐** (`chara_card_v3`, spec 3.0):

- 15 world book entries
- 5 regex scripts
- 5 TavernHelper scripts

## Querying examples

```bash
# List world book entries
python3 -c "import sqlite3; [print(r) for r in sqlite3.connect('tavern_cards.db').execute('SELECT display_order, comment FROM world_book_entries ORDER BY display_order')]"

# Dump a helper script's content
python3 -c "import sqlite3; print(sqlite3.connect('tavern_cards.db').execute('SELECT content FROM helper_scripts WHERE name=?', ('游戏逻辑',)).fetchone()[0])"
```
