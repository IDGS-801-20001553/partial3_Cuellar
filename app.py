from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from config import DevelopmentConfig
from models import db, Cliente, Usuario
import form
import os
import datetime

app = Flask(__name__)
app.config.from_object('config.DevelopmentConfig')
csrf = CSRFProtect(app)

PEDIDOS_FILE = "pedidos.txt"


# Configuración de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index'  

# Clase de usuario para Flask-Login
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

# Cargador de usuario 
@login_manager.user_loader
def load_user(user_id):
    usuario = Usuario.query.get(int(user_id))
    if usuario:
        return User(id=usuario.id, username=usuario.username)
    return None

# Ruta de inicio de sesión
@app.route("/", methods=["GET", "POST"])
def index():
    csrf_token = generate_csrf()
    form_login = form.LoginForm(request.form)
    if request.method == "POST" and form_login.validate():
        username = form_login.username.data
        password = form_login.password.data

        usuario = Usuario.query.filter_by(username=username).first()
        if usuario and usuario.check_password(password): 
            user = User(id=usuario.id, username=usuario.username)
            login_user(user)
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('pedidos'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')

    return render_template("index.html", form=form_login, csrf_token=csrf_token)

# Ruta de cierre de sesión
@app.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    csrf_token = generate_csrf()
    logout_user()
    flash('Sesión cerrada correctamente', 'success')
    return redirect(url_for("index"))

# Rutas protegida
def leer_pedidos():
    pedidos = []
    if os.path.exists(PEDIDOS_FILE):
        with open(PEDIDOS_FILE, "r") as f:
            for line in f:
                tamaño, ingredientes, cantidad, subtotal = line.strip().split("|")
                pedidos.append({
                    "tamaño": tamaño,
                    "ingredientes": ingredientes,
                    "cantidad": cantidad,
                    "subtotal": subtotal
                })
    return pedidos


def guardar_pedido(tamaño, ingredientes, cantidad, subtotal):
    with open(PEDIDOS_FILE, "a") as f:
        f.write(f"{tamaño}|{ingredientes}|{cantidad}|{subtotal}\n")


def eliminar_ultimo_pedido():
    if os.path.exists(PEDIDOS_FILE):
        with open(PEDIDOS_FILE, "r") as f:
            lines = f.readlines()
        if lines:
            print(f"Eliminando: {lines[-1]}")  
            lines.pop()  
            with open(PEDIDOS_FILE, "w") as f:
                f.writelines(lines)


def calcular_total():
    pedidos = leer_pedidos()
    total = sum(float(pedido["subtotal"]) for pedido in pedidos)
    return total


def guardar_datos_cliente(nombre, direccion, telefono):
    session["nombre_cliente"] = nombre
    session["direccion_cliente"] = direccion
    session["telefono_cliente"] = telefono


@app.route("/pedidos", methods=["GET", "POST"])
@login_required
def pedidos():
    form_pedido = form.PedidoForm(request.form)
    pedidos = leer_pedidos()
    csrf_token = generate_csrf()

    
    nombre_cliente = session.get("nombre_cliente", "")
    direccion_cliente = session.get("direccion_cliente", "")
    telefono_cliente = session.get("telefono_cliente", "")

    if request.method == "POST" and form_pedido.validate():

        if not nombre_cliente and not direccion_cliente and not telefono_cliente:
            nombre_cliente = form_pedido.nombre.data
            direccion_cliente = form_pedido.direccion.data
            telefono_cliente = form_pedido.telefono.data

            session["nombre_cliente"] = nombre_cliente
            session["direccion_cliente"] = direccion_cliente
            session["telefono_cliente"] = telefono_cliente

        tamaño = form_pedido.tamaño.data
        ingredientes = []

        if form_pedido.jamon.data:
            ingredientes.append("Jamón")
        if form_pedido.pina.data:
            ingredientes.append("Piña")
        if form_pedido.champiñones.data:
            ingredientes.append("Champiñones")
        
        cantidad = form_pedido.cantidad.data
        
        precios = {"chica": 40, "mediana": 80, "grande": 120}
        precio_base = precios.get(tamaño, 0)
        precio_ingredientes = len(ingredientes) * 10
        subtotal = (precio_base + precio_ingredientes) * int(cantidad)
        
        guardar_pedido(tamaño, ",".join(ingredientes), cantidad, subtotal)
        flash("Pedido agregado correctamente")
        return redirect(url_for("pedidos"))

    if request.method == "POST" and "quitar" in request.form:
        eliminar_ultimo_pedido()
        flash("Última pizza eliminada")
        pedidos = leer_pedidos()  
        return redirect(url_for("pedidos"))

    if request.method == "POST" and "terminar" in request.form:
        total = calcular_total()
        flash(f"El total del pedido es: ${total:.2f}")

        if nombre_cliente and direccion_cliente and telefono_cliente:
            cliente = Cliente(
                nombre=nombre_cliente,
                direccion=direccion_cliente,
                telefono=telefono_cliente,
                fecha_pedido=datetime.datetime.now(),
                total_pagar=total
            )
            db.session.add(cliente)
            db.session.commit()

            with open(PEDIDOS_FILE, "w"):
                pass 

            # Limpiar los datos del formulario y la sesión
            session.pop("nombre_cliente", None)
            session.pop("direccion_cliente", None)
            session.pop("telefono_cliente", None)

            flash("Pedido finalizado correctamente")
            return redirect(url_for("pedidos"))
        else:
            flash("Por favor complete todos los campos del cliente.")
            return redirect(url_for("pedidos"))

    
    resultados = session.pop("resultados", None)
    total_ventas = session.pop("total_ventas", None)

    return render_template("pedidos.html", form=form_pedido, pedidos=pedidos, csrf_token=csrf_token, 
                        nombre_cliente=nombre_cliente, direccion_cliente=direccion_cliente, telefono_cliente=telefono_cliente,
                        resultados=resultados, total_ventas=total_ventas)


@app.route("/buscar_ventas", methods=["POST"])
def buscar_ventas():
    tipo_fecha = request.form.get("tipo_fecha")
    fecha_seleccionada = request.form.get("fecha")

    resultados = []
    total_ventas = 0

    if tipo_fecha:
        if tipo_fecha == "dia":
            if fecha_seleccionada:
                fecha_obj = datetime.datetime.strptime(fecha_seleccionada, "%Y-%m-%d")
                resultados = Cliente.query.filter(
                    db.func.date(Cliente.fecha_pedido) == fecha_obj.date()
                ).all()
            else:
                fecha_actual = datetime.datetime.now().date()
                resultados = Cliente.query.filter(
                    db.func.date(Cliente.fecha_pedido) == fecha_actual
                ).all()
        elif tipo_fecha == "mes":
            if fecha_seleccionada:
                fecha_obj = datetime.datetime.strptime(fecha_seleccionada, "%Y-%m-%d")
                resultados = Cliente.query.filter(
                    db.extract("year", Cliente.fecha_pedido) == fecha_obj.year,
                    db.extract("month", Cliente.fecha_pedido) == fecha_obj.month
                ).all()
            else:
                fecha_actual = datetime.datetime.now()
                resultados = Cliente.query.filter(
                    db.extract("year", Cliente.fecha_pedido) == fecha_actual.year,
                    db.extract("month", Cliente.fecha_pedido) == fecha_actual.month
                ).all()
        elif tipo_fecha == "fecha_especifica" and fecha_seleccionada:
            fecha_obj = datetime.datetime.strptime(fecha_seleccionada, "%Y-%m-%d")
            resultados = Cliente.query.filter(
                db.func.date(Cliente.fecha_pedido) == fecha_obj.date()
            ).all()

    total_ventas = sum(venta.total_pagar for venta in resultados)

    session["resultados"] = [{"nombre": venta.nombre, "total_pagar": venta.total_pagar} for venta in resultados]
    session["total_ventas"] = total_ventas

    return redirect(url_for("pedidos"))

if __name__ == '__main__':
    csrf.init_app(app)
    db.init_app(app)
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=3000)