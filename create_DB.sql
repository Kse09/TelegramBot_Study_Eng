CREATE TABLE IF NOT EXISTS words (
    id SERIAL PRIMARY KEY,
    english TEXT NOT NULL,
    russian TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tg_users (
    id SERIAL PRIMARY KEY,
    tg_user_id  BIGINT UNIQUE NOT NULL,
    user_name TEXT
);

CREATE TABLE IF NOT EXISTS user_words (
    id SERIAL PRIMARY KEY,
    user_id  INTEGER REFERENCES tg_users(id),
    eng_word TEXT,
    rus_word TEXT
);

