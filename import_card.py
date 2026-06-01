#!/usr/bin/env python3
"""Import a SillyTavern character card (chara_card_v3) into a SQLite database.

Stores the complete card: persona fields, world book (character_book) entries,
regex scripts, and TavernHelper scripts/variables. The whole original JSON is
also kept verbatim in `characters.raw_json` for lossless recovery.

Usage:
    python3 import_card.py <card.json> [--db tavern_cards.db] [--schema schema.sql]

Re-importing the same card (matched by name + avatar) replaces the previous
copy rather than duplicating it.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys


def as_bool_int(value):
    """Coerce a truthy/None value into 0/1/None for SQLite storage."""
    if value is None:
        return None
    return 1 if value else 0


def as_json(value):
    """Serialise nested structures to JSON text, leaving None as NULL."""
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def pick(*values):
    """Return the first value that is not None and not an empty string."""
    for v in values:
        if v is not None and v != "":
            return v
    return None


def load_card(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def init_db(conn, schema_path):
    with open(schema_path, "r", encoding="utf-8") as fh:
        conn.executescript(fh.read())


def import_card(conn, card, raw_text):
    data = card.get("data") or {}
    ext = data.get("extensions") or {}
    depth = ext.get("depth_prompt") or {}
    tavern_helper = ext.get("tavern_helper") or {}

    name = pick(data.get("name"), card.get("name")) or "Unknown"
    avatar = card.get("avatar")

    # Replace any previous import of this card (cascades to children).
    conn.execute(
        "DELETE FROM characters WHERE name = ? AND avatar IS ?",
        (name, avatar),
    )

    cur = conn.execute(
        """
        INSERT INTO characters (
            name, avatar, fav, create_date, spec, spec_version,
            description, personality, scenario, first_mes, mes_example,
            system_prompt, post_history_instructions, creatorcomment,
            creator, creator_notes, character_version, tags, talkativeness,
            world_name, depth_prompt, depth_prompt_depth, depth_prompt_role,
            variables, raw_json
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            name,
            avatar,
            as_bool_int(pick(data.get("fav"), ext.get("fav"), card.get("fav"))),
            card.get("create_date"),
            card.get("spec"),
            card.get("spec_version"),
            pick(data.get("description"), card.get("description")),
            pick(data.get("personality"), card.get("personality")),
            pick(data.get("scenario"), card.get("scenario")),
            pick(data.get("first_mes"), card.get("first_mes")),
            pick(data.get("mes_example"), card.get("mes_example")),
            data.get("system_prompt"),
            data.get("post_history_instructions"),
            card.get("creatorcomment"),
            data.get("creator"),
            data.get("creator_notes"),
            data.get("character_version"),
            as_json(pick(data.get("tags"), card.get("tags"))),
            pick(ext.get("talkativeness"), card.get("talkativeness")),
            ext.get("world"),
            depth.get("prompt"),
            depth.get("depth"),
            depth.get("role"),
            as_json(tavern_helper.get("variables")),
            raw_text,
        ),
    )
    character_id = cur.lastrowid

    _import_greetings(conn, character_id, data)
    n_wb = _import_world_book(conn, character_id, data.get("character_book") or {})
    n_regex = _import_regex_scripts(conn, character_id, ext.get("regex_scripts") or [])
    n_helper = _import_helper_scripts(conn, character_id, tavern_helper.get("scripts") or [])

    return {
        "character_id": character_id,
        "name": name,
        "world_book_entries": n_wb,
        "regex_scripts": n_regex,
        "helper_scripts": n_helper,
    }


def _import_greetings(conn, character_id, data):
    rows = []
    for idx, content in enumerate(data.get("alternate_greetings") or []):
        rows.append((character_id, "alternate", idx, content))
    for idx, content in enumerate(data.get("group_only_greetings") or []):
        rows.append((character_id, "group_only", idx, content))
    conn.executemany(
        "INSERT INTO greetings (character_id, kind, idx, content) VALUES (?,?,?,?)",
        rows,
    )


def _import_world_book(conn, character_id, book):
    book_name = book.get("name")
    entries = book.get("entries") or []
    rows = []
    for order, entry in enumerate(entries):
        rows.append((
            character_id,
            book_name,
            entry.get("id"),
            order,
            entry.get("comment"),
            as_json(entry.get("keys")),
            as_json(entry.get("secondary_keys")),
            entry.get("content"),
            as_bool_int(entry.get("enabled")),
            as_bool_int(entry.get("constant")),
            as_bool_int(entry.get("selective")),
            as_bool_int(entry.get("use_regex")),
            entry.get("insertion_order"),
            str(entry.get("position")) if entry.get("position") is not None else None,
            as_json(entry.get("extensions")),
        ))
    conn.executemany(
        """
        INSERT INTO world_book_entries (
            character_id, book_name, entry_id, display_order, comment,
            keys, secondary_keys, content, enabled, constant, selective,
            use_regex, insertion_order, position, extensions
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        rows,
    )
    return len(rows)


def _import_regex_scripts(conn, character_id, scripts):
    rows = []
    for order, s in enumerate(scripts):
        rows.append((
            character_id,
            order,
            s.get("id"),
            s.get("scriptName"),
            s.get("findRegex"),
            s.get("replaceString"),
            as_json(s.get("placement")),
            as_bool_int(s.get("disabled")),
            as_bool_int(s.get("markdownOnly")),
            as_bool_int(s.get("promptOnly")),
            as_bool_int(s.get("runOnEdit")),
            as_bool_int(s.get("substituteRegex")),
            s.get("minDepth"),
            s.get("maxDepth"),
            as_json(s.get("trimStrings")),
        ))
    conn.executemany(
        """
        INSERT INTO regex_scripts (
            character_id, display_order, script_id, script_name, find_regex,
            replace_string, placement, disabled, markdown_only, prompt_only,
            run_on_edit, substitute_regex, min_depth, max_depth, trim_strings
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        rows,
    )
    return len(rows)


def _import_helper_scripts(conn, character_id, scripts):
    rows = []
    for order, s in enumerate(scripts):
        rows.append((
            character_id,
            order,
            s.get("id"),
            s.get("name"),
            s.get("type"),
            as_bool_int(s.get("enabled")),
            s.get("content"),
            s.get("info"),
            as_json(s.get("button")),
            as_json(s.get("data")),
            as_json(s.get("export_with")),
        ))
    conn.executemany(
        """
        INSERT INTO helper_scripts (
            character_id, display_order, script_id, name, type, enabled,
            content, info, button, data, export_with
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """,
        rows,
    )
    return len(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Import a tavern card JSON into SQLite.")
    parser.add_argument("card", help="Path to the character card JSON file.")
    parser.add_argument("--db", default="tavern_cards.db", help="SQLite database path.")
    parser.add_argument(
        "--schema",
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql"),
        help="Path to the schema.sql file.",
    )
    args = parser.parse_args(argv)

    with open(args.card, "r", encoding="utf-8") as fh:
        raw_text = fh.read()
    card = json.loads(raw_text)

    conn = sqlite3.connect(args.db)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        init_db(conn, args.schema)
        result = import_card(conn, card, raw_text)
        conn.commit()
    finally:
        conn.close()

    print(f"Imported '{result['name']}' (character id {result['character_id']}) into {args.db}")
    print(f"  world book entries : {result['world_book_entries']}")
    print(f"  regex scripts      : {result['regex_scripts']}")
    print(f"  helper scripts     : {result['helper_scripts']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
