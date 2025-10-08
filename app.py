"""
AyurSutra - Panchakarma Patient Management and Therapy Scheduling Software
Team: Panchakarma Pioneers (PY-III-T085)

Team Members and Responsibilities:
- Aniruddh Negi (Team Lead, 240212122): User Management, Authentication, Overall Architecture
- Mohit Yadav (240212506): Patient Profiles, Therapy Scheduling Engine
- Aditya Mastwal (240211335): Progress Tracking, Billing & Inventory Management
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import sqlite3

app = Flask(__name__)
app.secret_key = 'ayursutra_secret_key_2024'

# =============================================================================
# DATABASE SETUP AND INITIALIZATION
# Responsibility: Aniruddh Negi (Team Lead) - Overall Architecture & Database Design
# =============================================================================

def init_database():
    """
    Initialize the SQLite database with all required tables
    Aniruddh Negi - Creates comprehensive database schema for the entire system
    """
    conn = sqlite3.connect('ayursutra.db')
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('admin', 'doctor', 'therapist')),
            full_name TEXT NOT NULL,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    """)

    # Patients table (Mohit Yadav)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL CHECK (gender IN ('Male', 'Female', 'Other')),
            phone TEXT NOT NULL,
            email TEXT,
            address TEXT,
            emergency_contact TEXT,
            medical_history TEXT,
            allergies TEXT,
            contraindications TEXT,
            prakriti_vata INTEGER DEFAULT 0,
            prakriti_pitta INTEGER DEFAULT 0,
            prakriti_kapha INTEGER DEFAULT 0,
            vikriti_vata INTEGER DEFAULT 0,
            vikriti_pitta INTEGER DEFAULT 0,
            vikriti_kapha INTEGER DEFAULT 0,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    """)

    # Therapies table (Mohit Yadav)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS therapies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            therapy_name TEXT NOT NULL,
            description TEXT,
            duration_minutes INTEGER DEFAULT 60,
            cost DECIMAL(10,2) DEFAULT 0.00,
            requires_oil BOOLEAN DEFAULT 0,
            oil_quantity_ml INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Therapists table (Aniruddh Negi)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS therapists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            specialization TEXT,
            experience_years INTEGER,
            available_hours TEXT,
            max_sessions_per_day INTEGER DEFAULT 8,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # Appointments table (Mohit Yadav)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id TEXT UNIQUE NOT NULL,
            patient_id INTEGER NOT NULL,
            therapist_id INTEGER NOT NULL,
            therapy_id INTEGER NOT NULL,
            appointment_date DATE NOT NULL,
            start_time TIME NOT NULL,
            end_time TIME NOT NULL,
            status TEXT DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'completed', 'cancelled', 'rescheduled')),
            notes TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients (id),
            FOREIGN KEY (therapist_id) REFERENCES therapists (id),
            FOREIGN KEY (therapy_id) REFERENCES therapies (id),
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    """)

    # Progress notes (Aditya Mastwal)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS progress_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id INTEGER NOT NULL,
            session_notes TEXT,
            patient_response TEXT,
            therapist_observations TEXT,
            improvement_scale INTEGER CHECK (improvement_scale BETWEEN 1 AND 10),
            side_effects TEXT,
            recommendations TEXT,
            next_session_notes TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (appointment_id) REFERENCES appointments (id),
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    """)

    # Billing (Aditya Mastwal)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS billing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id TEXT UNIQUE NOT NULL,
            patient_id INTEGER NOT NULL,
            appointment_id INTEGER,
            total_amount DECIMAL(10,2) NOT NULL,
            discount_amount DECIMAL(10,2) DEFAULT 0.00,
            final_amount DECIMAL(10,2) NOT NULL,
            payment_status TEXT DEFAULT 'pending' CHECK (payment_status IN ('pending', 'paid', 'partially_paid', 'refunded')),
            payment_method TEXT,
            payment_date TIMESTAMP,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients (id),
            FOREIGN KEY (appointment_id) REFERENCES appointments (id),
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    """)

    # Inventory (Aditya Mastwal)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            item_type TEXT NOT NULL CHECK (item_type IN ('oil', 'medicine', 'consumable')),
            current_stock INTEGER DEFAULT 0,
            unit TEXT NOT NULL,
            min_stock_alert INTEGER DEFAULT 10,
            cost_per_unit DECIMAL(10,2) DEFAULT 0.00,
            supplier TEXT,
            expiry_date DATE,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Stock usage (Aditya Mastwal)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inventory_id INTEGER NOT NULL,
            appointment_id INTEGER,
            quantity_used INTEGER NOT NULL,
            usage_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            used_by INTEGER,
            FOREIGN KEY (inventory_id) REFERENCES inventory (id),
            FOREIGN KEY (appointment_id) REFERENCES appointments (id),
            FOREIGN KEY (used_by) REFERENCES users (id)
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

# =============================================================================
# USER MANAGEMENT (Aniruddh Negi)
# =============================================================================

def create_default_admin():
    """Create default admin user for initial setup"""
    conn = sqlite3.connect('ayursutra.db')
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
    if cursor.fetchone():
        conn.close()
        return

    admin_password = generate_password_hash('admin123')
    cursor.execute("""
        INSERT INTO users (username, email, password_hash, role, full_name, phone)
        VALUES (?, ?, ?, ?, ?, ?)
    """, ('admin', 'admin@ayursutra.com', admin_password, 'admin', 'System Administrator', '9999999999'))

    conn.commit()
    conn.close()
    print("✅ Default admin created successfully!")

@app.route('/')
def index():
    """Dashboard routing - Aniruddh Negi"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_role = session.get('user_role')
    if user_role == 'admin':
        return render_template('admin_dashboard.html')
    elif user_role == 'doctor':
        return render_template('admin_dashboard.html')  # Could be specialized later
    elif user_role == 'therapist':
        return render_template('admin_dashboard.html')  # Could be specialized later
    else:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login - Aniruddh Negi"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('ayursutra.db')
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, username, password_hash, role, full_name, email
            FROM users WHERE username = ? AND is_active = 1
        """, (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['user_role'] = user[3]
            session['full_name'] = user[4]
            session['email'] = user[5]
            flash(f'Welcome {user[4]}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password!', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout - Aniruddh Negi"""
    session.clear()
    flash('You have been logged out successfully!', 'info')
    return redirect(url_for('login'))

# =============================================================================
# PATIENT PROFILES (Mohit Yadav)
# =============================================================================

@app.route('/patients')
def patients_list():
    """List patients with search - Mohit Yadav"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    search_query = request.args.get('search', '')
    conn = sqlite3.connect('ayursutra.db')
    cursor = conn.cursor()

    if search_query:
        cursor.execute("""
            SELECT id, patient_id, full_name, age, gender, phone, email, created_at
            FROM patients
            WHERE full_name LIKE ? OR patient_id LIKE ? OR phone LIKE ?
            ORDER BY created_at DESC
        """, (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'))
    else:
        cursor.execute("""
            SELECT id, patient_id, full_name, age, gender, phone, email, created_at
            FROM patients ORDER BY created_at DESC
        """)

    patients = cursor.fetchall()
    conn.close()

    return render_template('patients_list.html', patients=patients, search_query=search_query)

@app.route('/add_patient', methods=['GET', 'POST'])
def add_patient():
    """Add patient with dosha assessment - Mohit Yadav"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        full_name = request.form['full_name']
        age = int(request.form['age'])
        gender = request.form['gender']
        phone = request.form['phone']
        email = request.form.get('email', '')
        address = request.form.get('address', '')
        emergency_contact = request.form.get('emergency_contact', '')
        medical_history = request.form.get('medical_history', '')
        allergies = request.form.get('allergies', '')
        contraindications = request.form.get('contraindications', '')

        prakriti_vata = int(request.form.get('prakriti_vata', 0))
        prakriti_pitta = int(request.form.get('prakriti_pitta', 0))
        prakriti_kapha = int(request.form.get('prakriti_kapha', 0))

        vikriti_vata = int(request.form.get('vikriti_vata', 0))
        vikriti_pitta = int(request.form.get('vikriti_pitta', 0))
        vikriti_kapha = int(request.form.get('vikriti_kapha', 0))

        patient_id = f"AYU{datetime.now().strftime('%Y%m%d')}{phone[-4:]}"

        try:
            conn = sqlite3.connect('ayursutra.db')
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO patients (
                    patient_id, full_name, age, gender, phone, email, address,
                    emergency_contact, medical_history, allergies, contraindications,
                    prakriti_vata, prakriti_pitta, prakriti_kapha,
                    vikriti_vata, vikriti_pitta, vikriti_kapha, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (patient_id, full_name, age, gender, phone, email, address,
                  emergency_contact, medical_history, allergies, contraindications,
                  prakriti_vata, prakriti_pitta, prakriti_kapha,
                  vikriti_vata, vikriti_pitta, vikriti_kapha, session['user_id']))

            conn.commit()
            conn.close()
            flash(f'Patient {full_name} (ID: {patient_id}) added successfully!', 'success')
            return redirect(url_for('patients_list'))
        except sqlite3.IntegrityError:
            flash('Error adding patient. Phone number might already exist!', 'danger')

    return render_template('add_patient.html')

@app.route('/patient/<int:patient_id>')
def patient_profile(patient_id):
    """View patient profile - Mohit Yadav"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('ayursutra.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.*, u.full_name as created_by_name
        FROM patients p
        LEFT JOIN users u ON p.created_by = u.id
        WHERE p.id = ?
    """, (patient_id,))
    patient = cursor.fetchone()

    if not patient:
        flash('Patient not found!', 'danger')
        return redirect(url_for('patients_list'))

    cursor.execute("""
        SELECT a.appointment_date, a.start_time, th.therapy_name,
               a.status, u.full_name as therapist_name
        FROM appointments a
        JOIN therapies th ON a.therapy_id = th.id
        JOIN therapists t ON a.therapist_id = t.id
        JOIN users u ON t.user_id = u.id
        WHERE a.patient_id = ?
        ORDER BY a.appointment_date DESC, a.start_time DESC
        LIMIT 10
    """, (patient_id,))
    recent_appointments = cursor.fetchall()

    conn.close()

    return render_template('patient_profile.html', patient=patient,
                           recent_appointments=recent_appointments)

# =============================================================================
# SCHEDULING (Mohit Yadav)
# =============================================================================

@app.route('/schedule')
def schedule_view():
    """Weekly schedule view - Mohit Yadav"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    conn = sqlite3.connect('ayursutra.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT a.*, p.full_name as patient_name, p.phone as patient_phone,
               th.therapy_name, u.full_name as therapist_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN therapies th ON a.therapy_id = th.id
        JOIN therapists t ON a.therapist_id = t.id
        JOIN users u ON t.user_id = u.id
        WHERE a.appointment_date BETWEEN ? AND ?
        ORDER BY a.appointment_date, a.start_time
    """, (week_start, week_end))
    appointments = cursor.fetchall()
    conn.close()

    return render_template('schedule.html', appointments=appointments,
                           week_start=week_start, week_end=week_end)

@app.route('/book_appointment', methods=['GET', 'POST'])
def book_appointment():
    """Book new appointment with conflict detection - Mohit Yadav"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('ayursutra.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        patient_id = int(request.form['patient_id'])
        therapist_id = int(request.form['therapist_id'])
        therapy_id = int(request.form['therapy_id'])
        appointment_date = request.form['appointment_date']
        start_time = request.form['start_time']
        notes = request.form.get('notes', '')

        cursor.execute('SELECT duration_minutes FROM therapies WHERE id = ?', (therapy_id,))
        duration = cursor.fetchone()[0]

        start_dt = datetime.strptime(f"{appointment_date} {start_time}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(minutes=duration)
        end_time = end_dt.strftime("%H:%M")

        cursor.execute("""
            SELECT id FROM appointments 
            WHERE therapist_id = ? AND appointment_date = ? 
            AND status != 'cancelled'
            AND (
                (start_time <= ? AND end_time > ?) OR
                (start_time < ? AND end_time >= ?) OR
                (start_time >= ? AND end_time <= ?)
            )
        """, (therapist_id, appointment_date, start_time, start_time,
              end_time, end_time, start_time, end_time))
        conflict = cursor.fetchone()

        if conflict:
            flash('Time slot conflict! Please choose a different time.', 'danger')
        else:
            appointment_code = f"APP{datetime.now().strftime('%Y%m%d%H%M%S')}"
            cursor.execute("""
                INSERT INTO appointments (
                    appointment_id, patient_id, therapist_id, therapy_id,
                    appointment_date, start_time, end_time, notes, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (appointment_code, patient_id, therapist_id, therapy_id,
                  appointment_date, start_time, end_time, notes, session['user_id']))
            conn.commit()
            flash('Appointment booked successfully!', 'success')
            conn.close()
            return redirect(url_for('schedule_view'))

    cursor.execute('SELECT id, patient_id, full_name FROM patients ORDER BY full_name')
    patients = cursor.fetchall()

    cursor.execute("""
        SELECT t.id, u.full_name, t.specialization
        FROM therapists t
        JOIN users u ON t.user_id = u.id
        WHERE u.is_active = 1
        ORDER BY u.full_name
    """)
    therapists = cursor.fetchall()

    cursor.execute('SELECT id, therapy_name, duration_minutes, cost FROM therapies ORDER BY therapy_name')
    therapies = cursor.fetchall()

    conn.close()
    return render_template('book_appointment.html', patients=patients,
                           therapists=therapists, therapies=therapies)

# =============================================================================
# PROGRESS TRACKING (Aditya Mastwal)
# =============================================================================

@app.route('/progress')
def progress_dashboard():
    """Progress dashboard - Aditya Mastwal"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('ayursutra.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT a.id, a.appointment_id, p.full_name as patient_name,
               th.therapy_name, a.appointment_date, a.start_time,
               CASE WHEN pn.id IS NOT NULL THEN 1 ELSE 0 END as has_progress_note
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN therapies th ON a.therapy_id = th.id
        LEFT JOIN progress_notes pn ON a.id = pn.appointment_id
        WHERE a.status = 'completed' OR a.appointment_date <= date('now')
        ORDER BY a.appointment_date DESC, a.start_time DESC
        LIMIT 20
    """)
    appointments = cursor.fetchall()
    conn.close()

    return render_template('progress_dashboard.html', appointments=appointments)

@app.route('/add_progress_note/<int:appointment_id>', methods=['GET', 'POST'])
def add_progress_note(appointment_id):
    """Add/Edit progress note - Aditya Mastwal"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('ayursutra.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT a.*, p.full_name as patient_name, th.therapy_name,
               u.full_name as therapist_name
        FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        JOIN therapies th ON a.therapy_id = th.id
        JOIN therapists t ON a.therapist_id = t.id
        JOIN users u ON t.user_id = u.id
        WHERE a.id = ?
    """, (appointment_id,))
    appointment = cursor.fetchone()

    if not appointment:
        flash('Appointment not found!', 'danger')
        return redirect(url_for('progress_dashboard'))

    if request.method == 'POST':
        session_notes = request.form['session_notes']
        patient_response = request.form['patient_response']
        therapist_observations = request.form['therapist_observations']
        improvement_scale = int(request.form.get('improvement_scale', 5))
        side_effects = request.form.get('side_effects', '')
        recommendations = request.form['recommendations']
        next_session_notes = request.form.get('next_session_notes', '')

        cursor.execute('SELECT id FROM progress_notes WHERE appointment_id = ?', (appointment_id,))
        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
                UPDATE progress_notes SET
                    session_notes = ?, patient_response = ?, therapist_observations = ?,
                    improvement_scale = ?, side_effects = ?, recommendations = ?,
                    next_session_notes = ?, created_by = ?
                WHERE appointment_id = ?
            """, (session_notes, patient_response, therapist_observations,
                  improvement_scale, side_effects, recommendations,
                  next_session_notes, session['user_id'], appointment_id))
            flash('Progress note updated successfully!', 'success')
        else:
            cursor.execute("""
                INSERT INTO progress_notes (
                    appointment_id, session_notes, patient_response, therapist_observations,
                    improvement_scale, side_effects, recommendations, next_session_notes, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (appointment_id, session_notes, patient_response, therapist_observations,
                  improvement_scale, side_effects, recommendations, next_session_notes, session['user_id']))
            flash('Progress note added successfully!', 'success')

        cursor.execute("""
            UPDATE appointments SET status = 'completed', updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND status != 'completed'
        """, (appointment_id,))
        conn.commit()
        conn.close()
        return redirect(url_for('progress_dashboard'))

    cursor.execute('SELECT * FROM progress_notes WHERE appointment_id = ?', (appointment_id,))
    existing_note = cursor.fetchone()
    conn.close()

    return render_template('add_progress_note.html', appointment=appointment, existing_note=existing_note)

# =============================================================================
# BILLING & INVENTORY (Aditya Mastwal)
# =============================================================================

@app.route('/billing')
def billing_dashboard():
    """Billing dashboard - Aditya Mastwal"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('ayursutra.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT b.*, p.full_name as patient_name, p.patient_id
        FROM billing b
        JOIN patients p ON b.patient_id = p.id
        ORDER BY b.created_at DESC
        LIMIT 50
    """)
    invoices = cursor.fetchall()

    cursor.execute("""
        SELECT 
            COUNT(*) as total_invoices,
            SUM(final_amount) as total_revenue,
            SUM(CASE WHEN payment_status = 'paid' THEN final_amount ELSE 0 END) as collected_revenue,
            SUM(CASE WHEN payment_status = 'pending' THEN final_amount ELSE 0 END) as pending_revenue
        FROM billing
        WHERE created_at >= date('now', '-30 days')
    """)
    stats = cursor.fetchone()
    conn.close()

    return render_template('billing_dashboard.html', invoices=invoices, stats=stats)

@app.route('/inventory')
def inventory_dashboard():
    """Inventory dashboard - Aditya Mastwal"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('ayursutra.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *, 
               CASE 
                   WHEN current_stock <= min_stock_alert THEN 'low' 
                   WHEN current_stock <= (min_stock_alert * 2) THEN 'medium'
                   ELSE 'good' 
               END as stock_status
        FROM inventory
        ORDER BY item_type, item_name
    """)
    inventory_items = cursor.fetchall()

    cursor.execute("""
        SELECT item_name, current_stock, min_stock_alert, item_type
        FROM inventory
        WHERE current_stock <= min_stock_alert
        ORDER BY current_stock ASC
    """)
    low_stock_items = cursor.fetchall()
    conn.close()

    return render_template('inventory_dashboard.html',
                           inventory_items=inventory_items,
                           low_stock_items=low_stock_items)

@app.route('/add_inventory_item', methods=['GET', 'POST'])
def add_inventory_item():
    """Add inventory item - Aditya Mastwal"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        item_name = request.form['item_name']
        item_type = request.form['item_type']
        current_stock = int(request.form['current_stock'])
        unit = request.form['unit']
        min_stock_alert = int(request.form['min_stock_alert'])
        cost_per_unit = float(request.form.get('cost_per_unit', 0.00))
        supplier = request.form.get('supplier', '')
        expiry_date = request.form.get('expiry_date') or None

        conn = sqlite3.connect('ayursutra.db')
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO inventory (
                item_name, item_type, current_stock, unit, min_stock_alert,
                cost_per_unit, supplier, expiry_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (item_name, item_type, current_stock, unit, min_stock_alert,
              cost_per_unit, supplier, expiry_date))

        conn.commit()
        conn.close()
        flash(f'Item {item_name} added to inventory successfully!', 'success')
        return redirect(url_for('inventory_dashboard'))

    return render_template('add_inventory_item.html')

@app.route('/update_stock/<int:item_id>', methods=['POST'])
def update_stock(item_id):
    """Update stock quantity - Aditya Mastwal"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    new_stock = int(request.form['new_stock'])

    conn = sqlite3.connect('ayursutra.db')
    cursor = conn.cursor()

    cursor.execute('SELECT current_stock FROM inventory WHERE id = ?', (item_id,))
    current_stock = cursor.fetchone()[0]

    cursor.execute("""
        UPDATE inventory SET current_stock = ?, last_updated = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (new_stock, item_id))

    if new_stock < current_stock:
        quantity_used = current_stock - new_stock
        cursor.execute("""
            INSERT INTO stock_usage (inventory_id, quantity_used, used_by)
            VALUES (?, ?, ?)
        """, (item_id, quantity_used, session['user_id']))

    conn.commit()
    conn.close()
    flash('Stock updated successfully!', 'success')
    return redirect(url_for('inventory_dashboard'))

# =============================================================================
# SETUP UTILITIES (Aniruddh Negi)
# =============================================================================

@app.route('/setup_default_data')
def setup_default_data():
    """Insert default therapies and inventory - Aniruddh Negi"""
    if 'user_id' not in session or session.get('user_role') != 'admin':
        flash('Access denied! Admin role required.', 'danger')
        return redirect(url_for('index'))

    conn = sqlite3.connect('ayursutra.db')
    cursor = conn.cursor()

    default_therapies = [
        ('Abhyanga', 'Full body oil massage with warm herbal oils', 90, 2500.00, 1, 200),
        ('Shirodhara', 'Continuous pouring of oil on forehead', 60, 3000.00, 1, 500),
        ('Pizhichil', 'Oil bath therapy with warm medicated oils', 75, 4000.00, 1, 1000),
        ('Udvartana', 'Herbal powder massage for weight reduction', 45, 2000.00, 0, 0),
        ('Nasya', 'Nasal administration of medicated oils', 30, 1500.00, 1, 50),
        ('Karna Purana', 'Ear treatment with medicated oils', 20, 1000.00, 1, 30),
        ('Akshi Tarpana', 'Eye treatment with medicated ghee', 30, 2500.00, 1, 100)
    ]
    for therapy in default_therapies:
        cursor.execute("""
            INSERT OR IGNORE INTO therapies 
            (therapy_name, description, duration_minutes, cost, requires_oil, oil_quantity_ml)
            VALUES (?, ?, ?, ?, ?, ?)
        """, therapy)

    default_inventory = [
        ('Sesame Oil', 'oil', 5000, 'ml', 1000, 15.00, 'Ayur Supplier', None),
        ('Coconut Oil', 'oil', 3000, 'ml', 500, 25.00, 'Ayur Supplier', None),
        ('Mahanarayan Oil', 'oil', 2000, 'ml', 200, 45.00, 'Ayur Supplier', None),
        ('Triphala Churna', 'medicine', 1000, 'gm', 100, 120.00, 'Herbal Co.', '2025-12-31'),
        ('Ashwagandha Tablets', 'medicine', 500, 'tablets', 50, 2.00, 'Herbal Co.', '2025-10-31'),
        ('Cotton Towels', 'consumable', 50, 'pieces', 10, 150.00, 'Textile Supplier', None),
        ('Disposable Sheets', 'consumable', 200, 'pieces', 20, 25.00, 'Medical Supplier', None)
    ]
    for item in default_inventory:
        cursor.execute("""
            INSERT OR IGNORE INTO inventory 
            (item_name, item_type, current_stock, unit, min_stock_alert, 
             cost_per_unit, supplier, expiry_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, item)

    conn.commit()
    conn.close()
    flash('Default data setup completed successfully!', 'success')
    return redirect(url_for('index'))

# =============================================================================
# ERROR HANDLERS (Aniruddh Negi)
# =============================================================================

@app.errorhandler(404)
def not_found_error(error):
    return ("404 Not Found", 404)

@app.errorhandler(500)
def internal_error(error):
    return ("500 Internal Server Error", 500)

# =============================================================================
# APPLICATION STARTUP (Aniruddh Negi)
# =============================================================================

if __name__ == '__main__':
    print("🏥 Initializing AyurSutra - Panchakarma Management System")
    print("="*70)
    print("📋 Team: Panchakarma Pioneers (ID: PY-III-T085)")
    print("="*70)
    print("👥 Responsibilities:")
    print("   🔐 Aniruddh Negi: Auth, Architecture, Utilities")
    print("   👤 Mohit Yadav: Patients, Scheduling")
    print("   📊 Aditya Mastwal: Progress, Billing, Inventory")
    print("="*70)

    init_database()
    create_default_admin()

    print("✅ System initialization completed!")
    print("🌐 http://localhost:5000")
    print("🔑 Login: admin / admin123")
    print("="*70)
    app.run(debug=True, host='0.0.0.0', port=5000)
