import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, g, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "mastertools.db")

app = Flask(__name__)
app.secret_key = "cambia-esta-clave-por-una-segura-mastertools-2026"

COSTO_ENVIO = 5000  # envío fijo de ejemplo, en pesos


# ---------------------------------------------------------------------------
# Conexión a la base de datos
# ---------------------------------------------------------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Crea las tablas y carga datos de ejemplo si la base no existe."""
    nueva = not os.path.exists(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    with open(os.path.join(BASE_DIR, "schema.sql"), "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()

    if nueva:
        cur = conn.cursor()

        categorias = ["Taladros", "Amoladoras", "Soldadoras", "Compresores",
                      "Herramientas Manuales", "Accesorios", "Kits"]
        for c in categorias:
            cur.execute("INSERT OR IGNORE INTO categorias (nombre) VALUES (?)", (c,))

        marcas = ["Energy", "Bosch", "Stanley", "DeWalt", "Makita"]
        for m in marcas:
            cur.execute("INSERT OR IGNORE INTO marcas (nombre) VALUES (?)", (m,))

        conn.commit()

        def cat_id(nombre):
            return cur.execute("SELECT id FROM categorias WHERE nombre=?", (nombre,)).fetchone()[0]

        def marca_id(nombre):
            return cur.execute("SELECT id FROM marcas WHERE nombre=?", (nombre,)).fetchone()[0]

        productos = [
            ("Taladro Percutor Energy 850W", "TAL850W", "Taladro percutor de alta potencia, ideal para perforar madera, metal y mampostería.",
             85000, 15, "Taladros", "Energy", 1, 0),
            ("Amoladora Angular Energy 115mm", "AMO115", "Amoladora angular liviana, perfecta para corte y desbaste.",
             62000, 23, "Amoladoras", "Energy", 1, 0),
            ("Soldadora Inverter Energy 160A", "SOL160A", "Soldadora inverter portátil, electrodo revestido, fácil de transportar.",
             145000, 8, "Soldadoras", "Energy", 1, 0),
            ("Compresor Energy 24L 2HP", "COM24L", "Compresor de aire de 24 litros, ideal para taller e inflado.",
             135000, 12, "Compresores", "Energy", 1, 1),
            ("Kit Herramientas 129 Piezas", "KIT129", "Set completo de herramientas manuales para el hogar y el taller.",
             78000, 18, "Kits", "Stanley", 0, 0),
            ("Destornillador Set 6 piezas", "DES006", "Set de destornilladores de precisión, puntas variadas.",
             9500, 40, "Herramientas Manuales", "Stanley", 0, 0),
            ("Disco de corte 115mm x10", "DIS115", "Pack de 10 discos de corte para metal, compatibles con amoladoras de 115mm.",
             14500, 60, "Accesorios", "DeWalt", 0, 1),
            ("Taladro Atornillador Makita 18V", "TAL18V", "Taladro atornillador a batería, liviano y potente, incluye 2 baterías.",
             210000, 6, "Taladros", "Makita", 1, 0),
        ]
        for (nombre, sku, desc, precio, stock, cat, marca, destacado, oferta) in productos:
            precio_oferta = round(precio * 0.85, 0) if oferta else None
            cur.execute("""
                INSERT INTO productos (nombre, sku, descripcion, precio, stock, categoria_id,
                                        marca_id, destacado, oferta, precio_oferta)
                VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (nombre, sku, desc, precio, stock, cat_id(cat), marca_id(marca),
                  destacado, oferta, precio_oferta))

        # Usuario administrador por defecto
        cur.execute("""
            INSERT INTO usuarios (nombre, apellido, telefono, direccion, correo, password_hash, es_admin)
            VALUES (?,?,?,?,?,?,1)
        """, ("Maximiliano", "Admin", "+54 9 0000 0000", "Casa Central",
              "admin@mastertools.com", generate_password_hash("admin123")))

        conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Funciones auxiliares
# ---------------------------------------------------------------------------
def current_user():
    if "user_id" in session:
        db = get_db()
        return db.execute("SELECT * FROM usuarios WHERE id=?", (session["user_id"],)).fetchone()
    return None


def cart():
    return session.setdefault("cart", {})  # {producto_id_str: cantidad}


def cart_count():
    return sum(cart().values())


@app.context_processor
def inject_globals():
    return dict(usuario_actual=current_user(), cantidad_carrito=cart_count())


def login_required(view):
    from functools import wraps
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Debes iniciar sesión para continuar.", "error")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    from functools import wraps
    @wraps(view)
    def wrapped(*args, **kwargs):
        u = current_user()
        if not u or not u["es_admin"]:
            flash("No tienes permisos para acceder al panel.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def precio_final(p):
    return p["precio_oferta"] if p["oferta"] and p["precio_oferta"] else p["precio"]


# ---------------------------------------------------------------------------
# RUTAS PÚBLICAS
# ---------------------------------------------------------------------------
@app.route("/")
def home():
    db = get_db()
    destacados = db.execute(
        "SELECT * FROM productos WHERE destacado=1 AND activo=1 LIMIT 8"
    ).fetchall()
    categorias = db.execute("SELECT * FROM categorias").fetchall()
    return render_template("home.html", destacados=destacados, categorias=categorias,
                            precio_final=precio_final)


@app.route("/productos")
def productos():
    db = get_db()
    q = request.args.get("q", "").strip()
    cat = request.args.get("categoria", "")
    marca = request.args.get("marca", "")
    p_min = request.args.get("precio_min", "")
    p_max = request.args.get("precio_max", "")

    sql = """SELECT p.*, c.nombre AS categoria_nombre, m.nombre AS marca_nombre
             FROM productos p
             LEFT JOIN categorias c ON p.categoria_id = c.id
             LEFT JOIN marcas m ON p.marca_id = m.id
             WHERE p.activo = 1"""
    params = []
    if q:
        sql += " AND p.nombre LIKE ?"
        params.append(f"%{q}%")
    if cat:
        sql += " AND p.categoria_id = ?"
        params.append(cat)
    if marca:
        sql += " AND p.marca_id = ?"
        params.append(marca)
    if p_min:
        sql += " AND p.precio >= ?"
        params.append(p_min)
    if p_max:
        sql += " AND p.precio <= ?"
        params.append(p_max)
    sql += " ORDER BY p.id DESC"

    lista = db.execute(sql, params).fetchall()
    categorias = db.execute("SELECT * FROM categorias").fetchall()
    marcas = db.execute("SELECT * FROM marcas").fetchall()
    return render_template("productos.html", productos=lista, categorias=categorias,
                            marcas=marcas, filtros=request.args, precio_final=precio_final)


@app.route("/producto/<int:producto_id>")
def detalle_producto(producto_id):
    db = get_db()
    p = db.execute("SELECT * FROM productos WHERE id=?", (producto_id,)).fetchone()
    if not p:
        flash("Producto no encontrado.", "error")
        return redirect(url_for("productos"))
    return render_template("detalle_producto.html", p=p, precio_final=precio_final)


@app.route("/ofertas")
def ofertas():
    db = get_db()
    lista = db.execute("SELECT * FROM productos WHERE oferta=1 AND activo=1").fetchall()
    return render_template("ofertas.html", productos=lista, precio_final=precio_final)


@app.route("/categorias")
def categorias_page():
    db = get_db()
    cats = db.execute("SELECT * FROM categorias").fetchall()
    return render_template("categorias.html", categorias=cats)


# --- Carrito ---------------------------------------------------------------
@app.route("/carrito/agregar/<int:producto_id>", methods=["POST"])
def agregar_carrito(producto_id):
    c = cart()
    c[str(producto_id)] = c.get(str(producto_id), 0) + int(request.form.get("cantidad", 1))
    session.modified = True
    flash("Producto agregado al carrito.", "success")
    return redirect(request.referrer or url_for("productos"))


@app.route("/carrito/actualizar/<int:producto_id>", methods=["POST"])
def actualizar_carrito(producto_id):
    c = cart()
    cantidad = int(request.form.get("cantidad", 1))
    if cantidad <= 0:
        c.pop(str(producto_id), None)
    else:
        c[str(producto_id)] = cantidad
    session.modified = True
    return redirect(url_for("ver_carrito"))


@app.route("/carrito/eliminar/<int:producto_id>")
def eliminar_carrito(producto_id):
    c = cart()
    c.pop(str(producto_id), None)
    session.modified = True
    return redirect(url_for("ver_carrito"))


@app.route("/carrito")
def ver_carrito():
    db = get_db()
    c = cart()
    items = []
    subtotal = 0
    for pid, cantidad in c.items():
        p = db.execute("SELECT * FROM productos WHERE id=?", (pid,)).fetchone()
        if p:
            precio = precio_final(p)
            sub = precio * cantidad
            subtotal += sub
            items.append({"producto": p, "cantidad": cantidad, "subtotal": sub, "precio": precio})
    envio = COSTO_ENVIO if items else 0
    total = subtotal + envio
    return render_template("carrito.html", items=items, subtotal=subtotal, envio=envio, total=total)


@app.route("/carrito/enviar", methods=["POST"])
@login_required
def enviar_pedido():
    db = get_db()
    c = cart()
    if not c:
        flash("Tu carrito está vacío.", "error")
        return redirect(url_for("ver_carrito"))

    subtotal = 0
    detalles = []
    for pid, cantidad in c.items():
        p = db.execute("SELECT * FROM productos WHERE id=?", (pid,)).fetchone()
        if p:
            precio = precio_final(p)
            subtotal += precio * cantidad
            detalles.append((p, cantidad, precio))

    envio = COSTO_ENVIO
    total = subtotal + envio

    cur = db.execute(
        "INSERT INTO pedidos (usuario_id, estado, subtotal, envio, total) VALUES (?,?,?,?,?)",
        (session["user_id"], "Pendiente", subtotal, envio, total)
    )
    pedido_id = cur.lastrowid
    for p, cantidad, precio in detalles:
        db.execute("""INSERT INTO pedido_items (pedido_id, producto_id, nombre_producto, cantidad, precio_unitario)
                      VALUES (?,?,?,?,?)""", (pedido_id, p["id"], p["nombre"], cantidad, precio))
        nuevo_stock = max(p["stock"] - cantidad, 0)
        db.execute("UPDATE productos SET stock=? WHERE id=?", (nuevo_stock, p["id"]))
    db.commit()

    session["cart"] = {}
    flash(f"¡Pedido #{pedido_id} enviado con éxito!", "success")
    return redirect(url_for("historial_pedidos"))


# --- Contacto ----------------------------------------------------------------
@app.route("/contacto", methods=["GET", "POST"])
def contacto():
    if request.method == "POST":
        db = get_db()
        db.execute("INSERT INTO mensajes_contacto (nombre, correo, mensaje) VALUES (?,?,?)",
                   (request.form["nombre"], request.form["correo"], request.form["mensaje"]))
        db.commit()
        flash("Mensaje enviado. ¡Gracias por contactarnos!", "success")
        return redirect(url_for("contacto"))
    return render_template("contacto.html")


# --- Cuenta de usuario -------------------------------------------------------
@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        db = get_db()
        existe = db.execute("SELECT id FROM usuarios WHERE correo=?", (request.form["correo"],)).fetchone()
        if existe:
            flash("Ya existe una cuenta con ese correo.", "error")
            return redirect(url_for("registro"))
        db.execute("""INSERT INTO usuarios (nombre, apellido, telefono, direccion, correo, password_hash)
                      VALUES (?,?,?,?,?,?)""",
                   (request.form["nombre"], request.form["apellido"], request.form.get("telefono", ""),
                    request.form.get("direccion", ""), request.form["correo"],
                    generate_password_hash(request.form["password"])))
        db.commit()
        flash("Cuenta creada con éxito. Ahora puedes iniciar sesión.", "success")
        return redirect(url_for("login"))
    return render_template("registro.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        db = get_db()
        user = db.execute("SELECT * FROM usuarios WHERE correo=?", (request.form["correo"],)).fetchone()
        if user and check_password_hash(user["password_hash"], request.form["password"]):
            session["user_id"] = user["id"]
            flash(f"¡Bienvenido, {user['nombre']}!", "success")
            if user["es_admin"]:
                return redirect(url_for("admin_dashboard"))
            return redirect(request.args.get("next") or url_for("home"))
        flash("Correo o contraseña incorrectos.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada.", "success")
    return redirect(url_for("home"))


@app.route("/mi-cuenta/pedidos")
@login_required
def historial_pedidos():
    db = get_db()
    pedidos = db.execute("SELECT * FROM pedidos WHERE usuario_id=? ORDER BY fecha DESC",
                          (session["user_id"],)).fetchall()
    return render_template("historial_pedidos.html", pedidos=pedidos)


# ---------------------------------------------------------------------------
# PANEL DE ADMINISTRADOR
# ---------------------------------------------------------------------------
@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_db()
    ventas = db.execute("SELECT COALESCE(SUM(total),0) AS t FROM pedidos").fetchone()["t"]
    pedidos = db.execute("SELECT COUNT(*) AS c FROM pedidos").fetchone()["c"]
    productos_count = db.execute("SELECT COUNT(*) AS c FROM productos").fetchone()["c"]
    clientes = db.execute("SELECT COUNT(*) AS c FROM usuarios WHERE es_admin=0").fetchone()["c"]
    ultimos_productos = db.execute("""SELECT p.*, c.nombre AS categoria_nombre, m.nombre AS marca_nombre
                                       FROM productos p
                                       LEFT JOIN categorias c ON p.categoria_id=c.id
                                       LEFT JOIN marcas m ON p.marca_id=m.id
                                       ORDER BY p.id DESC LIMIT 5""").fetchall()
    return render_template("admin/dashboard.html", ventas=ventas, pedidos=pedidos,
                            productos_count=productos_count, clientes=clientes,
                            ultimos_productos=ultimos_productos)


@app.route("/admin/productos")
@admin_required
def admin_productos():
    db = get_db()
    lista = db.execute("""SELECT p.*, c.nombre AS categoria_nombre, m.nombre AS marca_nombre
                           FROM productos p
                           LEFT JOIN categorias c ON p.categoria_id=c.id
                           LEFT JOIN marcas m ON p.marca_id=m.id
                           ORDER BY p.id DESC""").fetchall()
    return render_template("admin/productos.html", productos=lista)


@app.route("/admin/productos/nuevo", methods=["GET", "POST"])
@admin_required
def admin_nuevo_producto():
    db = get_db()
    if request.method == "POST":
        db.execute("""INSERT INTO productos (nombre, sku, descripcion, precio, stock, categoria_id,
                                              marca_id, destacado, oferta, precio_oferta, activo)
                      VALUES (?,?,?,?,?,?,?,?,?,?,1)""",
                   (request.form["nombre"], request.form["sku"], request.form.get("descripcion", ""),
                    float(request.form["precio"]), int(request.form["stock"]),
                    request.form.get("categoria_id") or None, request.form.get("marca_id") or None,
                    1 if request.form.get("destacado") else 0,
                    1 if request.form.get("oferta") else 0,
                    request.form.get("precio_oferta") or None))
        db.commit()
        flash("Producto agregado.", "success")
        return redirect(url_for("admin_productos"))
    categorias = db.execute("SELECT * FROM categorias").fetchall()
    marcas = db.execute("SELECT * FROM marcas").fetchall()
    return render_template("admin/form_producto.html", categorias=categorias, marcas=marcas, p=None)


@app.route("/admin/productos/<int:producto_id>/editar", methods=["GET", "POST"])
@admin_required
def admin_editar_producto(producto_id):
    db = get_db()
    if request.method == "POST":
        db.execute("""UPDATE productos SET nombre=?, sku=?, descripcion=?, precio=?, stock=?,
                      categoria_id=?, marca_id=?, destacado=?, oferta=?, precio_oferta=?, activo=?
                      WHERE id=?""",
                   (request.form["nombre"], request.form["sku"], request.form.get("descripcion", ""),
                    float(request.form["precio"]), int(request.form["stock"]),
                    request.form.get("categoria_id") or None, request.form.get("marca_id") or None,
                    1 if request.form.get("destacado") else 0,
                    1 if request.form.get("oferta") else 0,
                    request.form.get("precio_oferta") or None,
                    1 if request.form.get("activo") else 0,
                    producto_id))
        db.commit()
        flash("Producto actualizado.", "success")
        return redirect(url_for("admin_productos"))
    p = db.execute("SELECT * FROM productos WHERE id=?", (producto_id,)).fetchone()
    categorias = db.execute("SELECT * FROM categorias").fetchall()
    marcas = db.execute("SELECT * FROM marcas").fetchall()
    return render_template("admin/form_producto.html", categorias=categorias, marcas=marcas, p=p)


@app.route("/admin/productos/<int:producto_id>/eliminar")
@admin_required
def admin_eliminar_producto(producto_id):
    db = get_db()
    db.execute("DELETE FROM productos WHERE id=?", (producto_id,))
    db.commit()
    flash("Producto eliminado.", "success")
    return redirect(url_for("admin_productos"))


@app.route("/admin/categorias", methods=["GET", "POST"])
@admin_required
def admin_categorias():
    db = get_db()
    if request.method == "POST":
        db.execute("INSERT OR IGNORE INTO categorias (nombre) VALUES (?)", (request.form["nombre"],))
        db.commit()
        flash("Categoría agregada.", "success")
        return redirect(url_for("admin_categorias"))
    cats = db.execute("SELECT * FROM categorias").fetchall()
    return render_template("admin/categorias.html", categorias=cats)


@app.route("/admin/categorias/<int:cat_id>/eliminar")
@admin_required
def admin_eliminar_categoria(cat_id):
    db = get_db()
    db.execute("DELETE FROM categorias WHERE id=?", (cat_id,))
    db.commit()
    flash("Categoría eliminada.", "success")
    return redirect(url_for("admin_categorias"))


@app.route("/admin/marcas", methods=["GET", "POST"])
@admin_required
def admin_marcas():
    db = get_db()
    if request.method == "POST":
        db.execute("INSERT OR IGNORE INTO marcas (nombre) VALUES (?)", (request.form["nombre"],))
        db.commit()
        flash("Marca agregada.", "success")
        return redirect(url_for("admin_marcas"))
    marcas = db.execute("SELECT * FROM marcas").fetchall()
    return render_template("admin/marcas.html", marcas=marcas)


@app.route("/admin/marcas/<int:marca_id>/eliminar")
@admin_required
def admin_eliminar_marca(marca_id):
    db = get_db()
    db.execute("DELETE FROM marcas WHERE id=?", (marca_id,))
    db.commit()
    flash("Marca eliminada.", "success")
    return redirect(url_for("admin_marcas"))


@app.route("/admin/pedidos")
@admin_required
def admin_pedidos():
    db = get_db()
    pedidos = db.execute("""SELECT pe.*, u.nombre AS cliente_nombre, u.apellido AS cliente_apellido
                             FROM pedidos pe LEFT JOIN usuarios u ON pe.usuario_id = u.id
                             ORDER BY pe.fecha DESC""").fetchall()
    return render_template("admin/pedidos.html", pedidos=pedidos)


@app.route("/admin/pedidos/<int:pedido_id>")
@admin_required
def admin_detalle_pedido(pedido_id):
    db = get_db()
    pedido = db.execute("""SELECT pe.*, u.nombre AS cliente_nombre, u.apellido AS cliente_apellido,
                                   u.correo AS cliente_correo
                            FROM pedidos pe LEFT JOIN usuarios u ON pe.usuario_id = u.id
                            WHERE pe.id=?""", (pedido_id,)).fetchone()
    items = db.execute("SELECT * FROM pedido_items WHERE pedido_id=?", (pedido_id,)).fetchall()
    return render_template("admin/detalle_pedido.html", pedido=pedido, items=items)


@app.route("/admin/pedidos/<int:pedido_id>/estado", methods=["POST"])
@admin_required
def admin_actualizar_estado_pedido(pedido_id):
    db = get_db()
    db.execute("UPDATE pedidos SET estado=? WHERE id=?", (request.form["estado"], pedido_id))
    db.commit()
    flash("Estado del pedido actualizado.", "success")
    return redirect(url_for("admin_detalle_pedido", pedido_id=pedido_id))


@app.route("/admin/clientes")
@admin_required
def admin_clientes():
    db = get_db()
    clientes = db.execute("SELECT * FROM usuarios WHERE es_admin=0 ORDER BY id DESC").fetchall()
    return render_template("admin/clientes.html", clientes=clientes)


@app.route("/admin/mensajes")
@admin_required
def admin_mensajes():
    db = get_db()
    mensajes = db.execute("SELECT * FROM mensajes_contacto ORDER BY fecha DESC").fetchall()
    return render_template("admin/mensajes.html", mensajes=mensajes)


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
else:
    init_db()
