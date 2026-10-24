-- ======================================================================
-- INSTALACIÓN NUEVA (base de datos vacía) - VERSIÓN FINAL DEL MVP
-- Úsalo para instalar el sistema desde cero (ej. en el servidor de producción).
-- Si ya tienes la base de un paso anterior, usa los scripts de migración 02, 03 y 04
-- (solo los que te falten, en orden).
-- ======================================================================
CREATE DATABASE IF NOT EXISTS db_cotizaciones CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE db_cotizaciones;

-- Cada empresa que te compra el sistema es una fila aquí (un "inquilino").
CREATE TABLE empresas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(150) NOT NULL,
  nit VARCHAR(30) NULL,
  -- Datos que salen en el PDF
  direccion VARCHAR(255) NULL,
  telefono VARCHAR(30) NULL,
  email VARCHAR(100) NULL,
  sitio_web VARCHAR(100) NULL,
  logo_path VARCHAR(255) NULL,
  color_primario CHAR(7) NOT NULL DEFAULT '#1F4E79',
  -- Preferencias comerciales
  moneda CHAR(3) NOT NULL DEFAULT 'COP',
  iva_defecto DECIMAL(5,2) NOT NULL DEFAULT 19.00,
  validez_dias INT NOT NULL DEFAULT 15,
  prefijo VARCHAR(10) NOT NULL DEFAULT 'COT',
  condiciones TEXT NULL,
  ultimo_numero INT NOT NULL DEFAULT 0,   -- contador de cotizaciones de la empresa
  creada_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE usuarios (
  id INT AUTO_INCREMENT PRIMARY KEY,
  empresa_id INT NOT NULL,
  nombre VARCHAR(100) NOT NULL,
  email VARCHAR(100) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  rol ENUM('admin','vendedor') NOT NULL DEFAULT 'vendedor',
  activo TINYINT(1) NOT NULL DEFAULT 1,
  creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_usuario_email (email),
  CONSTRAINT fk_usuario_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)
) ENGINE=InnoDB;

CREATE TABLE clientes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  empresa_id INT NOT NULL,
  nombre VARCHAR(150) NOT NULL,
  identificacion VARCHAR(20) NOT NULL,
  telefono VARCHAR(20) NULL,
  email VARCHAR(100) NULL,
  direccion VARCHAR(255) NULL,
  activo TINYINT(1) NOT NULL DEFAULT 1,
  UNIQUE KEY uq_cliente_identificacion (empresa_id, identificacion),
  CONSTRAINT fk_cliente_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)
) ENGINE=InnoDB;

CREATE TABLE items (
  id INT AUTO_INCREMENT PRIMARY KEY,
  empresa_id INT NOT NULL,
  nombre VARCHAR(150) NOT NULL,
  descripcion TEXT NULL,
  precio_unitario DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  tipo ENUM('producto','servicio') NOT NULL,
  activo TINYINT(1) NOT NULL DEFAULT 1,
  KEY idx_items_empresa (empresa_id),
  CONSTRAINT fk_item_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)
) ENGINE=InnoDB;

CREATE TABLE cotizaciones (
  id INT AUTO_INCREMENT PRIMARY KEY,
  empresa_id INT NOT NULL,
  numero INT NOT NULL,            -- consecutivo propio de cada empresa
  usuario_id INT NULL,            -- quién la creó
  cliente_id INT NOT NULL,
  fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  fecha_vencimiento DATE NOT NULL,
  subtotal DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  descuento DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  iva_porcentaje DECIMAL(5,2) NOT NULL,   -- IVA usado en ESTA cotización
  impuesto DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  total DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  estado ENUM('Pendiente','Aceptada','Rechazada') NOT NULL DEFAULT 'Pendiente',
  notas TEXT NULL,
  activo TINYINT(1) NOT NULL DEFAULT 1,
  UNIQUE KEY uq_cot_numero (empresa_id, numero),
  KEY idx_cot_empresa_fecha (empresa_id, fecha),
  CONSTRAINT fk_cot_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id),
  CONSTRAINT fk_cot_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
  CONSTRAINT fk_cot_cliente FOREIGN KEY (cliente_id) REFERENCES clientes(id)
) ENGINE=InnoDB;

CREATE TABLE cotizacion_detalles (
  id INT AUTO_INCREMENT PRIMARY KEY,
  cotizacion_id INT NOT NULL,
  item_id INT NOT NULL,
  cantidad DECIMAL(10,2) NOT NULL DEFAULT 1.00,
  precio_unitario DECIMAL(12,2) NOT NULL,
  subtotal_linea DECIMAL(12,2) NOT NULL,
  KEY idx_det_cotizacion (cotizacion_id),
  CONSTRAINT fk_det_cotizacion FOREIGN KEY (cotizacion_id) REFERENCES cotizaciones(id) ON DELETE CASCADE,
  CONSTRAINT fk_det_item FOREIGN KEY (item_id) REFERENCES items(id)
) ENGINE=InnoDB;

-- Bitácora: cada cambio de estado de una cotización queda registrado (quién, cuándo, de qué a qué).
CREATE TABLE cotizacion_historial (
  id INT AUTO_INCREMENT PRIMARY KEY,
  cotizacion_id INT NOT NULL,
  usuario_id INT NULL,
  estado_anterior VARCHAR(20) NULL,       -- NULL en el registro de creación
  estado_nuevo VARCHAR(20) NOT NULL,
  comentario VARCHAR(255) NULL,
  fecha TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_hist_cotizacion (cotizacion_id),
  CONSTRAINT fk_hist_cotizacion FOREIGN KEY (cotizacion_id) REFERENCES cotizaciones(id) ON DELETE CASCADE,
  CONSTRAINT fk_hist_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
) ENGINE=InnoDB;
