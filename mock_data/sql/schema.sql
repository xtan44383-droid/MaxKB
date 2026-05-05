-- 售后知识与工单数据助手：PostgreSQL 演示库表结构

DROP TABLE IF EXISTS ticket_logs;
DROP TABLE IF EXISTS tickets;
DROP TABLE IF EXISTS products;

CREATE TABLE products (
    product_model VARCHAR(32) PRIMARY KEY,
    product_name VARCHAR(128) NOT NULL,
    category VARCHAR(64) NOT NULL,
    warranty_months INTEGER NOT NULL,
    release_year INTEGER NOT NULL
);

CREATE TABLE tickets (
    ticket_id VARCHAR(32) PRIMARY KEY,
    product_model VARCHAR(32) NOT NULL REFERENCES products(product_model),
    fault_code VARCHAR(32) NOT NULL,
    fault_type VARCHAR(64) NOT NULL,
    region VARCHAR(32) NOT NULL,
    customer_type VARCHAR(32) NOT NULL,
    priority VARCHAR(16) NOT NULL,
    status VARCHAR(16) NOT NULL,
    channel VARCHAR(32) NOT NULL,
    handler_name VARCHAR(64) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    closed_at TIMESTAMP NULL,
    satisfaction_score NUMERIC(3,1) NULL,
    is_escalated BOOLEAN NOT NULL DEFAULT FALSE,
    issue_summary TEXT NOT NULL
);

CREATE TABLE ticket_logs (
    log_id VARCHAR(32) PRIMARY KEY,
    ticket_id VARCHAR(32) NOT NULL REFERENCES tickets(ticket_id),
    action_type VARCHAR(32) NOT NULL,
    action_note TEXT NOT NULL,
    operator_name VARCHAR(64) NOT NULL,
    action_time TIMESTAMP NOT NULL
);

CREATE INDEX idx_tickets_product_model ON tickets(product_model);
CREATE INDEX idx_tickets_fault_code ON tickets(fault_code);
CREATE INDEX idx_tickets_region ON tickets(region);
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_created_at ON tickets(created_at);
CREATE INDEX idx_ticket_logs_ticket_id ON ticket_logs(ticket_id);
