-- SQLite schema for storing SillyTavern character cards (chara_card_v3)
-- including their world book (character_book), regex scripts, and
-- TavernHelper scripts / variables.
--
-- Design notes:
--   * One row per character in `characters`. The full original JSON is kept
--     in `characters.raw_json` for lossless round-tripping.
--   * Array/nested structures are normalised into child tables so they can be
--     queried directly, while sub-objects that have no fixed shape are stored
--     as JSON text columns.
--   * All child tables cascade-delete with their parent character so a card can
--     be re-imported cleanly.

PRAGMA foreign_keys = ON;

-- Core character record. Scalar fields prefer the v3 `data.*` block (the
-- authoritative location in chara_card_v3) and fall back to the legacy
-- top-level fields when absent.
CREATE TABLE IF NOT EXISTS characters (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    name                     TEXT NOT NULL,
    avatar                   TEXT,
    fav                      INTEGER,            -- 0/1
    create_date              TEXT,
    spec                     TEXT,               -- e.g. "chara_card_v3"
    spec_version             TEXT,               -- e.g. "3.0"

    -- Prompt / persona fields
    description              TEXT,
    personality              TEXT,
    scenario                 TEXT,
    first_mes                TEXT,
    mes_example              TEXT,
    system_prompt            TEXT,
    post_history_instructions TEXT,
    creatorcomment           TEXT,

    -- Authorship / metadata
    creator                  TEXT,
    creator_notes            TEXT,
    character_version        TEXT,
    tags                     TEXT,               -- JSON array
    talkativeness            REAL,

    -- Extensions: world binding + character-level depth prompt
    world_name               TEXT,
    depth_prompt             TEXT,
    depth_prompt_depth       INTEGER,
    depth_prompt_role        TEXT,

    -- TavernHelper free-form variable store (JSON)
    variables                TEXT,

    -- Lossless copy of the entire imported card
    raw_json                 TEXT NOT NULL,
    imported_at              TEXT NOT NULL DEFAULT (datetime('now')),

    UNIQUE (name, avatar)
);

-- alternate_greetings and group_only_greetings.
CREATE TABLE IF NOT EXISTS greetings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id  INTEGER NOT NULL,
    kind          TEXT NOT NULL,                 -- 'alternate' | 'group_only'
    idx           INTEGER NOT NULL,              -- position in the array
    content       TEXT,
    FOREIGN KEY (character_id) REFERENCES characters (id) ON DELETE CASCADE
);

-- World book (character_book) entries.
CREATE TABLE IF NOT EXISTS world_book_entries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id    INTEGER NOT NULL,
    book_name       TEXT,                        -- character_book.name
    entry_id        INTEGER,                     -- entry.id within the card
    display_order   INTEGER,                     -- index within entries[]
    comment         TEXT,                        -- human label / title
    keys            TEXT,                        -- JSON array of primary keys
    secondary_keys  TEXT,                        -- JSON array
    content         TEXT,
    enabled         INTEGER,                     -- 0/1
    constant        INTEGER,                     -- 0/1
    selective       INTEGER,                     -- 0/1
    use_regex       INTEGER,                     -- 0/1
    insertion_order INTEGER,
    position        TEXT,
    extensions      TEXT,                        -- JSON object
    FOREIGN KEY (character_id) REFERENCES characters (id) ON DELETE CASCADE
);

-- Regex scripts (data.extensions.regex_scripts).
CREATE TABLE IF NOT EXISTS regex_scripts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id     INTEGER NOT NULL,
    display_order    INTEGER,
    script_id        TEXT,
    script_name      TEXT,
    find_regex       TEXT,
    replace_string   TEXT,
    placement        TEXT,                       -- JSON array
    disabled         INTEGER,                    -- 0/1
    markdown_only    INTEGER,                    -- 0/1
    prompt_only      INTEGER,                    -- 0/1
    run_on_edit      INTEGER,                    -- 0/1
    substitute_regex INTEGER,
    min_depth        INTEGER,
    max_depth        INTEGER,
    trim_strings     TEXT,                       -- JSON array
    FOREIGN KEY (character_id) REFERENCES characters (id) ON DELETE CASCADE
);

-- TavernHelper scripts (data.extensions.tavern_helper.scripts).
CREATE TABLE IF NOT EXISTS helper_scripts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id  INTEGER NOT NULL,
    display_order INTEGER,
    script_id     TEXT,
    name          TEXT,
    type          TEXT,
    enabled       INTEGER,                       -- 0/1
    content       TEXT,
    info          TEXT,
    button        TEXT,                          -- JSON object
    data          TEXT,                          -- JSON object
    export_with   TEXT,                          -- JSON
    FOREIGN KEY (character_id) REFERENCES characters (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_greetings_char    ON greetings (character_id);
CREATE INDEX IF NOT EXISTS idx_wbe_char           ON world_book_entries (character_id);
CREATE INDEX IF NOT EXISTS idx_regex_char         ON regex_scripts (character_id);
CREATE INDEX IF NOT EXISTS idx_helper_char        ON helper_scripts (character_id);
