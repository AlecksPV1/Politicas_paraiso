# Sistema de Generación de Políticas y Consignación de Equipos de Cómputo

Aplicación web Full-Stack construida en **Python (Flask)**, **SQLite**, **ReportLab** y **HTML5/Bootstrap 5** para la automatización, registro, firma digital y generación de documentos PDF oficiales de Políticas de Uso y Asignación de Equipo de Cómputo.

---

## 🚀 Características Principales

1. **Seguridad y Acceso Restringido:**
   - Pantalla de inicio de sesión protegida con **contraseña maestra** (por defecto: `admin2026`, configurable por variable de entorno).
   - Protección de rutas y sesiones cifradas con `SECRET_KEY`.

2. **Formulario de Captura Intuitivo:**
   - Registro de datos obligatorios: Nombre del empleado, Equipo asignado, Marca, Modelo, Fecha de entrega, Estado físico del equipo y Notas / Accesorios.
   - Cálculo y visualización en tiempo real del próximo **Folio consecutivo** (`POL-0001`, `POL-0002`, etc.).

3. **Firma Digital Interactiva (HTML5 Canvas):**
   - Recuadro de trazo con soporte para ratón y pantallas táctiles (smartphones/tablets).
   - Botón para limpiar o rehacer firma.
   - Conversión automática a imagen PNG de alta resolución.

4. **Generación de PDF Oficial con ReportLab:**
   - Carga dinámica del texto legal desde el archivo de plantilla `plantilla_politica.txt`.
   - Inyección automática de todos los datos capturados y el Folio en el texto.
   - Encabezado con el logotipo corporativo (`logo.png`).
   - Tabla estilizada de especificaciones técnicas del equipo.
   - Incrustación de la firma digital trazada y recuadros para firmas físicas y sellos de TI.
   - Paginación dinámica en pie de página (*Página X de Y*).

5. **Panel de Control (Dashboard):**
   - Resumen estadístico de registros (Total, Firmados, Pendientes, Último Folio).
   - Tabla de historial con buscador y filtro en vivo.
   - Ficha técnica en modal para cada expediente.
   - Descarga directa e ilimitada de los archivos PDF generados.

---

## 📁 Estructura del Proyecto

```text
Generador_de_politicas/
├── app.py                     # Controlador principal Flask (rutas, auth, lógica)
├── config.py                  # Configuraciones y rutas del sistema
├── database.py                # Lógica SQLite (esquema, folios y consultas)
├── pdf_generator.py           # Motor de generación PDF con ReportLab
├── requirements.txt           # Dependencias Python
├── plantilla_politica.txt     # Plantilla de texto de la política
├── logo.png                   # Logotipo de la empresa para el encabezado del PDF
├── static/
│   ├── css/
│   │   └── styles.css         # Estilos visuales personalizados
│   └── js/
│       └── signature.js       # Manejo del canvas de firma digital táctil
├── templates/
│   ├── base.html              # Plantilla base con navbar y alertas
│   ├── login.html             # Pantalla de acceso por contraseña maestra
│   ├── form.html              # Formulario de captura y firma digital
│   └── dashboard.html         # Historial, buscador y descarga de PDFs
└── storage/
    ├── politicas.db           # Base de datos SQLite
    ├── pdfs/                  # Directorio de PDFs generados
    └── signatures/            # Imágenes de firmas digitales capturadas
```

---

## 🛠️ Requisitos e Instalación

### 1. Clonar o acceder a la carpeta del proyecto
```bash
cd /home/alecks/Documents/Generador_de_politicas
```

### 2. (Opcional recomendado) Crear un entorno virtual
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

---

## ⚙️ Configuración (Opcional)

Puedes personalizar las credenciales mediante variables de entorno antes de iniciar el servidor:

```bash
# Cambiar la contraseña maestra (por defecto: admin2026)
export MASTER_PASSWORD="TuContraseñaSegura123!"

# Cambiar la clave de sesión secreta
export SECRET_KEY="clave-aleatoria-personalizada"

# Cambiar el puerto (por defecto: 5000)
export PORT=5000
```

---

## ▶️ Ejecución del Servidor

Inicia la aplicación ejecutando:

```bash
python3 app.py
```

Abre tu navegador web en:
👉 **http://localhost:5000** (o http://127.0.0.1:5000)

- **Contraseña maestra inicial:** `admin2026`
