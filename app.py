from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from mysql.connector import Error
from datetime import date

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'   # Change this for production!

# Database config (using your password)
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '1234',
    'database': 'bloodbank_new'
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

# ------------------- LOGIN -------------------
# @app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Check Staff table using email as username, phone as password
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Staff WHERE email = %s AND phone = %s", (username, password))
        staff = cursor.fetchone()
        cursor.close()
        conn.close()
        if staff:
            session['staff_id'] = staff['staff_id']
            session['name'] = staff['name']
            session['role'] = staff['role']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials (use email as username, phone as password)', 'danger')
    return render_template('login.html')
@app.route('/')
def home():
    return render_template('public_home.html')
# ------------------- DASHBOARD -------------------
@app.route('/dashboard')
def dashboard():
    if 'staff_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) AS total FROM Donor")
    total_donors = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) AS total FROM Patient")
    total_patients = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) AS total FROM Blood_Request")
    total_requests = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) AS total FROM Blood_Request WHERE status = 'Pending'")
    pending_requests = cursor.fetchone()['total']
    cursor.execute("SELECT COUNT(*) AS total FROM Blood_Request WHERE status = 'Completed'")
    completed_requests = cursor.fetchone()['total']
    cursor.close()
    conn.close()
    return render_template('dashboard.html',
                           donors=total_donors,
                           patients=total_patients,
                           requests=total_requests,
                           pending=pending_requests,
                           completed=completed_requests)

# ------------------- DONORS -------------------
@app.route('/donors')
def donors():
    if 'staff_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Donor ORDER BY donor_id DESC")
    donor_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('donors.html', donors=donor_list)

@app.route('/add_donor', methods=['GET', 'POST'])
def add_donor():
    if 'staff_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        blood_group = request.form['blood_group']
        phone = request.form['phone']
        address = request.form['address']
        last_donation = request.form['last_donation'] or None
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""INSERT INTO Donor (name, age, gender, blood_group, phone, address, last_donation_date)
                              VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                           (name, age, gender, blood_group, phone, address, last_donation))
            conn.commit()
            flash('Donor added successfully', 'success')
        except mysql.connector.IntegrityError as e:
            flash(f'Error: Duplicate phone number or other constraint violated.', 'danger')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('donors'))
    return render_template('add_donor.html')

# ------------------- PATIENTS -------------------
@app.route('/patients')
def patients():
    if 'staff_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Patient ORDER BY patient_id DESC")
    patient_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('patients.html', patients=patient_list)

@app.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    if 'staff_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        patient_id = request.form['patient_id']
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        blood_group = request.form['blood_group']
        hospital = request.form['hospital_name']
        phone = request.form['phone']
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""INSERT INTO Patient (patient_id, name, age, gender, blood_group, hospital_name, phone)
                              VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                           (patient_id, name, age, gender, blood_group, hospital, phone))
            conn.commit()
            flash('Patient added successfully', 'success')
        except mysql.connector.IntegrityError:
            flash('Error: Patient ID already exists. Use a different ID.', 'danger')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('patients'))
    return render_template('add_patient.html')

# ------------------- BLOOD REQUESTS -------------------
@app.route('/requests')
def requests():
    if 'staff_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT r.*, p.name AS patient_name 
        FROM Blood_Request r
        JOIN Patient p ON r.patient_id = p.patient_id
        ORDER BY r.request_date DESC
    """)
    request_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('requests.html', requests=request_list)

@app.route('/add_request', methods=['GET', 'POST'])
def add_request():
    if 'staff_id' not in session:
        return redirect(url_for('login'))
    
    # Fetch patients for the dropdown (needed for both GET and POST if form fails)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT patient_id, name FROM Patient ORDER BY name")
    patients = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if request.method == 'POST':
        req_id = request.form['request_id']
        patient_id = request.form['patient_id']
        blood_group = request.form['blood_group']
        quantity = request.form['quantity_required']
        req_date = request.form['request_date']
        status = request.form['status']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""INSERT INTO Blood_Request (request_id, patient_id, blood_group, quantity_required, request_date, status)
                              VALUES (%s, %s, %s, %s, %s, %s)""",
                           (req_id, patient_id, blood_group, quantity, req_date, status))
            conn.commit()
            flash('Blood request added successfully', 'success')
        except mysql.connector.IntegrityError:
            flash('Error: Request ID already exists or patient not found.', 'danger')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('requests'))
    
    return render_template('add_request.html', patients=patients)

@app.route('/update_request_status/<int:req_id>/<new_status>')
def update_request_status(req_id, new_status):
    if 'staff_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Blood_Request SET status = %s WHERE request_id = %s", (new_status, req_id))
    conn.commit()
    cursor.close()
    conn.close()
    flash(f'Request {req_id} status updated to {new_status}', 'info')
    return redirect(url_for('requests'))

# ------------------- BLOOD UNITS -------------------
@app.route('/blood_units')
def blood_units():
    if 'staff_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT u.*, d.name AS donor_name 
        FROM Blood_Unit u
        LEFT JOIN Donor d ON u.donor_id = d.donor_id
        ORDER BY u.collection_date DESC
    """)
    units = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('blood_units.html', units=units)

# ------------------- STAFF -------------------
@app.route('/staff')
def staff_list():
    if 'staff_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Staff")
    all_staff = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('staff.html', staff=all_staff)

# ------------------- LOGOUT -------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
    # ------------------- PUBLIC: Donor Registration (no login) -------------------
@app.route('/register_donor', methods=['GET', 'POST'])
def register_donor():
    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        blood_group = request.form['blood_group']
        phone = request.form['phone']
        address = request.form['address']
        # last_donation_date is NULL for new donors
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""INSERT INTO Donor (name, age, gender, blood_group, phone, address, last_donation_date)
                              VALUES (%s, %s, %s, %s, %s, %s, NULL)""",
                           (name, age, gender, blood_group, phone, address))
            conn.commit()
            flash('Thank you for registering as a blood donor!', 'success')
        except mysql.connector.IntegrityError:
            flash('Error: Phone number already exists. Please use a different phone.', 'danger')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('register_donor'))
    return render_template('public_donor.html')

# ------------------- PUBLIC: Blood Request (no login) -------------------
@app.route('/request_blood', methods=['GET', 'POST'])
def request_blood():
    if request.method == 'POST':
        patient_name = request.form['patient_name']
        age = request.form['age']
        gender = request.form['gender']
        blood_group = request.form['blood_group']
        hospital = request.form['hospital_name']
        phone = request.form['phone']
        quantity = request.form['quantity']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Insert into Patient table
            cursor.execute("""INSERT INTO Patient (name, age, gender, blood_group, hospital_name, phone)
                              VALUES (%s, %s, %s, %s, %s, %s)""",
                           (patient_name, age, gender, blood_group, hospital, phone))
            patient_id = cursor.lastrowid  # works if patient_id is AUTO_INCREMENT
            
            # Insert into Blood_Request table
            cursor.execute("""INSERT INTO Blood_Request (patient_id, blood_group, quantity_required, request_date, status)
                              VALUES (%s, %s, %s, CURDATE(), 'Pending')""",
                           (patient_id, blood_group, quantity))
            conn.commit()
            flash('Blood request submitted successfully. Our staff will contact you.', 'success')
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('request_blood'))
    return render_template('public_request.html')

if __name__ == '__main__':
    app.run(debug=True)