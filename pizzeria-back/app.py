
from flask import Flask, jsonify, request, flash
from flask_cors import CORS
import mysql.connector
import config

app = Flask(__name__)
app.secret_key = "pizzeria123"
CORS(app)


def obtener_conexion():
    conexion = mysql.connector.connect(
        host=config.HOST,
        user=config.USER,
        password=config.PASSWORD,
        database=config.DATABASE,
        port=config.PORT
    )

    return conexion


@app.route('/')
def inicio():
    return jsonify({
        "mensaje": "API de la pizzeria funcionando"
    })


@app.route('/probar-conexion')
def probar_conexion():
    try:
        conexion = obtener_conexion()
        conexion.close()

        return jsonify({
            "mensaje": "Conexion con MySQL exitosa"
        })

    except mysql.connector.Error as error:
        return jsonify({
            "error": str(error)
        }), 500


@app.route('/registrar-pedido', methods=['POST'])
def registrar_pedido():

    datos = request.get_json()

    if not datos:
        return jsonify({
            "error": "No se recibieron datos"
        }), 400

    nombre = datos.get('nombre_cliente', '').strip()
    direccion = datos.get('direccion', '').strip()
    telefono = datos.get('telefono', '').strip()
    fecha = datos.get('fecha_pedido')
    pizzas = datos.get('pizzas', [])

    if nombre == '' or direccion == '' or telefono == '' or fecha is None:
        return jsonify({
            "error": "Completa todos los datos del cliente"
        }), 400

    if not isinstance(pizzas, list) or len(pizzas) == 0:
        return jsonify({
            "error": "Agrega al menos una pizza"
        }), 400

    conexion = None
    cursor = None

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()

        total = 0
        detalles = []

        for pizza in pizzas:

            tamano = pizza.get('tamano')
            ingredientes = pizza.get('ingredientes', [])
            cantidad = pizza.get('cantidad')

            if tamano not in ['Mediana', 'Grande']:
                conexion.rollback()
                return jsonify({
                    "error": "Tamaño de pizza no valido"
                }), 400

            if not isinstance(ingredientes, list) or len(ingredientes) == 0:
                conexion.rollback()
                return jsonify({
                    "error": "Selecciona los ingredientes"
                }), 400

            if not isinstance(cantidad, int) or isinstance(cantidad, bool) or cantidad <= 0:
                conexion.rollback()
                return jsonify({
                    "error": "La cantidad debe ser mayor a cero"
                }), 400

            if tamano == 'Mediana':
                precio = 150
            else:
                precio = 200

            subtotal = precio * cantidad
            total = total + subtotal

            detalles.append({
                "tamano": tamano,
                "ingredientes": ", ".join(ingredientes),
                "cantidad": cantidad,
                "precio": precio,
                "subtotal": subtotal
            })

        cursor.execute(
            """INSERT INTO pedidos
            (nombre_cliente, direccion, telefono, fecha_pedido, total)
            VALUES (%s, %s, %s, %s, %s)""",
            (nombre, direccion, telefono, fecha, total)
        )

        id_pedido = cursor.lastrowid

        for detalle in detalles:

            cursor.execute(
                """INSERT INTO detalle_pedido
                (id_pedido, tamano, ingredientes, cantidad,
                precio_unitario, subtotal)
                VALUES (%s, %s, %s, %s, %s, %s)""",
                (
                    id_pedido,
                    detalle['tamano'],
                    detalle['ingredientes'],
                    detalle['cantidad'],
                    detalle['precio'],
                    detalle['subtotal']
                )
            )

        conexion.commit()

        mensaje = "Pedido registrado. Total a pagar: $" + str(total)

        flash(mensaje, "success")

        return jsonify({
            "mensaje": mensaje,
            "id_pedido": id_pedido,
            "total": total,
            "detalles": detalles
        }), 201

    except mysql.connector.Error as error:

        if conexion:
            conexion.rollback()

        return jsonify({
            "error": str(error)
        }), 500

    finally:

        if cursor:
            cursor.close()

        if conexion and conexion.is_connected():
            conexion.close()


@app.route('/ventas/dia/<dia>')
def ventas_dia(dia):

    dias = {
        'lunes': 0,
        'martes': 1,
        'miercoles': 2,
        'miércoles': 2,
        'jueves': 3,
        'viernes': 4,
        'sabado': 5,
        'sábado': 5,
        'domingo': 6
    }

    if dia.lower() not in dias:
        return jsonify({
            "error": "Dia no valido"
        }), 400

    conexion = None
    cursor = None

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)

        cursor.execute(
            """SELECT * FROM pedidos
            WHERE WEEKDAY(fecha_pedido) = %s
            ORDER BY fecha_pedido""",
            (dias[dia.lower()],)
        )

        ventas = cursor.fetchall()

        return jsonify(ventas)

    except mysql.connector.Error as error:
        return jsonify({
            "error": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexion and conexion.is_connected():
            conexion.close()


@app.route('/ventas/mes/<mes>')
def ventas_mes(mes):

    meses = {
        'enero': 1,
        'febrero': 2,
        'marzo': 3,
        'abril': 4,
        'mayo': 5,
        'junio': 6,
        'julio': 7,
        'agosto': 8,
        'septiembre': 9,
        'octubre': 10,
        'noviembre': 11,
        'diciembre': 12
    }

    if mes.lower() not in meses:
        return jsonify({
            "error": "Mes no valido"
        }), 400

    conexion = None
    cursor = None

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)

        cursor.execute(
            """SELECT * FROM pedidos
            WHERE MONTH(fecha_pedido) = %s
            ORDER BY fecha_pedido""",
            (meses[mes.lower()],)
        )

        ventas = cursor.fetchall()

        total = 0

        for venta in ventas:
            total = total + float(venta['total'])

        return jsonify({
            "ventas": ventas,
            "total_acumulado": total
        })

    except mysql.connector.Error as error:
        return jsonify({
            "error": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexion and conexion.is_connected():
            conexion.close()


@app.route('/detalle-pedido/<int:id_pedido>')
def detalle_pedido(id_pedido):

    conexion = None
    cursor = None

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM pedidos WHERE id_pedido = %s",
            (id_pedido,)
        )

        pedido = cursor.fetchone()

        if pedido is None:
            return jsonify({
                "error": "Pedido no encontrado"
            }), 404

        cursor.execute(
            """SELECT * FROM detalle_pedido
            WHERE id_pedido = %s""",
            (id_pedido,)
        )

        detalles = cursor.fetchall()

        return jsonify({
            "pedido": pedido,
            "detalles": detalles
        })

    except mysql.connector.Error as error:
        return jsonify({
            "error": str(error)
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexion and conexion.is_connected():
            conexion.close()


if __name__ == '__main__':
    app.run(debug=True)
