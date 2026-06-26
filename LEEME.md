# MasterTools — Tienda online + Panel de administración

Esto es una web completa y funcional para tu negocio de herramientas, con:
- Tienda online (Inicio, Productos, Ofertas, Categorías, Carrito, Contacto, Mi cuenta).
- Base de datos propia (se crea sola, no necesitas instalar nada extra de bases de datos).
- Panel de administración para gestionar productos, categorías, marcas, pedidos y clientes.

Todo está hecho con **software 100% gratuito y de código abierto** (Python + Flask + SQLite), sin licencias que pagar.

## 1. Qué necesitas instalar (una sola vez)

Solo necesitas **Python** (gratis): https://www.python.org/downloads/
Al instalarlo en Windows, marcá la casilla "Add Python to PATH".

## 2. Cómo poner en marcha la web en tu computadora

1. Descomprimí esta carpeta donde quieras (por ejemplo, en el Escritorio).
2. Abrí una terminal / símbolo del sistema dentro de la carpeta `mastertools`.
   - En Windows: abrí la carpeta, hacé clic con el botón derecho dentro de ella y elegí "Abrir en Terminal".
3. Instalá las dependencias (una sola vez):
   ```
   pip install -r requirements.txt
   ```
4. Iniciá la web:
   ```
   python app.py
   ```
5. Abrí el navegador y entrá a: **http://localhost:5000**

¡Listo! La primera vez que la iniciás, se crea automáticamente la base de datos con productos de ejemplo (los mismos que tenías en tu panel).

## 3. Usuario administrador de prueba

- Correo: `admin@mastertools.com`
- Contraseña: `admin123`

Con esta cuenta entrás al **Panel de administración** (botón "Panel admin" arriba a la derecha, o yendo a `http://localhost:5000/admin`).
**Importante:** cambiá esta contraseña por una propia apenas puedas (creando otro admin desde la base o pidiéndole a un desarrollador que la actualice).

## 4. Qué podés hacer desde el panel admin

- Ver ventas totales, pedidos, productos y clientes (Dashboard).
- Agregar, editar, eliminar y desactivar productos (con precio, stock, oferta, destacado).
- Crear y eliminar categorías y marcas.
- Ver todos los pedidos de tus clientes y cambiar su estado (Pendiente, Enviado, Entregado, Cancelado).
- Ver la lista de clientes registrados.
- Ver los mensajes que te dejen desde el formulario de Contacto.

## 5. Cómo publicar la web en internet (para que cualquiera la vea, no solo tu PC)

Esta versión funciona en tu computadora. Para que esté disponible en internet con tu propio dominio, lo más simple y **gratuito/económico** es subirla a un servicio como:
- Render.com (tiene plan gratuito)
- Railway.app
- PythonAnywhere

Cualquiera de estos servicios te permite subir esta misma carpeta y tener la web funcionando 24/7 con una dirección propia. Si no tenés conocimientos técnicos para ese paso, te recomiendo pedirle ayuda puntual a alguien (o a mí) solo para esa parte de "subir la web a internet" — el resto (diseño, base de datos, funcionalidades) ya está listo.

## 6. Datos importantes a personalizar

Antes de publicarla, recordá cambiar en `app.py` y en las plantillas:
- Tu WhatsApp, teléfono, dirección y horarios reales (archivo `templates/contacto.html`).
- El costo de envío (`COSTO_ENVIO` en `app.py`).
- Las imágenes de los productos (actualmente se muestra un ícono 🛠️ en lugar de foto real — se puede reemplazar fácilmente subiendo fotos a `static/img` y ajustando las plantillas).
- La clave secreta `app.secret_key` en `app.py` (poné cualquier texto largo y aleatorio).

## 7. Estructura de archivos

```
mastertools/
├── app.py                -> toda la lógica de la web (rutas, carrito, login, panel admin)
├── schema.sql            -> estructura de la base de datos
├── requirements.txt      -> lista de programas necesarios (Flask)
├── mastertools.db        -> se crea solo al iniciar (tu base de datos real)
├── static/css/style.css  -> diseño visual (colores, estilos)
└── templates/            -> todas las páginas (HTML)
    └── admin/            -> páginas del panel de administración
```

Cualquier consulta sobre cómo modificar textos, colores, precios o agregar funciones nuevas, podés volver a preguntarme.
