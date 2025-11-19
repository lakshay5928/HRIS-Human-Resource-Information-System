# app.py - HRIS Application with Payroll + Attrition Prediction + Trigger System

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from models import (
    bcrypt, seed_sample_data, find_user_by_email, insert_user,
    list_employees, list_payroll, list_attendance, get_employee_by_id,
    train_and_save_model, load_model,
    train_attrition_model, load_attrition_model,
    db
)
import os
from bson import ObjectId
import warnings
from sklearn.exceptions import DataConversionWarning
import pandas as pd

# Suppress sklearn warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DataConversionWarning)

# -------------------- FLASK INIT --------------------
app = Flask(__name__)
app.secret_key = os.urandom(24)

# -------------------- DATABASE + MODELS --------------------
# Seed DB and train both models once
seed_sample_data()
payroll_model = train_and_save_model()        # Payroll anomaly / risk model
attrition_model = train_attrition_model()     # Attrition risk model

# -------------------- TRIGGER SYSTEM --------------------
def add_trigger(event_type, message, employee_id=None):
    """Insert a trigger record in the database"""
    trigger_doc = {
        "event_type": event_type,
        "message": message,
        "employee_id": employee_id,
        "timestamp": pd.Timestamp.now().isoformat()
    }
    db.triggers.insert_one(trigger_doc)
    print(f"⚡ Trigger fired: {event_type} → {message}")

def get_recent_triggers(limit=10):
    """Get the most recent triggers"""
    return list(db.triggers.find().sort("timestamp", -1).limit(limit))

# -------------------- UTIL --------------------
def clean_mongo_docs(docs):
    """Convert MongoDB ObjectIds to strings for JSON/template safety."""
    cleaned = []
    for d in docs:
        d = dict(d)
        if "_id" in d:
            d["_id"] = str(d["_id"])
        cleaned.append(d)
    return cleaned

# -------------------- ROUTES --------------------
@app.route('/')
def index():
    return render_template('index.html')

# -------------------- HR LOGIN --------------------
@app.route('/login/hr', methods=['GET', 'POST'])
def login_hr():
    if request.method == 'POST':
        email = request.form['email']
        pwd = request.form['password']
        user = find_user_by_email(email)
        if user and user.get('role') == 'hr' and bcrypt.check_password_hash(user['password'], pwd):
            session['user'] = {'email': user['email'], 'role': 'hr', 'name': user.get('name')}
            return redirect(url_for('hr_dashboard'))
        flash('Invalid HR credentials', 'danger')
    return render_template('login_hr.html')

# -------------------- EMPLOYEE LOGIN --------------------
@app.route('/login/employee', methods=['GET', 'POST'])
def login_employee():
    if request.method == 'POST':
        email = request.form['email']
        pwd = request.form['password']
        user = find_user_by_email(email)
        if user and user.get('role') == 'employee' and bcrypt.check_password_hash(user['password'], pwd):
            session['user'] = {
                'email': user['email'],
                'role': 'employee',
                'name': user.get('name'),
                'employee_id': user.get('employee_id')
            }
            return redirect(url_for('employee_dashboard'))
        flash('Invalid employee credentials', 'danger')
    return render_template('login_employee.html')

def to_bool(value):
    """Normalize salary_pending values from DB to True/False."""
    if value is True:
        return True
    if str(value).strip().lower() in ["true", "1", "pending", "yes"]:
        return True
    return False


# -------------------- HR DASHBOARD --------------------
@app.route('/hr/dashboard')
def hr_dashboard():
    global payroll_model, attrition_model

    # Access control
    if "user" not in session or session["user"].get("role") != "hr":
        return redirect(url_for("login_hr"))

    # Fetch data
    employees = clean_mongo_docs(list_employees())
    attendance = clean_mongo_docs(list_attendance())
    real_payroll = clean_mongo_docs(list_payroll())  # REAL payroll from DB

    # ----------------------------- 
    # DYNAMIC PAYROLL FOR CHART ONLY
    # -----------------------------
    chart_payroll = [{
        "employee_id": e["employee_id"],
        "amount": e["salary"]
    } for e in employees]

    # -----------------------------
    # STATISTICS
    # -----------------------------
    total_employees = len(employees)

    # Pending payroll based on REAL payroll collection
    pending_payroll = sum(
        1 for p in real_payroll if p.get("status") == "pending"
    )

    avg_salary = sum(
        e.get("salary", 0) for e in employees
    ) / max(1, total_employees)

    # -----------------------------
    # MACHINE LEARNING PREDICTIONS
    # -----------------------------
    preds = []

    for e in employees:
        X = [[
            e.get("tenure_years", 0),
            e.get("salary", 30000),
            {"Excellent": 3, "Good": 2, "Average": 1, "Below Average": 0}
                .get(e.get("performance", "Average"), 1),
            e.get("absence_count", 0)
        ]]

        # ---- Payroll anomaly ----
        payroll_pred = int(payroll_model.predict(X)[0])

        # ---- Attrition prediction ----
        attr_prob = float(attrition_model.predict_proba(X)[0][1])
        attrition_pred = int(attr_prob > 0.5)

        preds.append({
            "employee_id": e["employee_id"],
            "name": e["name"],
            "payroll_risk": bool(payroll_pred),
            "attrition_risk": bool(attrition_pred),
            "attrition_prob": round(attr_prob, 2)
        })

        # -----------------------------
        # TRIGGERS
        # -----------------------------
        if attr_prob > 0.8:
            add_trigger(
                event_type="High Attrition Risk",
                message=f"Employee {e['name']} ({e['employee_id']}) shows {attr_prob*100:.1f}% chance of leaving.",
                employee_id=e["employee_id"]
            )

        if payroll_pred == 1:
            add_trigger(
                event_type="Payroll Anomaly",
                message=f"Payroll irregularity detected for {e['name']} ({e['employee_id']}).",
                employee_id=e["employee_id"]
            )

        if e.get("absence_count", 0) > 5:
            add_trigger(
                event_type="High Absence",
                message=f"{e['name']} ({e['employee_id']}) has {e['absence_count']} absences.",
                employee_id=e["employee_id"]
            )

    payroll_risk_count = sum(1 for r in preds if r["payroll_risk"])
    attrition_risk_count = sum(1 for r in preds if r["attrition_risk"])
    triggers = get_recent_triggers()

    return render_template(
        "hr_dashboard.html",
        employees=employees,
        payroll_chart=chart_payroll,   # for Chart.js
        payroll=real_payroll,          # real payroll records
        attendance=attendance,
        total_employees=total_employees,
        pending_payroll=pending_payroll,
        avg_salary=int(avg_salary),
        preds=preds,
        payroll_risk_count=payroll_risk_count,
        attrition_risk_count=attrition_risk_count,
        triggers=triggers
    )

# -------------------- EMPLOYEE DASHBOARD --------------------
@app.route('/employee/dashboard')
def employee_dashboard():
    if 'user' not in session or session['user'].get('role') != 'employee':
        return redirect(url_for('login_employee'))

    user_email = session['user']['email']
    user_doc = db.users.find_one({"email": user_email})
    emp = None
    if user_doc:
        emp = db.employees.find_one({"employee_id": user_doc.get('employee_id')})
    if emp and "_id" in emp:
        emp["_id"] = str(emp["_id"])
    return render_template('employee_dashboard.html', user=session['user'], employee=emp)

# -------------------- EMPLOYEE VIEW (HR SIDE) --------------------
@app.route('/employee/<eid>')
def employee_view(eid):
    if 'user' not in session or session['user'].get('role') != 'hr':
        return redirect(url_for('login_hr'))
    emp = get_employee_by_id(eid)
    payrolls = clean_mongo_docs(list(db.payroll.find({"employee_id": eid})))
    attendance = clean_mongo_docs(list(db.attendance.find({"employee_id": eid}).sort("date", 1)))
    return render_template('employee_view.html', emp=emp, payrolls=payrolls, attendance=attendance)

# -------------------- API: PAYROLL RISK --------------------
@app.route('/api/predict', methods=['POST'])
def api_predict():
    data = request.get_json() or {}
    X = [[
        int(data.get('tenure', 0)),
        int(data.get('salary', 30000)),
        int(data.get('perf_score', 1)),
        int(data.get('absence', 0))
    ]]
    pred = int(payroll_model.predict(X)[0])
    prob = float(payroll_model.predict_proba(X)[0][1]) if hasattr(payroll_model, "predict_proba") else 0.0
    return jsonify({"risk": bool(pred), "probability": round(prob, 3)})

# -------------------- API: ATTRITION RISK --------------------
@app.route('/api/attrition_predict', methods=['POST'])
def api_attrition_predict():
    data = request.get_json() or {}
    X = [[
        int(data.get('tenure', 0)),
        int(data.get('salary', 30000)),
        int(data.get('perf_score', 1)),
        int(data.get('absence', 0))
    ]]
    pred = int(attrition_model.predict(X)[0])
    prob = float(attrition_model.predict_proba(X)[0][1]) if hasattr(attrition_model, "predict_proba") else 0.0
    return jsonify({"attrition_risk": bool(pred), "probability": round(prob, 3)})

# -------------------- REGISTER --------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form.get('role', 'employee')
        hashed = bcrypt.generate_password_hash(password).decode('utf-8')
        insert_user({'name': name, 'email': email, 'password': hashed, 'role': role})
        flash('User registered. You can login now.', 'success')
        return redirect(url_for('index'))
    return render_template('register.html')

# -------------------- LOGOUT --------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# -------------------- MAIN --------------------
if __name__ == '__main__':
    app.run(debug=True)
