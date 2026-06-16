-- ============================================================
-- Project Marketplace Chatbot — MySQL Schema
-- Run: mysql -u root -p < schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS project_marketplace
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE project_marketplace;

-- 1. USERS
CREATE TABLE IF NOT EXISTS users (
    id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(100)  NOT NULL,
    email         VARCHAR(150)  NOT NULL UNIQUE,
    password_hash VARCHAR(255)  NOT NULL,
    role          ENUM('buyer','seller','both','admin') NOT NULL DEFAULT 'buyer',
    avatar_url    VARCHAR(500)  DEFAULT NULL,
    is_verified   TINYINT(1)    NOT NULL DEFAULT 0,
    is_active     TINYINT(1)    NOT NULL DEFAULT 1,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_email (email),
    INDEX idx_users_role  (role)
);

-- 2. CATEGORIES
CREATE TABLE IF NOT EXISTS categories (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    slug        VARCHAR(100) NOT NULL UNIQUE,
    description TEXT         DEFAULT NULL,
    sort_order  INT          NOT NULL DEFAULT 0,
    is_active   TINYINT(1)   NOT NULL DEFAULT 1,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT IGNORE INTO categories (name, slug, sort_order) VALUES
    ('Java Projects',       'java',       1),
    ('Python Projects',     'python',     2),
    ('AI/ML Projects',      'ai-ml',      3),
    ('Web Development',     'web-dev',    4),
    ('Final Year Projects', 'final-year', 5),
    ('Mini Projects',       'mini',       6);

-- 3. PROJECTS
CREATE TABLE IF NOT EXISTS projects (
    id             INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    seller_id      INT UNSIGNED   NOT NULL,
    category_id    INT UNSIGNED   NOT NULL,
    title          VARCHAR(200)   NOT NULL,
    slug           VARCHAR(220)   NOT NULL UNIQUE,
    description    TEXT           DEFAULT NULL,
    tech_stack     VARCHAR(300)   DEFAULT NULL,
    price          DECIMAL(10,2)  NOT NULL DEFAULT 0.00,
    original_price DECIMAL(10,2)  DEFAULT NULL,
    demo_url       VARCHAR(500)   DEFAULT NULL,
    download_url   VARCHAR(500)   DEFAULT NULL,
    thumbnail_url  VARCHAR(500)   DEFAULT NULL,
    difficulty     ENUM('beginner','intermediate','advanced') NOT NULL DEFAULT 'beginner',
    status         ENUM('draft','pending','approved','rejected','archived') NOT NULL DEFAULT 'pending',
    total_sales    INT UNSIGNED   NOT NULL DEFAULT 0,
    avg_rating     DECIMAL(3,2)   NOT NULL DEFAULT 0.00,
    total_reviews  INT UNSIGNED   NOT NULL DEFAULT 0,
    is_featured    TINYINT(1)     NOT NULL DEFAULT 0,
    created_at     DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (seller_id)   REFERENCES users(id)      ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT,
    INDEX idx_projects_seller   (seller_id),
    INDEX idx_projects_category (category_id),
    INDEX idx_projects_status   (status),
    FULLTEXT INDEX ft_projects_search (title, description, tech_stack)
);

-- 4. ORDERS
CREATE TABLE IF NOT EXISTS orders (
    id             INT UNSIGNED   AUTO_INCREMENT PRIMARY KEY,
    buyer_id       INT UNSIGNED   NOT NULL,
    project_id     INT UNSIGNED   NOT NULL,
    amount_paid    DECIMAL(10,2)  NOT NULL,
    currency       VARCHAR(10)    NOT NULL DEFAULT 'INR',
    payment_method VARCHAR(50)    DEFAULT NULL,
    payment_id     VARCHAR(200)   DEFAULT NULL,
    status         ENUM('pending','completed','failed','refunded') NOT NULL DEFAULT 'pending',
    purchased_at   DATETIME       DEFAULT NULL,
    created_at     DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (buyer_id)   REFERENCES users(id)    ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    INDEX idx_orders_buyer   (buyer_id),
    INDEX idx_orders_project (project_id),
    INDEX idx_orders_status  (status)
);

-- 5. REVIEWS
CREATE TABLE IF NOT EXISTS reviews (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    project_id  INT UNSIGNED NOT NULL,
    reviewer_id INT UNSIGNED NOT NULL,
    rating      TINYINT      NOT NULL CHECK (rating BETWEEN 1 AND 5),
    title       VARCHAR(200) DEFAULT NULL,
    body        TEXT         DEFAULT NULL,
    is_verified TINYINT(1)   NOT NULL DEFAULT 0,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id)  REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (reviewer_id) REFERENCES users(id)    ON DELETE CASCADE,
    UNIQUE KEY uq_review_once (project_id, reviewer_id)
);

-- 6. CHAT SESSIONS
CREATE TABLE IF NOT EXISTS chat_sessions (
    id             VARCHAR(64)  NOT NULL PRIMARY KEY,
    user_id        INT UNSIGNED DEFAULT NULL,
    user_type      ENUM('buyer','seller','anonymous') NOT NULL DEFAULT 'anonymous',
    channel        VARCHAR(50)  NOT NULL DEFAULT 'web',
    started_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at       DATETIME     DEFAULT NULL,
    is_escalated   TINYINT(1)   NOT NULL DEFAULT 0,
    total_messages INT UNSIGNED NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_sessions_user    (user_id),
    INDEX idx_sessions_started (started_at)
);

-- 7. CHAT MESSAGES
CREATE TABLE IF NOT EXISTS chat_messages (
    id           INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id   VARCHAR(64)   NOT NULL,
    sender       ENUM('user','bot','human_agent') NOT NULL,
    message_text TEXT          NOT NULL,
    intent       VARCHAR(100)  DEFAULT NULL,
    confidence   DECIMAL(5,4)  DEFAULT NULL,
    handled_by   ENUM('rasa','ai_fallback','human') NOT NULL DEFAULT 'rasa',
    entities     JSON          DEFAULT NULL,
    sent_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
    INDEX idx_messages_session (session_id),
    INDEX idx_messages_sent    (sent_at)
);

-- 8. CHAT FEEDBACK
CREATE TABLE IF NOT EXISTS chat_feedback (
    id         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(64)  NOT NULL,
    message_id INT UNSIGNED DEFAULT NULL,
    rating     TINYINT      NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment    TEXT         DEFAULT NULL,
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (message_id) REFERENCES chat_messages(id) ON DELETE SET NULL
);

-- 9. ESCALATIONS
CREATE TABLE IF NOT EXISTS escalations (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    session_id  VARCHAR(64)  NOT NULL,
    reason      VARCHAR(300) DEFAULT NULL,
    agent_id    INT UNSIGNED DEFAULT NULL,
    status      ENUM('open','assigned','resolved') NOT NULL DEFAULT 'open',
    opened_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME     DEFAULT NULL,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (agent_id)   REFERENCES users(id)         ON DELETE SET NULL
);
