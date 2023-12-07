from flask import Flask, render_template, request,redirect, url_for
from flask import Flask, render_template, request, flash, redirect, url_for, session
import hashlib
import random
import string
import sqlite3
from flask_mail import Message
from utilidades import generar_combinaciones
from collections import Counter
from statistics import median, stdev
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from io import BytesIO



app = Flask(__name__)
app.config['DATABASE'] = 'clientes.db'  # Agrega esta línea para configurar la base de datos
app.secret_key = 'tu_clave_secreta_aqui'

DATABASE = 'clientes.db'
def close_connection(conn):
    conn.close()
def conectar_bd():
    return sqlite3.connect(app.config['DATABASE'], check_same_thread=False)
# Manejador de error para errores internos del servidor (código 500)
@app.errorhandler(500)
def internal_server_error(error):
    # Obtiene detalles del error
    error_type = type(error).__name__
    error_message = str(error)
    error_file = error.__traceback__.tb_frame.f_code.co_filename
    error_line = error.__traceback__.tb_lineno
    error_details = []

    # Puedes incluir más detalles del error según tus necesidades
    # Por ejemplo, puedes acceder a error.args para obtener información adicional

    return render_template('error.html', error_type=error_type, error_message=error_message,
                           error_file=error_file, error_line=error_line, error_details=error_details), 500

@app.route('/')
def inicio():
    return render_template('menu.html')
@app.route('/registro2', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        ticket = request.form['ticket']
        usuario = request.form['usuario']
        contrasena = hashlib.sha256(request.form['contrasena'].encode()).hexdigest()
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        telefono = request.form['telefono']
        lugar_residencia = request.form['lugar_residencia']
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM codigo_registro WHERE ticket = ? AND usado = 0', (ticket,))
            codigo_valido = cursor.fetchone()
            if codigo_valido:
                cursor.execute('SELECT * FROM clientes_usuario WHERE telefono = ?', (telefono,))
                telefono_existente = cursor.fetchone()
                if telefono_existente:
                    flash("El número de teléfono ya está registrado. Por favor, utiliza otro número.", "error")
                    return render_template('registro2.html')
                cursor.execute('UPDATE codigo_registro SET usado = 1, usuario_cliente = ?, telefono_cliente = ?, estado_ticket = "pendiente de pago", fecha_venta = CURRENT_TIMESTAMP WHERE ticket = ?', (usuario, telefono, ticket))
                combinacion1, combinacion2, combinacion3, combinacion4 = generar_combinaciones(telefono)
                cursor.execute('''
                    INSERT INTO clientes_usuario (usuario, contrasena, nombre, apellido, telefono, lugar_residencia, combinacion1, combinacion2, combinacion3, combinacion4)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (usuario, contrasena, nombre, apellido, telefono, lugar_residencia, combinacion1, combinacion2, combinacion3, combinacion4))
                conn.commit()
                flash("Registro exitoso. ¡Bienvenido!", "success")
                return redirect(url_for('inicio_sesion2'))
            else:
                flash("Código de ticket inválido o ya utilizado. Por favor, intenta de nuevo.", "error")
        finally:
            conn.close()
    return render_template('registro2.html')
@app.route('/inicio_sesion2', methods=['GET', 'POST'])
def inicio_sesion2():
    if request.method == 'POST':
        usuario = request.form['usuario']
        contrasena = hashlib.sha256(request.form['contrasena'].encode()).hexdigest()
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM clientes_usuario WHERE usuario = ? AND contrasena = ?', (usuario, contrasena))
            usuario_registrado = cursor.fetchone()
            if usuario_registrado:
                session['usuario'] = usuario_registrado[1]
                return redirect(url_for('sorteo2'))
            else:
                flash('Usuario o contraseña incorrectos. Por favor, inténtalo de nuevo.', 'error')
        finally:
            conn.close()
    return render_template('inicio_sesion2.html')
@app.route('/cerrar_sesion2')
def cerrar_sesion2():
    session.pop('usuario', None)
    return redirect(url_for('inicio_sesion2'))

def get_resultados_sorteo(id_cliente):
    # Connect to SQLite database
    conn = sqlite3.connect('clientes.db')
    cursor = conn.cursor()

    # Fetch resultados_sorteo from the "sorteos" table for a specific id_cliente
    cursor.execute("SELECT * FROM sorteos WHERE id_cliente = ?", (id_cliente,))
    resultados_sorteo = cursor.fetchall()

    # Close the database connection
    conn.close()

    return resultados_sorteo

@app.route('/mostrar_resultados/<int:id_cliente>')
def mostrar_resultados(id_cliente):
    # Get resultados_sorteo for the specified id_cliente
    resultados_sorteo = get_resultados_sorteo(id_cliente)

    return render_template('sorteos_ganados.html', resultado_sorteo=resultados_sorteo)

# Ruta para el sorteo
@app.route('/sorteo2')
def sorteo2():
    if 'usuario' in session:
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM clientes_usuario WHERE usuario = ?', (session['usuario'],))
            usuario_registrado = cursor.fetchone()
            cursor.execute('SELECT * FROM codigo_registro WHERE telefono_cliente = ?', (usuario_registrado[5],))
            codigo_registro_info = cursor.fetchone()

            # Fetch the won draws for the logged-in user
            cursor.execute('SELECT * FROM sorteos WHERE id_cliente = ? AND valor_ganado > 0', (usuario_registrado[0],))
            sorteos_ganados = cursor.fetchall()

            if usuario_registrado:
                return render_template('sorteo2.html',
                                       usuario_registrado=usuario_registrado,
                                       codigo_registro_info=codigo_registro_info,
                                       sorteos_ganados=sorteos_ganados)
        finally:
            conn.close()
    return redirect(url_for('inicio_sesion2'))


def obtener_contadores_combinaciones():
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute('SELECT id, telefono FROM clientes_usuario')
        registros = cursor.fetchall()
        contadores = {}
        for id, telefono in registros:
            combinaciones = generar_combinaciones(telefono)
            for combinacion in combinaciones:
                if combinacion in contadores:
                    contadores[combinacion].append(id)
                else:
                    contadores[combinacion] = [id]
        return contadores
    except Exception as e:
        print(f"Error al obtener contadores de combinaciones: {e}")
        return {}
    return contadores
def obtener_info_registro(registro_id):
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clientes_usuario WHERE id=?', (registro_id,))
        registro = cursor.fetchone()
        return registro
    except Exception as e:
        print(f"Error al obtener información del registro {registro_id}: {e}")
        return None
    finally:
        conn.close()
def obtener_contadores_combinaciones():
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute('SELECT id, telefono FROM clientes_usuario')
        registros = cursor.fetchall()
        contadores = {}
        for id, telefono in registros:
            combinaciones = generar_combinaciones(telefono)
            for combinacion in combinaciones:
                if combinacion in contadores:
                    contadores[combinacion].append(id)
                else:
                    contadores[combinacion] = [id]
        return contadores
    except Exception as e:
        print(f"Error al obtener contadores de combinaciones: {e}")
        return {}
    return contadores
def obtener_info_registro(registro_id):
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clientes_usuario WHERE id=?', (registro_id,))
        registro = cursor.fetchone()
        return registro
    except Exception as e:
        print(f"Error al obtener información del registro {registro_id}: {e}")
        return None
    finally:
        conn.close()
@app.route('/mostrar_clientes')
def mostrar_clientes():
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM clientes_usuario')
    clientes = cursor.fetchall()
    conn.close()
    return render_template('mostrar_clientes.html', clientes=clientes, menu=render_template('menu.html'))
@app.route('/editar_cliente/<int:cliente_id>', methods=['GET', 'POST'])
def editar_cliente(cliente_id):
    conn = conectar_bd()
    cursor = conn.cursor()
    if request.method == 'POST':
        datos_cliente = (
            request.form['usuario'],
            request.form['contrasena'],
            request.form['nombre'],
            request.form['apellido'],
            request.form['telefono'],
            request.form['lugar_residencia'],
            request.form['combinacion1'],
            request.form['combinacion2'],
            request.form['combinacion3'],
            request.form['combinacion4'],
            cliente_id
        )
        cursor.execute('UPDATE clientes_usuario SET usuario=?, contrasena=?, nombre=?, apellido=?, telefono=?, lugar_residencia=?, combinacion1=?, combinacion2=?, combinacion3=?, combinacion4=? WHERE id=?', datos_cliente)
        conn.commit()
        conn.close()
        return redirect(url_for('mostrar_clientes'))
    cursor.execute('SELECT * FROM clientes_usuario WHERE id=?', (cliente_id,))
    cliente = cursor.fetchone()
    conn.close()
    return render_template('editar_cliente.html', cliente=cliente)

# Ruta para restablecer contraseña
@app.route('/restablecer_contrasena', methods=['GET', 'POST'])
def restablecer_contrasena():
    if request.method == 'POST':
        usuario = request.form['usuario']
        conn = conectar_bd()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM clientes_usuario WHERE usuario = ?', (usuario,))
            usuario_existente = cursor.fetchone()
            if usuario_existente:
                token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
                cursor.execute('INSERT INTO solicitudes_restablecimiento (usuario_cliente, token, fecha_solicitud) VALUES (?, ?, ?)', (usuario, token, datetime.now()))
                conn.commit()
                mensaje = Message('Restablecer Contraseña', recipients=[usuario_existente[5]])  # Reemplaza con el índice correcto para el correo electrónico en tu tabla
                mensaje.body = f'Para restablecer tu contraseña, haz clic en el siguiente enlace: {url_for("cambiar_contrasena", token=token, _external=True)}'
#                mail.send(mensaje)
                flash('Se ha enviado un correo electrónico con las instrucciones para restablecer la contraseña.', 'success')
                return redirect(url_for('inicio_sesion2'))
            else:
                flash('Usuario no encontrado. Por favor, verifica tu información.', 'error')
        finally:
            conn.close()
    return render_template('restablecer_contrasena.html')
@app.route('/eliminar_cliente/<int:cliente_id>')
def eliminar_cliente(cliente_id):
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM clientes_usuario WHERE id=?', (cliente_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('mostrar_clientes'))
@app.route('/combinaciones_repetidas')
def combinaciones_repetidas():
    contadores = obtener_contadores_combinaciones()
    combinaciones_ordenadas = sorted(contadores.items(), key=lambda x: len(x[1]), reverse=True)
    info_combinaciones = []
    for combinacion, ids in combinaciones_ordenadas:
        detalles_repeticiones = []
        for id in ids:
            detalles_repeticiones.append(obtener_info_registro(id))
        info_combinaciones.append({
            'combinacion': combinacion,
            'repeticiones': len(ids),
            'detalles_repeticiones': detalles_repeticiones
        })
    return render_template('combinaciones_repetidas.html', combinaciones=info_combinaciones)
@app.route('/buscar_combinaciones', methods=['GET', 'POST'])
def buscar_combinaciones():
    if request.method == 'POST':
        telefono_ingresado = request.form['telefono']
        if len(telefono_ingresado) == 4 and telefono_ingresado.isdigit():
            combinacion_busqueda = telefono_ingresado
            conn = conectar_bd()
            cursor = conn.cursor()
            cursor.execute('SELECT id, telefono FROM clientes_usuario')
            registros = cursor.fetchall()
            conn.close()
            resultados = []
            for id, telefono in registros:
                combinaciones = generar_combinaciones(telefono)
                if combinacion_busqueda in combinaciones:
                    detalles_cliente = obtener_info_registro(id)
                    if detalles_cliente:
                        resultados.append(detalles_cliente)

            return render_template('resultados_busqueda.html', resultados=resultados, combinacion_busqueda=combinacion_busqueda)
        else:
            return render_template('buscar_combinaciones.html', error='Ingrese un número de 4 dígitos válido.')
    return render_template('buscar_combinaciones.html', error=None)
@app.route('/analisis_ventas', methods=['GET', 'POST'])
def analisis_ventas():
    if request.method == 'POST':
        conn = conectar_bd()
        cursor = conn.cursor()
        valor_ticket = float(request.form['valor_ticket'])
        cursor.execute("SELECT COUNT(*) FROM clientes_usuario")
        total_registros = cursor.fetchone()[0]
        total_ventas = valor_ticket * total_registros
        cursor.execute("SELECT COUNT(*) FROM sorteos")
        total_sorteos_realizados = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM sorteos WHERE valor_ganado > 0")
        total_sorteos_ganados = cursor.fetchone()[0]
        cursor.execute("SELECT valor_ganado FROM sorteos")
        valores_ganados = [valor[0] for valor in cursor.fetchall() if valor[0] is not None]
        total_ganado = sum(valores_ganados)
        total_no_ganado = total_ventas - total_ganado
        if valores_ganados:
            promedio_ganado = total_ganado / len(valores_ganados)
            minimo_ganado = min(valores_ganados)
            maximo_ganado = max(valores_ganados)
            num_ganadores = len(valores_ganados)
            porcentaje_ganadores = (num_ganadores / total_registros) * 100 if total_registros > 0 else 0
            mediana_valor_ganado = median(valores_ganados)
            desviacion_estandar_valor_ganado = stdev(valores_ganados) if len(valores_ganados) > 1 else 0
            balance_tickets_sorteos = total_ventas / total_ganado if total_ganado > 0 else 0
            equidad_modelo_negocio = total_ganado / (total_ganado + total_no_ganado) * 100 if (total_ganado + total_no_ganado) > 0 else 0
            conn.close()
            return render_template('analisis_ventas.html',
                                   total_ventas=total_ventas,
                                   total_registros=total_registros,
                                   total_sorteos_realizados=total_sorteos_realizados,
                                   total_sorteos_ganados=total_sorteos_ganados,
                                   total_sorteos_no_ganados=total_sorteos_realizados - total_sorteos_ganados,
                                   total_ganado=total_ganado,
                                   total_no_ganado=total_no_ganado,
                                   promedio_ganado=promedio_ganado,
                                   minimo_ganado=minimo_ganado,
                                   maximo_ganado=maximo_ganado,
                                   num_ganadores=num_ganadores,
                                   porcentaje_ganadores=porcentaje_ganadores,
                                   mediana_valor_ganado=mediana_valor_ganado,
                                   desviacion_estandar_valor_ganado=desviacion_estandar_valor_ganado,
                                   balance_tickets_sorteos=balance_tickets_sorteos,
                                   equidad_modelo_negocio=equidad_modelo_negocio)
        else:
            conn.close()
            return render_template('analisis_ventas.html', error="No hay registros en la tabla de sorteos.")
    return render_template('formulario_analisis_ventas.html')

def plot_histogram(valores, color, title):
    plt.hist(valores, bins=20, color=color, edgecolor='black')
    plt.title(title)
    plt.xlabel('Valor')
    plt.ylabel('Frecuencia')
    buffer = BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    plt.close()
    return buffer

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store'
    return response


# Ruta para consultar sorteos
@app.route('/consultar_sorteos')
def consultar_sorteos():
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute("SELECT id_cliente, nombre, numero_combinacion, CAST(valor_ganado AS INTEGER), CAST(no_ganado AS INTEGER) FROM sorteos")
        datos = cursor.fetchall()

        cantidad_sorteos_generados = len(datos)

        if datos:
            valores_ganados = [valor_ganado for (_, _, _, valor_ganado, _) in datos if valor_ganado is not None]
            valores_no_ganados = [no_ganado for (_, _, _, _, no_ganado) in datos if no_ganado is not None]
            total_valor_ganado = sum(valores_ganados)
            total_valor_no_ganado = sum(valores_no_ganados)
            promedio_valor_ganado = total_valor_ganado / cantidad_sorteos_generados if cantidad_sorteos_generados > 0 else 0
            valor_minimo_ganado = min(valores_ganados) if valores_ganados else 0
            valor_maximo_ganado = max(valores_ganados) if valores_ganados else 0
            ganadores = set([id_cliente for (id_cliente, _, _, valor_ganado, _) in datos if valor_ganado is not None])
            cantidad_ganadores = len(ganadores)
            porcentaje_ganadores = (cantidad_ganadores / cantidad_sorteos_generados) * 100 if cantidad_sorteos_generados > 0 else 0
            # Obtener las tres combinaciones más repetidas y si fueron ganadas o no
            combinaciones = [(numero_combinacion, valor_ganado is not None) for (_, _, numero_combinacion, valor_ganado, _) in datos if numero_combinacion is not None]
            frecuencia_combinaciones = Counter(combinaciones)
            combinaciones_mas_repetidas = frecuencia_combinaciones.most_common(20)

            # Nuevas métricas
            mediana_valor_ganado = median(valores_ganados) if valores_ganados else 0
            desviacion_estandar_valor_ganado = stdev(valores_ganados) if len(valores_ganados) > 1 else 0
            total_sorteos_realizados = cantidad_sorteos_generados
            porcentaje_sorteos_sin_ganadores = (len([1 for (_, _, _, _, no_ganado) in datos if no_ganado > 0]) / total_sorteos_realizados) * 100 if total_sorteos_realizados > 0 else 0
            valor_total_entregado = total_valor_ganado + total_valor_no_ganado
            valor_promedio_por_sorteo = valor_total_entregado / total_sorteos_realizados if total_sorteos_realizados > 0 else 0

            # Histograma de valores ganados
            buffer_ganados = plot_histogram(valores_ganados, 'blue', 'Histograma de Valores Ganados')

            # Histograma de valores no ganados
            buffer_no_ganados = plot_histogram(valores_no_ganados, 'red', 'Histograma de Valores No Ganados')
            # Cierra la conexión a la base de datos
            conn.close()

            # Devolver el resultado renderizado a través de la plantilla HTML
            return render_template('consultar_sorteos.html',
                                   datos=datos,
                                   cantidad_sorteos_generados=cantidad_sorteos_generados,
                                   total_valor_ganado=total_valor_ganado,
                                   total_valor_no_ganado=total_valor_no_ganado,
                                   promedio_valor_ganado=promedio_valor_ganado,
                                   valor_minimo_ganado=valor_minimo_ganado,
                                   valor_maximo_ganado=valor_maximo_ganado,
                                   cantidad_ganadores=cantidad_ganadores,
                                   porcentaje_ganadores=porcentaje_ganadores,
                                   combinaciones_mas_repetidas=combinaciones_mas_repetidas,
                                   mediana_valor_ganado=mediana_valor_ganado,
                                   desviacion_estandar_valor_ganado=desviacion_estandar_valor_ganado,
                                   total_sorteos_realizados=total_sorteos_realizados,
                                   porcentaje_sorteos_sin_ganadores=porcentaje_sorteos_sin_ganadores,
                                   valor_total_entregado=valor_total_entregado,
                                   valor_promedio_por_sorteo=valor_promedio_por_sorteo,
                                   buffer_ganados=buffer_ganados.getvalue(),
                                   buffer_no_ganados=buffer_no_ganados.getvalue())

        else:
            # Cierra la conexión a la base de datos
            conn.close()
            print("No se encontraron registros en la tabla de sorteos.")
            return render_template('consultar_sorteos.html', datos=None)

    except Exception as e:
        # Manejo de errores
        print(f"Error al consultar sorteos: {str(e)}")
        raise  # Raising the exception to see the full traceback in the console
    finally:
        # Asegurarse de cerrar la conexión en caso de cualquier excepción
        if conn:
            conn.close()

@app.route('/realizar_sorteo', methods=['GET', 'POST'])
def realizar_sorteo():
    if request.method == 'POST':
        conn = conectar_bd()
        cursor = conn.cursor()
        premio = request.form['premio']
        cursor.execute("SELECT * FROM clientes_usuario")
        datos = cursor.fetchall()
        fecha_sorteo = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        numero_sorteado = str(random.randint(1000, 9999))
        ganadores = []
        for row in datos:
            id_cliente, usuario, contrasena, nombre, apellido, telefono, lugar_residencia, combinacion1, combinacion2, combinacion3, combinacion4, url = row
            combinaciones = (combinacion1, combinacion2, combinacion3, combinacion4)
            if numero_sorteado in combinaciones:
                ganadores.append((id_cliente, nombre, numero_sorteado))
        if ganadores:
            num_coincidencias = len(ganadores)
            valor_ganado = int(float(premio) / num_coincidencias)
            valor_ganado = round(valor_ganado, -2)
            for id_cliente, nombre, numero_combinacion in ganadores:
                cursor.execute("INSERT INTO sorteos (id_cliente, nombre, numero_combinacion, valor_ganado, no_ganado, num_sorteos, fecha_sorteo) VALUES (?, ?, ?, ?, 0, 1, ?)",
                               (id_cliente, nombre, numero_combinacion, valor_ganado, fecha_sorteo))
                conn.commit()
            close_connection(conn)
            return render_template('ganadores.html', numero_sorteado=numero_sorteado, ganadores=ganadores, valor_ganado=valor_ganado)
        else:
            cursor.execute("INSERT INTO sorteos (numero_combinacion, no_ganado, num_sorteos, fecha_sorteo) VALUES (?, ?, 1, ?)", (numero_sorteado, int(float(premio)), fecha_sorteo))
            conn.commit()
            close_connection(conn)
            return render_template('sin_ganadores.html', numero_sorteado=numero_sorteado)
    return render_template('formulario_sorteo.html')


@app.route('/index')
def index():
    with sqlite3.connect(DATABASE) as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM vendedores")
        vendedores = cur.fetchall()
    return render_template('index.html', vendedores=vendedores)

@app.route('/crear_vendedor', methods=['GET', 'POST'])
def crear_vendedor():
    if request.method == 'POST':
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        tickets_asignados = request.form.get('tickets_asignados', 0)
        contrasena = request.form['contrasena']
        usuario_registro = request.form['usuario_registro']

        with sqlite3.connect(DATABASE) as con:
            cur = con.cursor()
            cur.execute("""
                INSERT INTO vendedores (
                    nombre_vendedor,
                    telefono_vendedor,
                    tickets_asignados_vendedor,
                    tickets_vendidos_vendedor,
                    tickets_pendientespago_vendedor,
                    ganancia_ventatickets_vendedor,
                    pnl_vendedor,
                    contrasena_vendedor,
                    usuario_registro_vendedor
                ) VALUES (?, ?, ?, 0, 0, 0, 0, ?, ?)
            """, (nombre, telefono, tickets_asignados, contrasena, usuario_registro))

        return redirect(url_for('menu_vendedores'))

    return render_template('crear_vendedor.html')

@app.route('/mostrar_vendedores')
def mostrar_vendedores():
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM vendedores')
    vendedores = cursor.fetchall()
    conn.close()
    return render_template('mostrar_vendedores.html', vendedores=vendedores, menu=render_template('crear_vendedor.html'))

@app.route('/editar_vendedor/<int:id_vendedor>', methods=['GET', 'POST'])
def editar_vendedor(id_vendedor):
    conn = conectar_bd()
    cursor = conn.cursor()
    if request.method == 'POST':
        datos_vendedor = (
            request.form['nombre_vendedor'],
            request.form['telefono_vendedor'],
            request.form['tickets_asignados_vendedor'],
            request.form['tickets_vendidos_vendedor'],
            request.form['tickets_pendientespago_vendedor'],
            request.form['ganancia_ventatickets_vendedor'],
            request.form['pnl_vendedor'],
            id_vendedor
        )
        cursor.execute('UPDATE vendedores SET nombre_vendedor=?, telefono_vendedor=?, tickets_asignados_vendedor=?, tickets_vendidos_vendedor=?, tickets_pendientespago_vendedor=?, ganancia_ventatickets_vendedor=?, pnl_vendedor=? WHERE id_vendedor=?', datos_vendedor)
        conn.commit()
        conn.close()
        return redirect(url_for('editar_vendedor', id_vendedor=id_vendedor))
    cursor.execute('SELECT * FROM vendedores WHERE id_vendedor=?', (id_vendedor,))
    vendedor = cursor.fetchone()
    conn.close()
    return render_template('editar_vendedor.html', vendedor=vendedor)

@app.route('/eliminar_vendedor/<int:id_vendedor>', methods=['GET', 'POST'])
def eliminar_vendedor(id_vendedor):
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM vendedores WHERE id_vendedor=?', (id_vendedor,))
    conn.commit()
    conn.close()
    return redirect(url_for('mostrar_vendedores'))

@app.route('/asignar_tickets', methods=['GET', 'POST'])
def asignar_tickets():
    if request.method == 'POST':
        id_vendedor = request.form['id_vendedor']
        cantidad_tickets = request.form['cantidad_tickets']

        with sqlite3.connect(DATABASE) as con:
            cur = con.cursor()

            # Obtener el nombre del vendedor y su comisión
            cur.execute('SELECT nombre_vendedor, ganancia_ventatickets_vendedor FROM vendedores WHERE id_vendedor=?', (id_vendedor,))
            vendedor_info = cur.fetchone()
            nombre_vendedor = vendedor_info[0]
            comision_vendedor = vendedor_info[1]

            # Obtener tickets pendientes de asignar
            cur.execute('SELECT ticket FROM codigo_registro WHERE estado_ticket IS NULL LIMIT ?', (cantidad_tickets,))
            tickets_pendientes = cur.fetchall()

            if not tickets_pendientes:
                return "No hay suficientes tickets disponibles para asignar."

            for ticket in tickets_pendientes:
                ticket_numero = ticket[0]

                # Actualizar información del ticket
                cur.execute('UPDATE codigo_registro SET id_vendedor=?, vendedor=?, comision_vendedor=?, estado_ticket=? WHERE ticket=?',
                            (id_vendedor, nombre_vendedor, comision_vendedor, 'pendiente de pago', ticket_numero))

            # Actualizar la cantidad de tickets asignados al vendedor
            cur.execute('UPDATE vendedores SET tickets_asignados_vendedor = tickets_asignados_vendedor + ? WHERE id_vendedor=?', (len(tickets_pendientes), id_vendedor))

            con.commit()

        return redirect(url_for('mostrar_vendedores'))

    # Obtener la lista de vendedores para el formulario
    with sqlite3.connect(DATABASE) as con:
        cur = con.cursor()
        cur.execute('SELECT id_vendedor, nombre_vendedor FROM vendedores')
        vendedores = cur.fetchall()

    return render_template('asignar_tickets.html', vendedores=vendedores)









def obtener_info_vendedor(id_vendedor):
    with sqlite3.connect(DATABASE) as con:
        cur = con.cursor()
        cur.execute('SELECT * FROM vendedores WHERE id_vendedor=?', (id_vendedor,))
        return cur.fetchone()

def obtener_tickets_asignados(id_vendedor):
    with sqlite3.connect(DATABASE) as con:
        cur = con.cursor()
        cur.execute('SELECT * FROM codigo_registro WHERE id_vendedor=?', (id_vendedor,))
        return cur.fetchall()

def asignar_tickets_iniciales(id_vendedor):
    with sqlite3.connect(DATABASE) as con:
        cur = con.cursor()
        for _ in range(10):
            cur.execute("""
                INSERT INTO codigo_registro (
                    usuario_cliente,
                    id_vendedor,
                    comision_vendedor,
                    estado_ticket
                ) VALUES (?, ?, ?, ?)
            """, (None, id_vendedor, 1000, 'pendiente de pago'))
        con.commit()



@app.route('/registro_vendedor', methods=['GET', 'POST'])
def registro_vendedor():
    if request.method == 'POST':
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        contrasena = request.form['contrasena']
        usuario_registro = request.form['usuario_registro']

        hashed_password = generate_password_hash(contrasena, method='pbkdf2:sha256')

        with sqlite3.connect(DATABASE) as con:
            cur = con.cursor()
            cur.execute("""
                INSERT INTO vendedores (
                    nombre_vendedor,
                    telefono_vendedor,
                    tickets_asignados_vendedor,
                    tickets_vendidos_vendedor,
                    tickets_pendientespago_vendedor,
                    ganancia_ventatickets_vendedor,
                    pnl_vendedor,
                    contrasena_vendedor,
                    usuario_registro_vendedor,
                    comision_vendedor
                ) VALUES (?, ?, 0, 0, 0, 0, 0, ?, ?, 0)
            """, (nombre, telefono, hashed_password, usuario_registro))

        return redirect(url_for('ingreso_vendedor'))

    return render_template('registro_vendedor.html')

@app.route('/ingreso_vendedor', methods=['GET', 'POST'])
def ingreso_vendedor():
    if request.method == 'POST':
        usuario_registro = request.form['usuario_registro']
        contrasena = request.form['contrasena']

        with sqlite3.connect(DATABASE) as con:
            cur = con.cursor()
            cur.execute('SELECT id_vendedor, contrasena_vendedor FROM vendedores WHERE usuario_registro_vendedor=?', (usuario_registro,))
            vendedor = cur.fetchone()

            if vendedor and check_password_hash(vendedor[1], contrasena):
                session['id_vendedor'] = vendedor[0]
                return redirect(url_for('panel_vendedor'))

    return render_template('ingreso_vendedor.html')

@app.route('/panel_vendedor', methods=['GET', 'POST'])
def panel_vendedor():
    if 'id_vendedor' in session:
        id_vendedor = session['id_vendedor']

        with sqlite3.connect(DATABASE) as con:
            cur = con.cursor()
            cur.execute('SELECT * FROM vendedores WHERE id_vendedor=?', (id_vendedor,))
            vendedor = cur.fetchone()
            cur.execute('SELECT * FROM codigo_registro WHERE id_vendedor=?', (id_vendedor,))
            tickets_asignados = cur.fetchall()

            if request.method == 'POST':
                ticket_id = request.form['ticket_id']
                nuevo_estado = request.form['nuevo_estado']

                cur.execute('SELECT * FROM codigo_registro WHERE ticket=? AND id_vendedor=?', (ticket_id, id_vendedor))
                ticket = cur.fetchone()

                if ticket and ticket[8] != 'pagado':  # Verifica si el ticket existe y no está pagado
                    # Actualiza el estado del ticket
                    cur.execute('UPDATE codigo_registro SET estado_ticket=? WHERE ticket=?', (nuevo_estado, ticket_id))

                    if nuevo_estado == 'pagado':
                        ticket_valor = 10000

                        # Verifica si la comisión ya se ha agregado para evitar duplicados
                        if ticket[8] != 'pagado':
                            # Actualiza la comisión del vendedor
                            comision_vendedor_actual = float(vendedor[10]) if vendedor[10] else 0
                            comision_vendedor_nueva = comision_vendedor_actual + 0.05 * ticket_valor
                            ganancia_ticket = 0.05 * ticket_valor
                            tickets_vendidos = int(vendedor[4]) + 1 if vendedor[4] else 1

                            cur.execute('UPDATE vendedores SET ganancia_ventatickets_vendedor = ganancia_ventatickets_vendedor + ?, comision_vendedor = ?, tickets_vendidos_vendedor = ? WHERE id_vendedor=?', (ganancia_ticket, comision_vendedor_nueva, tickets_vendidos, id_vendedor))
                            cur.execute('UPDATE vendedores SET pnl_vendedor = comision_vendedor WHERE id_vendedor=?', (id_vendedor,))


                            # Actualiza la columna tickets_pendientespago_vendedor
                            total_tickets_asignados = int(vendedor[2]) if vendedor[2] else 0
                            total_tickets_vendidos = int(vendedor[4]) + 1
                            tickets_pendientespago = total_tickets_asignados - total_tickets_vendidos
                            cur.execute('UPDATE vendedores SET tickets_pendientespago_vendedor=? WHERE id_vendedor=?', (tickets_pendientespago, id_vendedor))

                            # Marca el ticket como pagado en la tabla
                            cur.execute('UPDATE codigo_registro SET estado_ticket=? WHERE ticket=?', ('pagado', ticket_id))

                    con.commit()
                    return redirect(url_for('panel_vendedor'))

            return render_template('panel_vendedor.html', vendedor=vendedor, tickets_asignados=tickets_asignados)

    return redirect(url_for('ingreso_vendedor'))

@app.route('/modificar_estado_ticket/<string:ticket_id>/<string:nuevo_estado>', methods=['POST'])
def modificar_estado_ticket(ticket_id, nuevo_estado):
    if 'id_vendedor' in session:
        id_vendedor = session['id_vendedor']

        with sqlite3.connect(DATABASE) as con:
            cur = con.cursor()
            cur.execute('SELECT * FROM codigo_registro WHERE ticket=? AND id_vendedor=?', (ticket_id, id_vendedor))
            ticket = cur.fetchone()

            if ticket and ticket[8] != 'pagado':  # Verifica si el ticket existe y no está pagado
                # Actualiza el estado del ticket
                cur.execute('UPDATE codigo_registro SET estado_ticket=? WHERE ticket=?', (nuevo_estado, ticket_id))

                if nuevo_estado == 'pagado':
                    ticket_valor = 10000

                    vendedor = obtener_info_vendedor(id_vendedor)

                    # Verifica si la comisión ya se ha agregado para evitar duplicados
                    if ticket[8] != 'pagado':
                        # Actualiza la comisión del vendedor
                        comision_vendedor_actual = float(vendedor[10]) if vendedor[10] else 0
                        comision_vendedor_nueva = comision_vendedor_actual + 0.05 * ticket_valor
                        ganancia_ticket = 0.05 * ticket_valor
                        tickets_vendidos = int(vendedor[4]) + 1 if vendedor[4] else 1

                        cur.execute('UPDATE vendedores SET ganancia_ventatickets_vendedor = ganancia_ventatickets_vendedor + ?, comision_vendedor = ?, tickets_vendidos_vendedor = ? WHERE id_vendedor=?', (ganancia_ticket, comision_vendedor_nueva, tickets_vendidos, id_vendedor))
                        cur.execute('UPDATE vendedores SET pnl_vendedor = comision_vendedor WHERE id_vendedor=?', (id_vendedor,))


                        # Actualiza la columna tickets_pendientespago_vendedor
                        total_tickets_asignados = int(vendedor[3]) if vendedor[3] else 0
                        total_tickets_vendidos = int(vendedor[4]) + 1
                        tickets_pendientespago = total_tickets_asignados - total_tickets_vendidos
                        cur.execute('UPDATE vendedores SET tickets_pendientespago_vendedor=? WHERE id_vendedor=?', (tickets_pendientespago, id_vendedor))


                        # Marca el ticket como pagado en la tabla
                        cur.execute('UPDATE codigo_registro SET estado_ticket=? WHERE ticket=?', ('pagado', ticket_id))

                con.commit()

        return redirect(url_for('panel_vendedor'))

    return redirect(url_for('ingreso_vendedor'))

@app.route('/resumen')
def resumen():
    # Connect to the SQLite database
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Query data from the tables
    clientes_data = cursor.execute('SELECT * FROM clientes_usuario').fetchall()
    codigo_registro_data = cursor.execute('SELECT * FROM codigo_registro').fetchall()
    sorteos_data = cursor.execute('SELECT * FROM sorteos').fetchall()
    vendedores_data = cursor.execute('SELECT * FROM vendedores').fetchall()

    # Close the database connection
    conn.close()

    # Render HTML template with data
    return render_template('resumen.html',
                           clientes=clientes_data,
                           codigo_registro=codigo_registro_data,
                           sorteos=sorteos_data,
                           vendedores=vendedores_data)


if __name__ == '__main__':
    app.run()
