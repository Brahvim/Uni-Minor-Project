-- DROP DATABASE IF EXISTS quickpark;
--
-- Creation:
--
CREATE DATABASE IF NOT EXISTS quickpark;
USE quickpark;
CREATE TABLE IF NOT EXISTS entries(
    tstamp DOUBLE PRIMARY KEY,
    plate VARCHAR(32)
);
--
-- Manual viewing...:
--
DESCRIBE entries;
SELECT *
FROM entries;
SELECT *
FROM entries
WHERE plate IS NOT NULL;