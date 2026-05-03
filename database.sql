CREATE DATABASE IF NOT EXISTS gestion_mesas;
USE gestion_mesas;

CREATE TABLE IF NOT EXISTS restaurantes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    ciudad VARCHAR(100) NOT NULL,
    total_mesas INT NOT NULL,
    mesas_ocupadas INT NOT NULL DEFAULT 0
);

INSERT INTO restaurantes (nombre, ciudad, total_mesas, mesas_ocupadas) VALUES
('Sabor Colombiano', 'Bogotá', 20, 8),
('La Parrilla Real', 'Medellín', 15, 14),
('Costa Marina', 'Cali', 12, 12);
