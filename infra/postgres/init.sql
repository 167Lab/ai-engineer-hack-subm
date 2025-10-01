-- Инициализация PostgreSQL для проекта Moscow2025

-- Создание дополнительной базы данных для ETL данных
CREATE DATABASE etl_data;

-- Подключение к базе данных etl_data
\c etl_data;

-- Создание схемы для обработанных данных
CREATE SCHEMA IF NOT EXISTS processed;

-- Создание таблицы для примера данных
CREATE TABLE IF NOT EXISTS processed.sample_data (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255),
    age INTEGER,
    city VARCHAR(100),
    salary INTEGER,
    department VARCHAR(100),
    join_date DATE,
    is_active BOOLEAN,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание индексов
CREATE INDEX IF NOT EXISTS idx_sample_data_city ON processed.sample_data(city);
CREATE INDEX IF NOT EXISTS idx_sample_data_department ON processed.sample_data(department);
CREATE INDEX IF NOT EXISTS idx_sample_data_join_date ON processed.sample_data(join_date);

-- Создание пользователя для ETL процессов
CREATE USER etl_user WITH PASSWORD 'etl_password';
GRANT ALL PRIVILEGES ON DATABASE etl_data TO etl_user;
GRANT ALL PRIVILEGES ON SCHEMA processed TO etl_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA processed TO etl_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA processed TO etl_user;

-- Логирование
SELECT 'PostgreSQL инициализация для Moscow2025 ETL завершена успешно' AS status;
