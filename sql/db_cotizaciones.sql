CREATE DATABASE db_cotizaciones CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE db_cotizaciones;

-- =====================================================================================
--  PARTE 1: ESTRUCTURA (las 7 tablas)
--
--  Cómo se relacionan (cada flecha significa "pertenece a"):
--
--     empresas  <---  usuarios            Cada usuario pertenece a UNA empresa.
--        ^   ^
--        |   +------  clientes            Clientes, ítems y cotizaciones también
--        |   +------  items               llevan "empresa_id": así cada empresa
--        |   +------  cotizaciones        solo ve SUS datos (multiempresa).
--        |                 ^   ^
--        |                 |   +--------  cotizacion_historial   (cambios de estado)
--        |                 +------------  cotizacion_detalles    (líneas: qué ítems y cuántos)
--
--  "FOREIGN KEY" = llave foránea: obliga a que el dato apunte a algo que existe
--  (no puedes crear una cotización para un cliente inexistente).
--  "UNIQUE KEY" = valor que no se puede repetir.
-- =====================================================================================

-- EMPRESAS: cada negocio que usa el sistema es una fila. Aquí vive su configuración.
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

-- USUARIOS: las personas que inician sesión. El correo no se puede repetir en todo el sistema.
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

-- CLIENTES: a quién se le cotiza. La identificación no se repite DENTRO de una empresa
-- (pero dos empresas distintas sí pueden tener el mismo cliente).
CREATE TABLE clientes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  empresa_id INT NOT NULL,
  nombre VARCHAR(150) NOT NULL,
  identificacion VARCHAR(20) NOT NULL,
  telefono VARCHAR(20) NULL,
  email VARCHAR(100) NULL,
  direccion VARCHAR(255) NULL,
  activo TINYINT(1) NOT NULL DEFAULT 1,   -- 0 = "borrado" (baja lógica: el dato se conserva)
  UNIQUE KEY uq_cliente_identificacion (empresa_id, identificacion),
  CONSTRAINT fk_cliente_empresa FOREIGN KEY (empresa_id) REFERENCES empresas(id)
) ENGINE=InnoDB;

-- ITEMS: el catálogo de productos y servicios que la empresa vende.
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

-- COTIZACIONES: la "cabecera" de cada cotización (totales, estado, vencimiento).
-- Las líneas (qué ítems y cuántos) están en cotizacion_detalles.
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

-- COTIZACION_DETALLES: las líneas de cada cotización (ítem, cantidad, precio y subtotal de la línea).
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

-- COTIZACION_HISTORIAL: bitácora. Cada cambio de estado queda registrado (quién, cuándo, de qué a qué).
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


-- =====================================================================================
--  PARTE 2: DATOS DE EJEMPLO
--  Se insertan en este orden porque una tabla no puede apuntar a algo que aún no existe
--  (primero empresas, luego usuarios/clientes/ítems, luego cotizaciones, etc.).
-- =====================================================================================

-- ---- Empresas (ultimo_numero = el último número de cotización que ya usó cada una)
INSERT INTO empresas
  (id, nombre, nit, direccion, telefono, email, sitio_web, logo_path, color_primario,
   moneda, iva_defecto, validez_dias, prefijo, condiciones, ultimo_numero)
VALUES
  (1, 'Ferretería El Tornillo S.A.S.', '900123456-1', 'Calle 45 # 20-10, Barranquilla', '300 123 4567', 'ventas@eltornillo.com', 'www.eltornillo.com', NULL, '#1F4E79', 'COP', 19.00, 30, 'FER', '1. Precios sujetos a disponibilidad de inventario.
2. Pago: 50% anticipado y 50% contra entrega.
3. Garantía de 6 meses por defectos de fabricación o instalación.', 9),
  (2, 'Estudio Creativo Luna S.A.S.', '901456789-3', 'Carrera 53 # 76-120, Oficina 402, Barranquilla', '315 222 3344', 'hola@estudioluna.co', 'www.estudioluna.co', NULL, '#7B2D8E', 'COP', 19.00, 15, 'LUN', '1. Se requiere un anticipo del 50% para iniciar el trabajo.
2. Incluye hasta 2 rondas de ajustes; los cambios adicionales se cotizan aparte.
3. Los archivos finales se entregan al recibir el pago total.', 6);

-- ---- Usuarios (el password_hash es la "huella" de la contraseña Clave12345; la clave real nunca se guarda)
INSERT INTO usuarios (id, empresa_id, nombre, email, password_hash, rol, activo)
VALUES
  (1, 1, 'Carlos Pérez', 'carlos@eltornillo.com', 'scrypt:32768:8:1$tjjAmaCgpOrGQblP$07e59210acd3f16804f00907eeceae94b27ece4a2bed95478312371934c3040c98b732a3d05965da3956c1590d2754398bfac0024f0a2e3d2338f12cccb02939', 'admin', 1),
  (2, 1, 'Laura Gómez', 'laura@eltornillo.com', 'scrypt:32768:8:1$2Q8z7GmUJdvGpYVd$614f7e3d3baa5b342c5a1d2987b79f6696a26ad12eb8d1f397aaa29231f6e88169ecdb17f1b06bd7104af04bce0bdbbfef128207983c2cb8aca09712269cb631', 'vendedor', 1),
  (3, 1, 'Pedro Ramírez', 'pedro@eltornillo.com', 'scrypt:32768:8:1$z4XkRgpCikIKycWA$22f8ee030cac4e459852aa447d7e2fa1e597f5dec0a0e271e0b0b941b6be39cf142995d148fb89ece65917d4d01660841c91ab696111a4dd6fd523ea370245c9', 'vendedor', 0),
  (4, 2, 'Lucía Torres', 'lucia@estudioluna.co', 'scrypt:32768:8:1$BfZMqZuQkFwqJmQT$826b59c42df57603c5f9f80312a6c8f08420151fcb00a1e863667b62c7b042672df04130bd656c1a160b57aa025c238daa27db976ab1e017a333bf06854aee6d', 'admin', 1),
  (5, 2, 'Andrés Mejía', 'andres@estudioluna.co', 'scrypt:32768:8:1$o5YidPx5YclAgw0O$ffe4b5ec0de8990e0381bbb568a1d1a3ab7661e828fce9baf67427d853c1565c226a2e0fd510911bb7835f97805189176fb1be61081f576ceab8cbe597f2039f', 'vendedor', 1);

-- ---- Clientes (el 5 está desactivado; el 1 y el 6 tienen el mismo NIT pero son de empresas distintas)
INSERT INTO clientes (id, empresa_id, nombre, identificacion, telefono, email, direccion, activo)
VALUES
  (1, 1, 'Constructora Andina S.A.S.', '900555111-2', '3109876543', 'compras@andina.com', 'Carrera 50 # 80-15, Barranquilla', 1),
  (2, 1, 'María Gómez', '1045123456', '3157654321', 'maria.gomez@gmail.com', 'Calle 30 # 12-40, Soledad', 1),
  (3, 1, 'Hotel Playa Dorada Ltda.', '802334455-7', '3205551234', 'administracion@playadorada.co', 'Vía 40 # 85-120, Puerto Colombia', 1),
  (4, 1, 'Inversiones Caribe Sur S.A.', '890112233-4', '3004447788', 'gerencia@caribesur.com', 'Calle 72 # 54-30, Barranquilla', 1),
  (5, 1, 'Pedro Salcedo', '72345678', '3121112233', NULL, 'Calle 8 # 5-12, Malambo', 0),
  (6, 2, 'Constructora Andina S.A.S.', '900555111-2', '3109876543', 'compras@andina.com', 'Carrera 50 # 80-15, Barranquilla', 1),
  (7, 2, 'Panadería La Espiga', '901234567-8', '3186669900', 'contacto@laespiga.co', 'Carrera 21 # 45-67, Soledad', 1),
  (8, 2, 'Dra. Valentina Ríos', '1129876543', '3173332211', 'valentina@riosodontologia.com', 'Calle 85 # 49-25, Barranquilla', 1),
  (9, 2, 'Gimnasio Fuerza Total', '900876543-1', '3022223344', 'info@fuerzatotal.com', 'Avenida Circunvalar # 12-80, Barranquilla', 1);

-- ---- Catálogo de productos y servicios (el 7 y el 13 están desactivados)
INSERT INTO items (id, empresa_id, nombre, descripcion, precio_unitario, tipo, activo)
VALUES
  (1, 1, 'Mano de Obra - Instalación Eléctrica', 'Instalación de puntos de red y revisión de tablero', 85000, 'servicio', 1),
  (2, 1, 'Kit de Herramientas Profesionales Plus', 'Maletín metálico con 60 piezas y llaves mixtas reforzadas', 125000, 'producto', 1),
  (3, 1, 'Taladro Percutor 800W', 'Taladro con maletín y set de brocas', 210000, 'producto', 1),
  (4, 1, 'Cable THHN calibre 12 (por metro)', 'Cable de cobre aislado para instalaciones residenciales', 2100, 'producto', 1),
  (5, 1, 'Visita técnica y diagnóstico', 'Revisión en sitio con informe de hallazgos', 60000, 'servicio', 1),
  (6, 1, 'Mantenimiento de tablero eléctrico', 'Limpieza, ajuste de conexiones y verificación de protecciones', 150000, 'servicio', 1),
  (7, 1, 'Sierra circular 7 1/4 pulgadas', 'Modelo descontinuado', 320000, 'producto', 0),
  (8, 2, 'Diseño de logo e identidad básica', 'Logo, paleta de colores y tipografías', 850000, 'servicio', 1),
  (9, 2, 'Manual de marca', 'Guía de uso del logo, colores y aplicaciones', 1200000, 'servicio', 1),
  (10, 2, 'Gestión de redes sociales (mensual)', 'Planeación, publicación y reporte mensual en 2 redes', 650000, 'servicio', 1),
  (11, 2, 'Paquete de piezas gráficas (10 diseños)', 'Diseños para publicaciones, historias o volantes', 300000, 'servicio', 1),
  (12, 2, 'Tarjetas de presentación (millar)', 'Impresión a todo color, propalcote 300 g', 180000, 'producto', 1),
  (13, 2, 'Paquete promocional de lanzamiento', 'Promoción finalizada', 990000, 'servicio', 0);

-- ---- Cotizaciones
--  Las fechas son RELATIVAS a hoy (NOW / CURDATE): así siempre habrá cotizaciones
--  vencidas, por vencer y repartidas en los últimos meses para probar el panel.
--  La cotización 4 de la empresa 1 está anulada (activo = 0).
INSERT INTO cotizaciones
  (id, empresa_id, numero, usuario_id, cliente_id, fecha, fecha_vencimiento,
   subtotal, descuento, iva_porcentaje, impuesto, total, estado, notas, activo)
VALUES
  (1, 1, 1, 1, 1, DATE_SUB(NOW(), INTERVAL 140 DAY), DATE_ADD(CURDATE(), INTERVAL -110 DAY), 575000.00, 0.00, 19.00, 109250.00, 684250.00, 'Aceptada', 'Incluye instalación y retiro de residuos.', 1),
  (2, 1, 2, 3, 3, DATE_SUB(NOW(), INTERVAL 100 DAY), DATE_ADD(CURDATE(), INTERVAL -70 DAY), 360000.00, 20000.00, 19.00, 64600.00, 404600.00, 'Aceptada', NULL, 1),
  (3, 1, 3, 2, 2, DATE_SUB(NOW(), INTERVAL 75 DAY), DATE_ADD(CURDATE(), INTERVAL -45 DAY), 335000.00, 0.00, 19.00, 63650.00, 398650.00, 'Rechazada', NULL, 1),
  (4, 1, 4, 2, 5, DATE_SUB(NOW(), INTERVAL 60 DAY), DATE_ADD(CURDATE(), INTERVAL -30 DAY), 125000.00, 0.00, 19.00, 23750.00, 148750.00, 'Pendiente', 'Cotización anulada por error de cliente.', 0),
  (5, 1, 5, 1, 4, DATE_SUB(NOW(), INTERVAL 50 DAY), DATE_ADD(CURDATE(), INTERVAL -20 DAY), 865000.00, 150000.00, 19.00, 135850.00, 850850.00, 'Aceptada', 'Cable entregado por rollos de 100 m.', 1),
  (6, 1, 6, 2, 1, DATE_SUB(NOW(), INTERVAL 35 DAY), DATE_ADD(CURDATE(), INTERVAL -5 DAY), 625000.00, 0.00, 19.00, 118750.00, 743750.00, 'Pendiente', NULL, 1),
  (7, 1, 7, 2, 2, DATE_SUB(NOW(), INTERVAL 27 DAY), DATE_ADD(CURDATE(), INTERVAL 3 DAY), 460000.00, 0.00, 19.00, 87400.00, 547400.00, 'Pendiente', 'Precio especial por compra de 2 unidades.', 1),
  (8, 1, 8, 1, 3, DATE_SUB(NOW(), INTERVAL 20 DAY), DATE_ADD(CURDATE(), INTERVAL 10 DAY), 610000.00, 50000.00, 19.00, 106400.00, 666400.00, 'Pendiente', NULL, 1),
  (9, 1, 9, 1, 4, NOW(), DATE_ADD(CURDATE(), INTERVAL 30 DAY), 471250.00, 10000.00, 19.00, 87637.50, 548887.50, 'Pendiente', 'Instalación incluida.', 1),
  (10, 2, 1, 4, 7, DATE_SUB(NOW(), INTERVAL 120 DAY), DATE_ADD(CURDATE(), INTERVAL -105 DAY), 1150000.00, 0.00, 19.00, 218500.00, 1368500.00, 'Aceptada', NULL, 1),
  (11, 2, 2, 5, 8, DATE_SUB(NOW(), INTERVAL 85 DAY), DATE_ADD(CURDATE(), INTERVAL -70 DAY), 1950000.00, 100000.00, 19.00, 351500.00, 2201500.00, 'Aceptada', 'Contrato por 3 meses.', 1),
  (12, 2, 3, 5, 9, DATE_SUB(NOW(), INTERVAL 55 DAY), DATE_ADD(CURDATE(), INTERVAL -40 DAY), 2050000.00, 200000.00, 19.00, 351500.00, 2201500.00, 'Rechazada', NULL, 1),
  (13, 2, 4, 4, 6, DATE_SUB(NOW(), INTERVAL 30 DAY), DATE_ADD(CURDATE(), INTERVAL -15 DAY), 4200000.00, 0.00, 0.00, 0.00, 4200000.00, 'Pendiente', 'Cotización exenta de IVA según contrato marco.', 1),
  (14, 2, 5, 5, 7, DATE_SUB(NOW(), INTERVAL 10 DAY), DATE_ADD(CURDATE(), INTERVAL 5 DAY), 660000.00, 0.00, 19.00, 125400.00, 785400.00, 'Pendiente', NULL, 1),
  (15, 2, 6, 4, 8, DATE_SUB(NOW(), INTERVAL 1 DAY), DATE_ADD(CURDATE(), INTERVAL 14 DAY), 3350000.00, 150000.00, 19.00, 608000.00, 3808000.00, 'Pendiente', 'Paquete de marca completo.', 1);

-- ---- Líneas de cada cotización (subtotal_linea = cantidad x precio_unitario)
INSERT INTO cotizacion_detalles (id, cotizacion_id, item_id, cantidad, precio_unitario, subtotal_linea)
VALUES
  (1, 1, 7, 1.00, 320000.00, 320000.00),
  (2, 1, 1, 3.00, 85000.00, 255000.00),
  (3, 2, 6, 2.00, 150000.00, 300000.00),
  (4, 2, 5, 1.00, 60000.00, 60000.00),
  (5, 3, 3, 1.00, 210000.00, 210000.00),
  (6, 3, 2, 1.00, 125000.00, 125000.00),
  (7, 4, 2, 1.00, 125000.00, 125000.00),
  (8, 5, 4, 250.00, 2100.00, 525000.00),
  (9, 5, 1, 4.00, 85000.00, 340000.00),
  (10, 6, 2, 5.00, 125000.00, 625000.00),
  (11, 7, 3, 2.00, 200000.00, 400000.00),
  (12, 7, 5, 1.00, 60000.00, 60000.00),
  (13, 8, 6, 3.00, 150000.00, 450000.00),
  (14, 8, 1, 2.00, 80000.00, 160000.00),
  (15, 9, 1, 2.00, 85000.00, 170000.00),
  (16, 9, 2, 1.00, 125000.00, 125000.00),
  (17, 9, 6, 1.00, 150000.00, 150000.00),
  (18, 9, 4, 12.50, 2100.00, 26250.00),
  (19, 10, 8, 1.00, 850000.00, 850000.00),
  (20, 10, 11, 1.00, 300000.00, 300000.00),
  (21, 11, 10, 3.00, 650000.00, 1950000.00),
  (22, 12, 9, 1.00, 1200000.00, 1200000.00),
  (23, 12, 8, 1.00, 850000.00, 850000.00),
  (24, 13, 10, 6.00, 600000.00, 3600000.00),
  (25, 13, 11, 2.00, 300000.00, 600000.00),
  (26, 14, 12, 2.00, 180000.00, 360000.00),
  (27, 14, 11, 1.00, 300000.00, 300000.00),
  (28, 15, 8, 1.00, 850000.00, 850000.00),
  (29, 15, 9, 1.00, 1200000.00, 1200000.00),
  (30, 15, 10, 2.00, 650000.00, 1300000.00);

-- ---- Historial: cada cotización tiene su registro de creación y sus cambios de estado
INSERT INTO cotizacion_historial (id, cotizacion_id, usuario_id, estado_anterior, estado_nuevo, comentario, fecha)
VALUES
  (1, 1, 1, NULL, 'Pendiente', 'Cotización creada', DATE_SUB(NOW(), INTERVAL 140 DAY)),
  (2, 1, 1, 'Pendiente', 'Aceptada', 'Aprobada por el gerente de obra', DATE_SUB(NOW(), INTERVAL 134 DAY)),
  (3, 2, 3, NULL, 'Pendiente', 'Cotización creada', DATE_SUB(NOW(), INTERVAL 100 DAY)),
  (4, 2, 3, 'Pendiente', 'Aceptada', 'Confirmó por correo', DATE_SUB(NOW(), INTERVAL 97 DAY)),
  (5, 3, 2, NULL, 'Pendiente', 'Cotización creada', DATE_SUB(NOW(), INTERVAL 75 DAY)),
  (6, 3, 2, 'Pendiente', 'Rechazada', 'Compró en otra ferretería por precio', DATE_SUB(NOW(), INTERVAL 67 DAY)),
  (7, 4, 2, NULL, 'Pendiente', 'Cotización creada', DATE_SUB(NOW(), INTERVAL 60 DAY)),
  (8, 5, 1, NULL, 'Pendiente', 'Cotización creada', DATE_SUB(NOW(), INTERVAL 50 DAY)),
  (9, 5, 1, 'Pendiente', 'Rechazada', 'Cliente pidió revisar el valor', DATE_SUB(NOW(), INTERVAL 45 DAY)),
  (10, 5, 1, 'Rechazada', 'Aceptada', 'Aceptó tras mejorar el descuento', DATE_SUB(NOW(), INTERVAL 38 DAY)),
  (11, 6, 2, NULL, 'Pendiente', 'Cotización creada', DATE_SUB(NOW(), INTERVAL 35 DAY)),
  (12, 7, 2, NULL, 'Pendiente', 'Cotización creada', DATE_SUB(NOW(), INTERVAL 27 DAY)),
  (13, 8, 1, NULL, 'Pendiente', 'Cotización creada', DATE_SUB(NOW(), INTERVAL 20 DAY)),
  (14, 9, 1, NULL, 'Pendiente', 'Cotización creada', NOW()),
  (15, 10, 4, NULL, 'Pendiente', 'Cotización creada', DATE_SUB(NOW(), INTERVAL 120 DAY)),
  (16, 10, 4, 'Pendiente', 'Aceptada', 'Aprobó la propuesta por WhatsApp', DATE_SUB(NOW(), INTERVAL 116 DAY)),
  (17, 11, 5, NULL, 'Pendiente', 'Cotización creada', DATE_SUB(NOW(), INTERVAL 85 DAY)),
  (18, 11, 5, 'Pendiente', 'Aceptada', 'Firmó el contrato', DATE_SUB(NOW(), INTERVAL 83 DAY)),
  (19, 12, 5, NULL, 'Pendiente', 'Cotización creada', DATE_SUB(NOW(), INTERVAL 55 DAY)),
  (20, 12, 5, 'Pendiente', 'Rechazada', 'Presupuesto insuficiente por ahora', DATE_SUB(NOW(), INTERVAL 45 DAY)),
  (21, 13, 4, NULL, 'Pendiente', 'Cotización creada', DATE_SUB(NOW(), INTERVAL 30 DAY)),
  (22, 14, 5, NULL, 'Pendiente', 'Cotización creada', DATE_SUB(NOW(), INTERVAL 10 DAY)),
  (23, 15, 4, NULL, 'Pendiente', 'Cotización creada', DATE_SUB(NOW(), INTERVAL 1 DAY));

-- =====================================================================================
--  VERIFICACIÓN: cantidad de filas de cada tabla (ninguna debe estar en 0)
-- =====================================================================================
SELECT 'empresas' AS tabla, COUNT(*) AS filas FROM empresas
UNION ALL SELECT 'usuarios', COUNT(*) FROM usuarios
UNION ALL SELECT 'clientes', COUNT(*) FROM clientes
UNION ALL SELECT 'items', COUNT(*) FROM items
UNION ALL SELECT 'cotizaciones', COUNT(*) FROM cotizaciones
UNION ALL SELECT 'cotizacion_detalles', COUNT(*) FROM cotizacion_detalles
UNION ALL SELECT 'cotizacion_historial', COUNT(*) FROM cotizacion_historial;