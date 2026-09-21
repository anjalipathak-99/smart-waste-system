-- Smart Waste Segregation & Collection System
-- MySQL schema (also auto-created by SQLAlchemy via `python seed_data.py`)

CREATE DATABASE IF NOT EXISTS smart_waste_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smart_waste_db;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'worker', 'citizen') NOT NULL DEFAULT 'citizen',
    phone VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS bins (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(30) NOT NULL UNIQUE,
    area VARCHAR(120) NOT NULL,
    address VARCHAR(255),
    latitude DOUBLE NOT NULL,
    longitude DOUBLE NOT NULL,
    bin_type ENUM('General','Plastic','Paper','Metal','Glass','Organic','E-waste') DEFAULT 'General',
    capacity_kg DOUBLE DEFAULT 100.0,
    fill_level DOUBLE DEFAULT 0.0,
    weight_kg DOUBLE DEFAULT 0.0,
    temperature_c DOUBLE DEFAULT 28.0,
    battery_percent DOUBLE DEFAULT 100.0,
    status ENUM('normal','warning','critical','damaged') DEFAULT 'normal',
    last_collected_at DATETIME NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS sensor_readings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bin_id INT NOT NULL,
    fill_level DOUBLE NOT NULL,
    weight_kg DOUBLE NOT NULL,
    temperature_c DOUBLE NOT NULL,
    battery_percent DOUBLE NOT NULL,
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bin_id) REFERENCES bins(id) ON DELETE CASCADE,
    INDEX idx_bin_recorded (bin_id, recorded_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS waste_classifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    bin_id INT NULL,
    image_path VARCHAR(255) NOT NULL,
    predicted_class VARCHAR(30) NOT NULL,
    confidence DOUBLE NOT NULL,
    all_probabilities JSON,
    model_used VARCHAR(60) DEFAULT 'MobileNetV2-TransferLearning',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (bin_id) REFERENCES bins(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS citizen_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    citizen_id INT NOT NULL,
    bin_id INT NULL,
    report_type ENUM('overflow','damaged','missed_collection','other') NOT NULL,
    description TEXT,
    image_path VARCHAR(255),
    latitude DOUBLE,
    longitude DOUBLE,
    status ENUM('pending','in_progress','resolved') DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME NULL,
    FOREIGN KEY (citizen_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (bin_id) REFERENCES bins(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bin_id INT NOT NULL,
    alert_type ENUM('overflow','damage','sensor_fault','high_temperature') NOT NULL,
    message VARCHAR(255) NOT NULL,
    severity ENUM('low','medium','high') DEFAULT 'medium',
    is_resolved BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bin_id) REFERENCES bins(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS collection_routes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    worker_id INT NOT NULL,
    route_date DATE,
    status ENUM('pending','in_progress','completed') DEFAULT 'pending',
    total_distance_km DOUBLE DEFAULT 0.0,
    estimated_time_min DOUBLE DEFAULT 0.0,
    algorithm_used VARCHAR(30) DEFAULT 'A*',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (worker_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS route_stops (
    id INT AUTO_INCREMENT PRIMARY KEY,
    route_id INT NOT NULL,
    bin_id INT NOT NULL,
    sequence_order INT NOT NULL,
    status ENUM('pending','collected','skipped') DEFAULT 'pending',
    collected_at DATETIME NULL,
    FOREIGN KEY (route_id) REFERENCES collection_routes(id) ON DELETE CASCADE,
    FOREIGN KEY (bin_id) REFERENCES bins(id) ON DELETE CASCADE
) ENGINE=InnoDB;
