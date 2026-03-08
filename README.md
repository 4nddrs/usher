# Usher — Sistema de Gestión de Acomodadores

Aplicación web interna para gestionar voluntarios, congregaciones, zonas y asignaciones del Departamento de Acomodadores en Asambleas de Circuito.

---

## Tabla de contenido

1. [Descripción general](#descripción-general)
2. [Tecnologías](#tecnologías)
3. [Estructura del proyecto](#estructura-del-proyecto)
4. [Colecciones de Firestore](#colecciones-de-firestore)
5. [Configuración local (desarrollo)](#configuración-local-desarrollo)
6. [Variables de entorno](#variables-de-entorno)
7. [Despliegue en producción](#despliegue-en-producción)
   - [Opción A — Render.com (recomendada, gratuita)](#opción-a--rendercom-recomendada-gratuita)
   - [Opción B — VPS / servidor propio con Gunicorn + Nginx](#opción-b--vps--servidor-propio-con-gunicorn--nginx)
8. [Rutas de la aplicación](#rutas-de-la-aplicación)
9. [API REST interna](#api-rest-interna)
10. [Funcionalidades principales](#funcionalidades-principales)
11. [Seguridad](#seguridad)

---

## Descripción general

Usher es una aplicación Flask conectada a **Firebase Firestore** como base de datos. Permite:

- Registrar y editar **voluntarios** con su congregación, rol de capitán y número de celular.
- Administrar **congregaciones** y **zonas** del local de asamblea.
- Crear, editar y eliminar **asignaciones** de voluntarios a zonas y bloques horarios.
- Generar una **carta formal** lista para imprimir/guardar como PDF por cada asignación.
- Generar un **mensaje de WhatsApp** pre-formateado y enviarlo directamente desde el navegador.
- Ver un **Dashboard** con estadísticas: totales, zonas más activas y actividad mensual.

---

## Tecnologías

| Capa           | Tecnología                                               |
| -------------- | -------------------------------------------------------- |
| Backend        | Python 3.11+ · Flask 3.x                                 |
| Base de datos  | Google Firebase Firestore (NoSQL)                        |
| Auth Firebase  | `firebase-admin` 6.5+ (Service Account)                  |
| Frontend       | Jinja2 · Alpine.js 3.14 (local) · Tailwind CSS 3.4 (CDN) |
| Servidor prod. | Gunicorn                                                 |
| Env vars       | python-dotenv                                            |

---

## Estructura del proyecto

```
app/
├── app.py                  # Aplicación Flask: rutas, lógica, API REST
├── requirements.txt        # Dependencias Python
├── .env.example            # Plantilla de variables de entorno (sin secretos)
├── .env                    # Variables reales (NO subir a git)
├── key.json                # Credenciales Firebase Service Account (NO subir a git)
├── static/
│   ├── css/                # Estilos adicionales (si los hay)
│   └── js/
│       └── alpine.min.js   # Alpine.js 3.14.1 servido localmente
└── templates/
    ├── layout.html         # Base template: sidebar, topbar, scripts globales
    ├── index.html          # Dashboard con KPIs y gráficos
    ├── voluntarios.html    # CRUD de voluntarios
    ├── congregaciones.html # CRUD de congregaciones
    ├── zonas.html          # CRUD de zonas y sub-sectores
    └── asignaciones.html   # CRUD de asignaciones + carta PDF + mensaje WhatsApp
```

---

## Colecciones de Firestore

### `congregaciones`

| Campo    | Tipo   | Descripción               |
| -------- | ------ | ------------------------- |
| `nombre` | string | Nombre de la congregación |
| `ciudad` | string | Ciudad (opcional)         |

### `voluntarios`

| Campo             | Tipo    | Descripción                            |
| ----------------- | ------- | -------------------------------------- |
| `nombre`          | string  | Nombre completo                        |
| `congregacion_id` | string  | ID del documento en `congregaciones`   |
| `capitan`         | boolean | `true` si puede ser capitán de zona    |
| `celular`         | string  | Número venezolano (ej. `0412-1234567`) |
| `notas`           | string  | Observaciones adicionales (opcional)   |

### `zonas`

| Campo                | Tipo   | Descripción                                     |
| -------------------- | ------ | ----------------------------------------------- |
| `id_zona`            | string | Identificador corto de la zona (ej. `Z-1`)      |
| `nombre_descriptivo` | string | Descripción larga de la zona                    |
| `sub_sectores`       | string | Sub-sectores separados por coma (ej. `A, B, C`) |

### `asignaciones`

| Campo            | Tipo   | Descripción                                      |
| ---------------- | ------ | ------------------------------------------------ |
| `fecha`          | string | Fecha de la asamblea (`YYYY-MM-DD`)              |
| `voluntario_id`  | string | ID del voluntario asignado                       |
| `capitan_id`     | string | ID del voluntario capitán                        |
| `zona_id`        | string | ID de la zona                                    |
| `sub_sector`     | string | Sub-sector específico dentro de la zona          |
| `bloque_maestro` | string | Etiqueta del bloque horario (ej. `7:30 – 12:30`) |
| `horario`        | map    | `{ inicio: "07:30", fin: "12:30" }`              |
| `notas`          | string | Notas internas (opcional)                        |

---

## Configuración local (desarrollo)

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd app
```

### 2. Crear y activar entorno virtual

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Copia `.env.example` a `.env` y completa los valores:

```bash
cp .env.example .env
```

Edita `.env`:

```env
SECRET_KEY=una-clave-secreta-larga-y-aleatoria
FIREBASE_CREDENTIALS=key.json
```

### 5. Obtener credenciales de Firebase

1. Abre [Firebase Console](https://console.firebase.google.com).
2. Selecciona tu proyecto → **Configuración del proyecto** (ícono de engranaje).
3. Pestaña **Cuentas de servicio** → **Generar nueva clave privada**.
4. Descarga el archivo `.json` y guárdalo como `key.json` en la raíz del proyecto (`app/`).

> ⚠️ **Nunca** subas `key.json` ni `.env` al repositorio. Ya están en `.gitignore`.

### 6. Ejecutar en modo desarrollo

```bash
python app.py
```

La aplicación estará disponible en `http://localhost:5000`.

---

## Variables de entorno

| Variable               | Requerida | Descripción                                                                     |
| ---------------------- | --------- | ------------------------------------------------------------------------------- |
| `SECRET_KEY`           | Sí        | Clave para firmar sesiones Flask. Usa un valor largo y aleatorio en producción. |
| `FIREBASE_CREDENTIALS` | Sí        | Ruta al archivo JSON de Service Account de Firebase. Por defecto: `key.json`.   |

Para generar un `SECRET_KEY` seguro:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Despliegue en producción

### Opción A — Render.com (recomendada, gratuita)

[Render.com](https://render.com) permite desplegar aplicaciones Flask gratis con un plan Web Service.

#### Pasos

1. **Crea una cuenta** en [render.com](https://render.com) y conecta tu repositorio de GitHub/GitLab.

2. **Nuevo Web Service** → selecciona tu repositorio → rama `main`.

3. Configura el servicio:

   | Campo              | Valor                                                        |
   | ------------------ | ------------------------------------------------------------ |
   | **Runtime**        | `Python 3`                                                   |
   | **Build Command**  | `pip install -r requirements.txt`                            |
   | **Start Command**  | `gunicorn app:app --workers 2 --bind 0.0.0.0:$PORT`          |
   | **Root Directory** | `app` (si el repositorio tiene la carpeta `app/` en la raíz) |

4. En **Environment Variables** agrega:

   | Clave                  | Valor                                   |
   | ---------------------- | --------------------------------------- |
   | `SECRET_KEY`           | _(genera uno con el comando de arriba)_ |
   | `FIREBASE_CREDENTIALS` | `/etc/secrets/key.json`                 |

5. En **Secret Files** (panel izquierdo de Render → tu servicio → Secret Files):
   - **Filename**: `/etc/secrets/key.json`
   - **Contents**: pega el contenido completo de tu `key.json`

6. Haz clic en **Deploy**. Render instalará las dependencias y arrancará Gunicorn automáticamente.

> El plan gratuito de Render pone el servicio en reposo tras 15 min de inactividad. El primer request tras el reposo puede tardar ~30 s. Para uso continuo, usa el plan **Starter** (~$7/mes).

---

### Opción B — VPS / servidor propio con Gunicorn + Nginx

Usa esta opción si tienes un VPS (DigitalOcean, Hetzner, Contabo, etc.) con Ubuntu/Debian.

#### 1. Instalar dependencias del sistema

```bash
sudo apt update && sudo apt install -y python3 python3-pip python3-venv nginx git
```

#### 2. Subir el código al servidor

```bash
# Desde tu máquina local
scp -r ./app usuario@ip-del-servidor:/home/usuario/usher/
# O clonar directamente en el servidor:
git clone <url-del-repositorio> /home/usuario/usher
```

#### 3. Crear entorno virtual e instalar dependencias

```bash
cd /home/usuario/usher/app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
```

#### 4. Configurar variables de entorno

```bash
cp .env.example .env
nano .env   # Completa SECRET_KEY y FIREBASE_CREDENTIALS
```

Coloca `key.json` en `/home/usuario/usher/app/key.json` y asegúrate de que `FIREBASE_CREDENTIALS=key.json` apunte a esa ruta (o usa ruta absoluta).

#### 5. Crear servicio systemd

Crea el archivo `/etc/systemd/system/usher.service`:

```ini
[Unit]
Description=Usher — Sistema de Acomodadores
After=network.target

[Service]
User=usuario
WorkingDirectory=/home/usuario/usher/app
EnvironmentFile=/home/usuario/usher/app/.env
ExecStart=/home/usuario/usher/app/.venv/bin/gunicorn app:app \
          --workers 2 \
          --bind 127.0.0.1:8000 \
          --access-logfile /var/log/usher/access.log \
          --error-logfile /var/log/usher/error.log
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo mkdir -p /var/log/usher
sudo chown usuario:usuario /var/log/usher
sudo systemctl daemon-reload
sudo systemctl enable usher
sudo systemctl start usher
sudo systemctl status usher   # debe mostrar "active (running)"
```

#### 6. Configurar Nginx como proxy inverso

Crea `/etc/nginx/sites-available/usher`:

```nginx
server {
    listen 80;
    server_name tu-dominio.com;   # o la IP pública si no tienes dominio

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_read_timeout    60s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/usher /etc/nginx/sites-enabled/
sudo nginx -t          # verificar sintaxis
sudo systemctl reload nginx
```

#### 7. HTTPS con Certbot (recomendado)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d tu-dominio.com
```

Certbot renovará el certificado automáticamente.

---

## Rutas de la aplicación

| Método | Ruta              | Descripción                             |
| ------ | ----------------- | --------------------------------------- |
| `GET`  | `/`               | Dashboard con estadísticas generales    |
| `GET`  | `/voluntarios`    | Lista y gestión de voluntarios          |
| `GET`  | `/congregaciones` | Lista y gestión de congregaciones       |
| `GET`  | `/zonas`          | Lista y gestión de zonas y sub-sectores |
| `GET`  | `/asignaciones`   | Lista y gestión de asignaciones         |

---

## API REST interna

Todos los endpoints devuelven JSON. Se consumen desde el frontend con `fetch()`.

| Método   | Ruta                       | Descripción             |
| -------- | -------------------------- | ----------------------- |
| `POST`   | `/api/congregaciones`      | Crear congregación      |
| `PUT`    | `/api/congregaciones/<id>` | Actualizar congregación |
| `DELETE` | `/api/congregaciones/<id>` | Eliminar congregación   |
| `POST`   | `/api/voluntarios`         | Crear voluntario        |
| `PUT`    | `/api/voluntarios/<id>`    | Actualizar voluntario   |
| `DELETE` | `/api/voluntarios/<id>`    | Eliminar voluntario     |
| `POST`   | `/api/zonas`               | Crear zona              |
| `PUT`    | `/api/zonas/<id>`          | Actualizar zona         |
| `DELETE` | `/api/zonas/<id>`          | Eliminar zona           |
| `POST`   | `/api/asignaciones`        | Crear asignación        |
| `PUT`    | `/api/asignaciones/<id>`   | Actualizar asignación   |
| `DELETE` | `/api/asignaciones/<id>`   | Eliminar asignación     |

---

## Funcionalidades principales

### Dashboard (`/`)

- Tarjetas KPI: total congregaciones, voluntarios, capitanes, zonas y asignaciones.
- Barras de las 5 zonas con más asignaciones.
- Actividad mensual de los últimos 6 meses.
- Tabla de las 8 asignaciones más recientes.

### Voluntarios (`/voluntarios`)

- Tabla filtrable por nombre o congregación.
- Formulario de alta/edición con selector de congregación y rol de capitán.
- Indicador visual de capitanes.

### Congregaciones (`/congregaciones`)

- Tarjetas en cuadrícula.
- Alta y edición inline mediante modal.

### Zonas (`/zonas`)

- Tarjetas con ID de zona, nombre descriptivo y chips de sub-sectores.
- Alta y edición inline.

### Asignaciones (`/asignaciones`)

- Tabla filtrable por texto y por fecha.
- Formulario con selector de bloque horario predefinido (auto-completa inicio/fin).
- Por cada fila, 4 acciones al hacer hover:
  - **PDF** (rojo): abre ventana con carta formal lista para imprimir/guardar como PDF.
  - **WhatsApp** (verde): genera el mensaje pre-formateado y abre `wa.me` con el texto listo.
  - **Editar** (cian): abre el formulario de edición.
  - **Eliminar** (rojo): confirmación y borrado.

### Carta PDF

La carta se genera 100 % en el navegador (sin servidor) usando una ventana emergente con HTML/CSS y el diálogo de impresión del sistema. Incluye:

- Encabezado de la asamblea.
- Datos del voluntario y congregación.
- Cuadro con zona, sub-sector, horario y turno.
- Cuerpo formal e instrucciones.
- Nota P.D. con enlace a reunión previa.

### Mensaje WhatsApp

- Texto formateado con markdown de WhatsApp (`*negrita*`, `_cursiva_`).
- Detecta automáticamente el número del voluntario.
- Normaliza el número venezolano (`0412...` → `58412...`).
- Botones: Copiar al portapapeles · Abrir en WhatsApp.

---

## Seguridad

- `key.json` y `.env` están excluidos del repositorio vía `.gitignore`.
- `SECRET_KEY` debe ser un valor largo y aleatorio en producción (nunca usar el valor por defecto).
- Las credenciales de Firebase se leen del sistema de archivos en tiempo de ejecución, nunca se hardcodean.
- En producción, servir siempre bajo **HTTPS** (Certbot/Let's Encrypt o el TLS del proveedor de hosting).
- Firestore Security Rules: dado que la app usa un Service Account con privilegios totales, se recomienda que el acceso público a Firestore esté **deshabilitado** en las reglas de Firebase Console (solo lectura/escritura vía Admin SDK).
