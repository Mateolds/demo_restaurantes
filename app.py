from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
app.secret_key = 'clave_secreta_super_segura'

# ✅ CONEXIÓN CORREGIDA (RAILWAY)
DB_CONFIG = {
    'host': 'switchback.proxy.rlwy.net',
    'port': 42048,
    'user': 'root',
    'password': 'SLFGZoiMCSwMtoUzgvnLFHneBRiEqfxs',
    'database': 'gestion_mesas'
}

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def calculate_status(total, occupied):
    if total <= 0:
        return 'Sin configurar'
    free = total - occupied
    ratio = free / total
    if free <= 0:
        return 'Lleno'
    if ratio <= 0.25:
        return 'Pocas mesas'
    return 'Disponible'


def calculate_wait(status):
    if status == 'Lleno':
        return '20-30 min'
    if status == 'Pocas mesas':
        return '10-15 min'
    if status == 'Disponible':
        return '0-5 min'
    return 'N/A'


# ── LOGIN ADMIN ────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Si ya esta logueado como admin, ir al panel
    if 'user' in session:
        return redirect(url_for('admin'))
    # Si hay sesion de cliente activa, limpiarla
    if 'cliente_id' in session:
        session.pop('cliente_id', None)
        session.pop('cliente_nombre', None)
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE username=%s AND password=%s", (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user:
            # Limpiar sesion de cliente si estaba activa
            session.pop('cliente_id', None)
            session.pop('cliente_nombre', None)
            session['user'] = user['username']
            return redirect('/admin')
        else:
            flash('Credenciales incorrectas.', 'error')
    return render_template('login.html')


# ── LOGOUT ADMIN ───────────────────────────────────────────────
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# ── REGISTRO CLIENTE ───────────────────────────────────────────
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre   = request.form['nombre']
        email    = request.form['email']
        password = request.form['password']

        try:
            conn   = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id FROM clientes WHERE email = %s", (email,))
            existe = cursor.fetchone()
            if existe:
                flash('Ya existe una cuenta con ese email.', 'error')
                return redirect(url_for('registro'))

            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO clientes (nombre, email, password) VALUES (%s, %s, %s)",
                (nombre, email, password)
            )
            conn.commit()
            flash('Cuenta creada exitosamente. Ahora inicia sesion.', 'success')
            return redirect(url_for('login_cliente'))
        except Error as e:
            flash(f'Error al registrar: {e}', 'error')
        finally:
            try:
                cursor.close()
                conn.close()
            except Exception:
                pass

    return render_template('registro.html')


# ── LOGIN CLIENTE ──────────────────────────────────────────────
@app.route('/login-cliente', methods=['GET', 'POST'])
def login_cliente():
    # Si ya esta logueado como cliente, ir al inicio
    if 'cliente_id' in session:
        return redirect(url_for('index'))
    # Si hay sesion de admin activa, limpiarla para no mezclar
    if 'user' in session:
        session.pop('user', None)
    if request.method == 'POST':
        email    = request.form['email']
        password = request.form['password']

        try:
            conn   = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM clientes WHERE email=%s AND password=%s", (email, password))
            cliente = cursor.fetchone()
            cursor.close()
            conn.close()

            if cliente:
                # Limpiar sesion de admin si estaba activa
                session.pop('user', None)
                session['cliente_id']     = cliente['id']
                session['cliente_nombre'] = cliente['nombre']
                return redirect(url_for('index'))
            else:
                flash('Email o contrasena incorrectos.', 'error')
        except Error as e:
            flash(f'Error: {e}', 'error')

    return render_template('login_cliente.html')


# ── LOGOUT CLIENTE ─────────────────────────────────────────────
@app.route('/logout-cliente')
def logout_cliente():
    session.clear()
    return redirect(url_for('login_cliente'))


# ── VISTA CLIENTE (HOME) ───────────────────────────────────────
@app.route('/')
def index():
    restaurantes = []
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM restaurantes ORDER BY nombre ASC')
        restaurantes = cursor.fetchall()
        for r in restaurantes:
            r['mesas_disponibles'] = max(r['total_mesas'] - r['mesas_ocupadas'], 0)
            r['estado']            = calculate_status(r['total_mesas'], r['mesas_ocupadas'])
            r['tiempo_espera']     = calculate_wait(r['estado'])
            r['ocupacion']         = round((r['mesas_ocupadas'] / r['total_mesas']) * 100, 1) if r['total_mesas'] else 0
    except Error as e:
        flash(f'Error de conexion: {e}', 'error')
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass
    return render_template('index.html', restaurantes=restaurantes)


# ── MIS RESERVAS (CLIENTE) ─────────────────────────────────────
@app.route('/mis-reservas')
def mis_reservas():
    if 'cliente_id' not in session:
        flash('Debes iniciar sesion para ver tus reservas.', 'error')
        return redirect(url_for('login_cliente'))

    reservas = []
    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            '''SELECT r.id, r.fecha_hora, r.personas, r.estado,
                      res.nombre AS restaurante_nombre, res.ciudad
               FROM reservas r
               JOIN restaurantes res ON r.restaurante_id = res.id
               WHERE r.cliente_id = %s
               ORDER BY r.fecha_hora DESC''',
            (session['cliente_id'],)
        )
        reservas = cursor.fetchall()
    except Error as e:
        flash(f'Error: {e}', 'error')
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass

    return render_template('mis_reservas.html', reservas=reservas)


# ── RESERVAR ───────────────────────────────────────────────────
@app.route('/reservar', methods=['POST'])
def reservar():
    if 'cliente_id' not in session:
        flash('Debes iniciar sesion para hacer una reserva.', 'error')
        return redirect(url_for('login_cliente'))

    restaurante_id = int(request.form['restaurante_id'])
    fecha_hora     = request.form['fecha_hora']
    personas       = int(request.form['personas'])
    cliente_id     = session['cliente_id']

    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT nombre, total_mesas, mesas_ocupadas FROM restaurantes WHERE id = %s', (restaurante_id,))
        restaurante = cursor.fetchone()

        if not restaurante:
            flash('Restaurante no encontrado.', 'error')
            return redirect(url_for('index'))

        if restaurante['mesas_ocupadas'] >= restaurante['total_mesas']:
            flash(f'Lo sentimos, {restaurante["nombre"]} no tiene mesas disponibles ahora mismo.', 'error')
            return redirect(url_for('index'))

        nombre_rest = restaurante['nombre']
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO reservas (cliente_id, restaurante_id, fecha_hora, personas) VALUES (%s, %s, %s, %s)',
            (cliente_id, restaurante_id, fecha_hora, personas)
        )
        cursor.execute(
            'UPDATE restaurantes SET mesas_ocupadas = mesas_ocupadas + 1 WHERE id = %s',
            (restaurante_id,)
        )
        conn.commit()
        flash(f'Reserva confirmada en {nombre_rest}. Tu mesa esta apartada! ', 'success')

    except Error as e:
        flash(f'No se pudo crear la reserva: {e}', 'error')
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass

    return redirect(url_for('mis_reservas'))


# ── CANCELAR RESERVA (CLIENTE) ─────────────────────────────────
@app.route('/cancelar-mi-reserva/<int:reserva_id>', methods=['POST'])
def cancelar_mi_reserva(reserva_id):
    if 'cliente_id' not in session:
        return redirect(url_for('login_cliente'))

    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT restaurante_id FROM reservas WHERE id = %s AND cliente_id = %s AND estado = 'pendiente'",
            (reserva_id, session['cliente_id'])
        )
        reserva = cursor.fetchone()

        if not reserva:
            flash('Reserva no encontrada o ya cancelada.', 'error')
            return redirect(url_for('mis_reservas'))

        cursor = conn.cursor()
        cursor.execute("UPDATE reservas SET estado = 'cancelada' WHERE id = %s", (reserva_id,))
        cursor.execute(
            'UPDATE restaurantes SET mesas_ocupadas = GREATEST(mesas_ocupadas - 1, 0) WHERE id = %s',
            (reserva['restaurante_id'],)
        )
        conn.commit()
        flash('Reserva cancelada. La mesa quedo disponible.', 'success')

    except Error as e:
        flash(f'Error al cancelar: {e}', 'error')
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass

    return redirect(url_for('mis_reservas'))


# ── PANEL ADMIN ────────────────────────────────────────────────
@app.route('/admin')
def admin():
    if 'user' not in session:
        return redirect('/login')
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM restaurantes ORDER BY nombre ASC")
    restaurantes = cursor.fetchall()
    cursor.execute(
        '''SELECT r.id, r.personas, r.fecha_hora, r.estado,
                  c.nombre AS nombre_cliente, c.email,
                  res.nombre AS restaurante_nombre
           FROM reservas r
           JOIN clientes c ON r.cliente_id = c.id
           JOIN restaurantes res ON r.restaurante_id = res.id
           ORDER BY r.fecha_hora DESC'''
    )
    reservas = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin.html', restaurantes=restaurantes, reservas=reservas)


# ── CREAR RESTAURANTE ──────────────────────────────────────────
@app.route('/crear', methods=['POST'])
def crear_restaurante():
    nombre         = request.form['nombre']
    ciudad         = request.form['ciudad']
    total_mesas    = int(request.form['total_mesas'])
    mesas_ocupadas = int(request.form['mesas_ocupadas'])

    if mesas_ocupadas > total_mesas:
        flash('Las mesas ocupadas no pueden ser mayores al total.', 'error')
        return redirect(url_for('admin'))

    try:
        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO restaurantes (nombre, ciudad, total_mesas, mesas_ocupadas) VALUES (%s, %s, %s, %s)',
            (nombre, ciudad, total_mesas, mesas_ocupadas)
        )
        conn.commit()
        flash('Restaurante creado correctamente.', 'success')
    except Error as e:
        flash(f'No se pudo crear: {e}', 'error')
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass

    return redirect(url_for('admin'))


# ── ACTUALIZAR OCUPACION ───────────────────────────────────────
@app.route('/actualizar/<int:restaurante_id>', methods=['POST'])
def actualizar_restaurante(restaurante_id):
    mesas_ocupadas = int(request.form['mesas_ocupadas'])

    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT total_mesas FROM restaurantes WHERE id = %s', (restaurante_id,))
        restaurante = cursor.fetchone()

        if not restaurante or mesas_ocupadas > restaurante['total_mesas']:
            flash('Valor invalido.', 'error')
            return redirect(url_for('admin'))

        cursor = conn.cursor()
        cursor.execute('UPDATE restaurantes SET mesas_ocupadas = %s WHERE id = %s', (mesas_ocupadas, restaurante_id))
        conn.commit()
        flash('Disponibilidad actualizada.', 'success')
    except Error as e:
        flash(f'No se pudo actualizar: {e}', 'error')
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass

    return redirect(url_for('admin'))


# ── CANCELAR RESERVA (ADMIN) ───────────────────────────────────
@app.route('/cancelar_reserva/<int:reserva_id>', methods=['POST'])
def cancelar_reserva(reserva_id):
    if 'user' not in session:
        return redirect('/login')

    try:
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT restaurante_id FROM reservas WHERE id = %s AND estado = 'pendiente'",
            (reserva_id,)
        )
        reserva = cursor.fetchone()

        cursor = conn.cursor()
        cursor.execute("UPDATE reservas SET estado = 'cancelada' WHERE id = %s", (reserva_id,))
        if reserva:
            cursor.execute(
                'UPDATE restaurantes SET mesas_ocupadas = GREATEST(mesas_ocupadas - 1, 0) WHERE id = %s',
                (reserva['restaurante_id'],)
            )
        conn.commit()
        flash('Reserva cancelada y mesa liberada.', 'success')
    except Error as e:
        flash(f'No se pudo cancelar: {e}', 'error')
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass

    return redirect(url_for('admin'))


if __name__ == '__main__':
    app.run(debug=True)
