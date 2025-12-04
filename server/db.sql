-- DROP TABLE IF EXISTS quickpark.entries;
-- DROP DATABASE IF EXISTS quickpark;
--
-- Creation:
--
CREATE DATABASE IF NOT EXISTS quickpark;
USE quickpark;
-- CREATE TABLE IF NOT EXISTS frontries(
--     tstamp BIGINT PRIMARY KEY,
--     plate VARCHAR(32)
-- );
-- CREATE TABLE IF NOT EXISTS pass1(
--     tstamp BIGINT PRIMARY KEY,
--     plate VARCHAR(32)
-- );
-- CREATE TABLE IF NOT EXISTS pass2(
--     tstamp BIGINT PRIMARY KEY,
--     plate VARCHAR(32)
-- );
CREATE TABLE IF NOT EXISTS entries(tstamp BIGINT PRIMARY KEY, plate TEXT);
--
-- Manual viewing...:
--
DESCRIBE entries;
SELECT *
FROM entries;
SELECT *
FROM entries
WHERE plate IS NOT NULL;