CREATE TABLE race (
    id integer primary key autoincrement,
    description text,
    start_time text,
    end_time text
);

CREATE TABLE category (
    id integer primary key autoincrement,
    short_name text,
    description  text,
    total_laps integer,
    race_id integer
);

CREATE TABLE racer (
    id integer primary key autoincrement,
    'number' integer,
    name text,
    category_id integer,
    race_id integer
);

CREATE TABLE racer_lap (
    id integer primary key autoincrement,
    event_time text,
    race_id integer,
    racer_id integer
);
