-- Users Table
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    full_name VARCHAR(50) NOT NULL,
    password VARCHAR(50) NOT NULL,
    total_hours INT DEFAULT 0
);

-- Entries Table
CREATE TABLE entries (
    entry_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    date DATE NOT NULL,
    hours INT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);