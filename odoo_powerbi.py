# =============================================================
# CONEXIÓN ODOO → POWER BI
# =============================================================
# Descripción: Este script extrae datos de ventas desde Odoo
# via XML-RPC y los transforma con Pandas para su visualización
# directa en Power BI sin necesidad de archivos intermedios.
#
# Autor: Sol Senosiain
# Fuente de datos: Odoo (instancia propia)
# Tablas generadas: df_pedidos, df_lineas
#
# Configuración:
#   Copiar .env.example → .env y completar con tus credenciales.
#   Requiere: pip install python-dotenv pandas
#
# Para actualizar los datos en Power BI:
#   Inicio → Actualizar (Power BI vuelve a ejecutar este script)
# =============================================================

import xmlrpc.client
import pandas as pd
import os
from dotenv import load_dotenv

# -------------------------------------------------------------
# 1. CONFIGURACIÓN DE CONEXIÓN
# -------------------------------------------------------------
# Las credenciales se cargan desde un archivo .env local.
# La API Key se genera en: Ajustes → Seguridad → Claves API
# IMPORTANTE: Nunca subir el archivo .env a GitHub.
# -------------------------------------------------------------
load_dotenv()

url      = os.getenv('ODOO_URL')       # Ej: https://miempresa.odoo.com
db       = os.getenv('ODOO_DB')        # Nombre de la base de datos
username = os.getenv('ODOO_USERNAME')  # Usuario administrador
api_key  = os.getenv('ODOO_API_KEY')   # API Key generada en Odoo

# -------------------------------------------------------------
# 2. AUTENTICACIÓN
# -------------------------------------------------------------
# XML-RPC requiere dos endpoints:
#   - /xmlrpc/2/common → autenticación (devuelve uid)
#   - /xmlrpc/2/object → consultas de datos
# El uid es el identificador único del usuario autenticado.
# -------------------------------------------------------------
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid    = common.authenticate(db, username, api_key, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

# -------------------------------------------------------------
# 3. EXTRACCIÓN DE DATOS
# -------------------------------------------------------------

# --- TABLA 1: PEDIDOS DE VENTA (sale.order) ---
# Campos extraídos:
#   - name: número de pedido (S00001, S00002, etc.)
#   - partner_id: cliente [id, nombre]
#   - date_order: fecha del pedido
#   - amount_total: monto total del pedido
#   - state: estado (draft, sale, done, cancel)
pedidos = models.execute_kw(
    db, uid, api_key,
    'sale.order',       # modelo de Odoo
    'search_read',      # operación: buscar y leer
    [[]],               # sin filtros → trae todos los registros
    {'fields': ['name', 'partner_id', 'date_order', 'amount_total', 'state'], 'limit': 200}
)
df_pedidos = pd.DataFrame(pedidos)

# --- TABLA 2: LÍNEAS DE PEDIDO (sale.order.line) ---
# Cada pedido tiene una o más líneas, una por producto.
# Campos extraídos:
#   - order_id: referencia al pedido [id, nombre]
#   - product_id: producto [id, nombre]
#   - product_uom_qty: cantidad vendida
#   - price_unit: precio unitario
#   - price_subtotal: subtotal de la línea (qty × precio)
lineas = models.execute_kw(
    db, uid, api_key,
    'sale.order.line',
    'search_read',
    [[]],
    {'fields': ['order_id', 'product_id', 'product_uom_qty', 'price_unit', 'price_subtotal'], 'limit': 500}
)
df_lineas = pd.DataFrame(lineas)

# -------------------------------------------------------------
# 4. TRANSFORMACIÓN Y LIMPIEZA
# -------------------------------------------------------------
# Odoo devuelve campos relacionales como listas [id, nombre].
# Extraemos solo el nombre para mayor legibilidad.
# Ejemplo: [42, 'Martín García'] → 'Martín García'
# -------------------------------------------------------------

# Extraer nombre del cliente desde partner_id
df_pedidos['cliente'] = df_pedidos['partner_id'].apply(lambda x: x[1] if x else None)
df_pedidos = df_pedidos.drop('partner_id', axis=1)

# Convertir fecha a tipo datetime para facilitar filtros en Power BI
df_pedidos['date_order'] = pd.to_datetime(df_pedidos['date_order'])

# Extraer nombre del producto desde product_id
df_lineas['producto'] = df_lineas['product_id'].apply(lambda x: x[1] if x else None)
df_lineas = df_lineas.drop('product_id', axis=1)

# -------------------------------------------------------------
# Power BI detecta automáticamente df_pedidos y df_lineas
# como tablas disponibles para importar al modelo de datos.
# -------------------------------------------------------------
