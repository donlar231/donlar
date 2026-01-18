from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import pyodbc, qrcode, io, base64, os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "factory_secret_2026"

# ຕັ້ງຄ່າບ່ອນເກັບຮູບ
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ເຊື່ອມຕໍ່ SQL Server (LAPTOP-LCRGL9F3)
def get_db_connection():
    return pyodbc.connect(
        "DRIVER={SQL Server};"
        "SERVER=LAPTOP-LCRGL9F3\\SQLEXPRESS;"
        "DATABASE=ClothingFactoryDB;"
        "Trusted_Connection=yes;"
    )

# --- ໜ້າລູກຄ້າ ---
@app.route('/')
def customer_home():
    return render_template('customer_view.html')

@app.route('/api/track/<order_id>')
def api_track(order_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT CurrentStatus, CustomerName, ShirtDetail, ImagePath FROM Orders WHERE OrderID = ?", (order_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        status_text = ["ລໍຖ້າການຜະລິດ", "ປີ້ນສີເສື້ອສຳເລັດ", "ໂລເສື້ອສຳເລັດ", "ຍີບເສື້ອສຳເລັດ"]
        return jsonify({
            "status": "success", "current_status": row[0], "customer_name": row[1],
            "detail": row[2], "image": row[3], "status_message": status_text[row[0]]
        })
    return jsonify({"status": "not_found"})

# --- ໜ້າ Login ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user, pw = request.form['username'], request.form['password']
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("SELECT Role FROM Users WHERE Username=? AND Password=?", (user, pw))
        res = cursor.fetchone(); conn.close()
        if res:
            session['username'], session['role'] = user, res[0]
            if res[0] == 'billing': return redirect(url_for('create_order'))
            return redirect(url_for('staff_scanner'))
    return render_template('login.html')

# --- ໜ້າອອກບິນ (Admin) ---
@app.route('/admin/create-order', methods=['GET', 'POST'])
def create_order():
    if session.get('role') != 'billing': return redirect(url_for('login'))
    if request.method == 'POST':
        oid, cname, det = request.form['order_id'], request.form['cust_name'], request.form['detail']
        file = request.files['image']
        fname = secure_filename(file.filename) if file else ""
        if file: file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
        
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("INSERT INTO Orders (OrderID, CustomerName, CurrentStatus, ShirtDetail, ImagePath) VALUES (?,?,?,?,?)",
                       (oid, cname, 0, det, fname))
        conn.commit(); conn.close()
        return redirect(url_for('view_qr', order_id=oid))
    return render_template('create_order.html')

@app.route('/view_qr/<order_id>')
def view_qr(order_id):
    qr = qrcode.make(order_id)
    buf = io.BytesIO(); qr.save(buf)
    qr_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    return f"<div style='text-align:center;'><h3>QR: {order_id}</h3><img src='data:image/png;base64,{qr_b64}'><br><a href='/admin/create-order'>ກັບຄືນ</a></div>"

# --- ໜ້າພະນັກງານຜະລິດ ---
@app.route('/staff/scanner')
def staff_scanner():
    if 'role' not in session: return redirect(url_for('login'))
    return render_template('staff_scanner.html', role=session['role'])

@app.route('/api/scan-update', methods=['POST'])
def api_scan_update():
    oid = request.json.get('order_id')
    status_map = {'printing': 1, 'ironing': 2, 'sewing': 3}
    new_status = status_map.get(session.get('role'), 0)
    conn = get_db_connection(); cursor = conn.cursor()
    cursor.execute("UPDATE Orders SET CurrentStatus=? WHERE OrderID=?", (new_status, oid))
    conn.commit(); conn.close()
    return jsonify({"status": "success"})

if __name__ == '__main__':
    # ໃຊ້ 0.0.0.0 ເພື່ອໃຫ້ Ngrok ສາມາດດຶງຂໍ້ມູນໄປ Online ໄດ້
    app.run(host='0.0.0.0', port=5000, debug=True)