from flask import Flask, flash, redirect, render_template, request, url_for, session
import psycopg2
from datetime import datetime
from psycopg2.extras import RealDictCursor
from functools import wraps
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import check_password_hash
from psycopg2 import connect
from werkzeug.security import generate_password_hash
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_log'
login_manager.session_protection = 'strong'

#admin
#admin123

def get_db_connection():
    db_url = os.environ.get("DATABASE_URL")
    return psycopg2.connect(db_url, sslmode='require')


# =========================
# ADMIN CREDENTIALS & AUTHENTICATION
# =========================
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    response.headers['Vary'] = 'Cookie'  
    return response

def get_admin_by_username(username):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
    SELECT id, username, password_hash, role, status
    FROM admins
    WHERE username = %s
""", (username,))

    admin = cur.fetchone()

    cur.close()
    conn.close()

    return admin

def verify_admin_login(username, password):
    admin = get_admin_by_username(username)

    if not admin:
        return None

    # admin[4] = status
    if admin[4] == False:
        return None

    if check_password_hash(admin[2], password):
        return admin

    return None

# =========================
# ADMIN LOGIC LOG IN/LOG OUT
# =========================

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    admin = verify_admin_login(username, password)

    if admin:
        user = AdminUser(id=admin[0])
        login_user(user)

        flash("Login successful!", "success")
        return redirect(url_for('menu_manage'))

    flash("Invalid credentials", "danger")
    return redirect(url_for('admin_log'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully", "info")
    return redirect(url_for('admin_log'))


class AdminUser(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return AdminUser(user_id)

# =========================
# CLIENT ROUTES
# =========================

@app.route('/')
def home():
    return render_template('landing_page.html')

@app.route('/menu')
def menu():
    return menu_display()

@app.route('/reservation')
def reservation():
    return render_template('reservation.html')


# =========================
# ADMIN ROUTES
# =========================
@app.route('/inventory_manage')
@login_required
def inventory_manage():
    inventory_items = get_inventory_items()
    return render_template('admin/Management/inventory_mangement.html', inventory_items=inventory_items)

@app.route('/reservation_manage')
@login_required
def reservation_manage():
    reservation = reservation_view()
    return render_template('admin/Management/reservation_management.html', reservation=reservation)


# =========================
# ADMIN LOGIN ROUTES
# =========================
@app.route('/admin-panel-secret-777')
def admin_log():
    if current_user.is_authenticated:
        return redirect(url_for('menu_manage'))
    return render_template('admin/log in/admin_log.html')

@app.route('/create-admin')
@login_required
def create_admin():
    return render_template('admin/log in/create_admin acc_.html')


# =========================
# RESERVATION LOGIC
# =========================

@app.route('/create', methods=['POST'])
def reservation_create():
    conn = get_db_connection()

    cur = conn.cursor()

    fname = request.form['full_name']
    email = request.form['email']
    phone = request.form['phone_number']
    address = request.form['address']
    guests = request.form['guests']
    date = request.form['reservation_date']
    time = request.form['reservation_time']
    note = request.form['special_request']

    cur.execute("""
        INSERT INTO CUSTOMER
        (
            CUS_FNAME,
            CUS_PHONE,
            CUS_ADDRESS,
            CUS_EMAIL
        )
        VALUES (%s, %s, %s, %s)
        RETURNING CUS_ID
    """, (
        fname,
        phone,
        address,
        email
    ))

    customer_id = cur.fetchone()[0]

    cur.execute("""
        INSERT INTO RESERVATION
        (
            RSV_GUEST,
            RSV_DATE,
            RSV_TIME,
            RSV_SPEC_REQ,
            CUS_ID
        )
        VALUES (%s, %s, %s, %s, %s)
    """, (
        guests,
        date,
        time,
        note,
        customer_id
    ))
    conn.commit()

    # CLOSE CONNECTION
    cur.close()
    conn.close()

    return redirect(url_for('reservation'))
    
def reservation_view():
    conn = get_db_connection()

    cur = conn.cursor()

    cur.execute("""
        SELECT
            RESERVATION.RSV_ID,
            CUSTOMER.CUS_FNAME,
            CUSTOMER.CUS_PHONE,
            CUSTOMER.CUS_EMAIL,
            CUSTOMER.CUS_ADDRESS,

            RESERVATION.RSV_GUEST,
            RESERVATION.RSV_DATE,
            RESERVATION.RSV_TIME,
            RESERVATION.RSV_SPEC_REQ,
            RESERVATION.RSV_STATUS

        FROM RESERVATION

        INNER JOIN CUSTOMER
        ON RESERVATION.CUS_ID = CUSTOMER.CUS_ID

        ORDER BY RESERVATION.RSV_ID DESC
    """)

    reservations = cur.fetchall()

    cur.close()
    conn.close()

    return reservations

@app.route('/delete-reservation/<int:id>', methods=['POST'])
@login_required
def delete_reservation(id):
    conn = get_db_connection()

    cur = conn.cursor()

    cur.execute("""
        DELETE FROM RESERVATION
        WHERE RSV_ID = %s
    """, (id,))

    conn.commit()

    cur.close()
    conn.close()

    return redirect(url_for('reservation_manage'))

@app.route('/confirm-reservation/<int:id>', methods=['POST'])
@login_required
def confirm_reservation(id):
    conn = get_db_connection()

    cur = conn.cursor()

    cur.execute("""
        UPDATE RESERVATION
        SET RSV_STATUS = 'Confirmed'
        WHERE RSV_ID = %s
    """, (id,))

    conn.commit()

    cur.close()
    conn.close()

    return redirect(url_for('reservation_manage'))

@app.route('/cancel-reservation/<int:id>', methods=['POST'])
@login_required
def cancel_reservation(id):
    conn = get_db_connection()

    cur = conn.cursor()

    cur.execute("""
        UPDATE RESERVATION
        SET RSV_STATUS = 'Cancelled'
        WHERE RSV_ID = %s
    """, (id,))

    conn.commit()

    cur.close()
    conn.close()

    return redirect(url_for('reservation_manage'))

# =========================
# MENU LOGIC
# =========================

@app.route('/menu_manage')
@login_required
def menu_manage():
    conn = get_db_connection()

    cur = conn.cursor()

    cur.execute("""
        SELECT 
            i.MENU_ITEMS_ID,
            i.MENU_ITEMS_NAME,
            i.MENU_ITEMS_PRICE,
            i.MENU_ITEMS_STATUS,
            c.MENU_CATEG_NAME
        FROM MENU_ITEMS i
        JOIN MENU_CATEGORIES c
        ON i.MENU_ITEMS_CATEG_ID = c.MENU_CATEG_ID
        ORDER BY i.MENU_ITEMS_ID DESC
    """)

    menu_items = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('admin/Management/menu_management.html', menu_items=menu_items)

@app.route('/menu/add', methods=['POST'])
@login_required
def add_menu_item():
    conn = get_db_connection()
    cur = conn.cursor()

    name = request.form['name']
    price = request.form['price']
    category_id = request.form['category_id']
    status = request.form.get('status') 

    if status == "on":
        status = True
    else:        
        status = False

    cur.execute("""
        INSERT INTO MENU_ITEMS 
        (MENU_ITEMS_NAME, MENU_ITEMS_PRICE, MENU_ITEMS_STATUS, MENU_ITEMS_CATEG_ID)
        VALUES (%s, %s, %s, %s)
    """, (name, price, status, category_id))


    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('menu_manage'))

@app.route('/menu/update/<int:id>', methods=['POST'])
@login_required
def update_menu(id):
    conn = get_db_connection()
    cur = conn.cursor()

    name = request.form['name']
    price = request.form['price']
    category_id = request.form.get('category_id')
    is_available = request.form.get('status') == 'on'

    cur.execute("""
        UPDATE MENU_ITEMS
        SET MENU_ITEMS_NAME = %s,
            MENU_ITEMS_PRICE = %s,
            MENU_ITEMS_STATUS = %s,
            MENU_ITEMS_CATEG_ID = %s
        WHERE MENU_ITEMS_ID = %s
    """, (name, price, is_available, category_id, id))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('menu_manage'))

@app.route('/menu/delete/<int:id>', methods=['POST'])
@login_required
def delete_menu(id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM MENU_ITEMS
        WHERE MENU_ITEMS_ID = %s
    """, (id,))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('menu_manage'))

@app.route('/menu_display')
def menu_display():
    conn = get_db_connection()

    cur = conn.cursor()

    cur.execute("""
        SELECT
            i.MENU_ITEMS_ID,
            i.MENU_ITEMS_NAME,
            i.MENU_ITEMS_PRICE,
            i.MENU_ITEMS_STATUS,
            c.MENU_CATEG_NAME
        FROM MENU_ITEMS i
        JOIN MENU_CATEGORIES c
        ON i.MENU_ITEMS_CATEG_ID = c.MENU_CATEG_ID
        ORDER BY c.MENU_CATEG_NAME
    """)

    menu_items = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('menu.html', menu_items=menu_items)

# =========================
# INVENTORY LOGIC
# =========================

def get_inventory_items():
    conn = get_db_connection()

    cur = conn.cursor()

    cur.execute("""
        SELECT
            INV_ID,
            INV_ITEM_NAME,
            INV_QUANTITY,
            INV_CATEGORY,
            INV_UNIT,
            INV_PRICE,
            INV_STATUS,
            INV_LAST_UPDATED
        FROM INVENTORY
        ORDER BY INV_ID DESC
    """)

    inventory_items = cur.fetchall()

    cur.close()
    conn.close()

    return inventory_items

@app.route('/inventory_view')
@login_required
def inventory_view():
    inventory_items = get_inventory_items()
    return render_template(
        'admin/Management/inventory_mangement.html',
        inventory_items=inventory_items
    )

@app.route('/inventory/add', methods=['POST'])
@login_required
def add_inventory():
    conn = get_db_connection()
    cur = conn.cursor()

    name = request.form['item_name']
    quantity = request.form['quantity']
    category = request.form['category']
    unit = request.form['unit']
    price = request.form['price']

    status = True if int(quantity) > 0 else False

    cur.execute("""
        INSERT INTO INVENTORY
        (INV_ITEM_NAME, INV_QUANTITY, INV_CATEGORY, INV_UNIT, INV_PRICE, INV_STATUS)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (name, quantity, category, unit, price, status))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('inventory_view'))

@app.route('/inventory/update/<int:id>', methods=['POST'])
@login_required
def update_inventory(id):
    conn = get_db_connection()
    cur = conn.cursor()

    name = request.form['name']
    quantity = request.form['quantity']
    category = request.form['category']
    unit = request.form['unit']
    price = request.form['price']

    status = request.form.get('status')
    is_available = True if status == "on" else False

    cur.execute("""
        UPDATE INVENTORY
        SET INV_ITEM_NAME = %s,
            INV_QUANTITY = %s,
            INV_CATEGORY = %s,
            INV_UNIT = %s,
            INV_PRICE = %s,
            INV_STATUS = %s,
            INV_LAST_UPDATED = CURRENT_TIMESTAMP
        WHERE INV_ID = %s
    """, (name, quantity, category, unit, price, is_available, id))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('inventory_view'))

@app.route('/inventory/delete/<int:id>', methods=['POST'])
@login_required
def delete_inventory(id):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM INVENTORY
        WHERE INV_ID = %s
    """, (id,))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('inventory_view'))






if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000))
    )