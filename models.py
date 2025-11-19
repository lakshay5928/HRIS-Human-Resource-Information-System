from pymongo import MongoClient
from flask_bcrypt import Bcrypt
from config import MONGO_URI, DB_NAME
from bson import ObjectId
import os, joblib, random
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

MODEL_PATH = os.path.join(os.path.dirname(__file__), "ml_models", "payroll_risk_model.joblib")
ATTRITION_MODEL_PATH = os.path.join(os.path.dirname(__file__), "ml_models", "attrition_model.joblib")


try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
except Exception as e:
    print("❌ MongoDB connection failed:", e)
    raise

bcrypt = Bcrypt()

# Utility — convert ObjectId → str (for JSON serialization)
def fix_object_ids(data):
    if isinstance(data, list):
        return [fix_object_ids(i) for i in data]
    elif isinstance(data, dict):
        return {k: fix_object_ids(v) for k, v in data.items()}
    elif isinstance(data, ObjectId):
        return str(data)
    return data

# ---------------- Helper Function ----------------
def generate_id(prefix, counter):
    """Generate formatted unique ID like EMP001, HR001, PAY001"""
    return f"{prefix}{counter:03d}"

# SEED SAMPLE DATA
def seed_sample_data():
    # ======================================
    # UNIQUE INDEXES (Primary Key Constraints)
    # ======================================
    db.users.create_index("email", unique=True)
    db.employees.create_index("employee_id", unique=True)
    db.payroll.create_index([("employee_id", 1), ("month", 1)], unique=True)
    db.attendance.create_index([("employee_id", 1), ("date", 1)], unique=True)

    # ======================================
    # USERS (HR + Employees)
    # ======================================
    if db.users.count_documents({}) == 0:
        users = []
        # 3 HR users
        for i in range(1, 4):
            hr_id = generate_id("HR", i)
            users.append({
                "user_id": hr_id,
                "name": f"HR {i}",
                "email": f"hr{i}@company.com",
                "password": bcrypt.generate_password_hash(f"hrpass{i}").decode("utf-8"),
                "role": "hr"
            })

        # 20 employee users
        for i in range(1, 21):
            eid = generate_id("E", 100 + i)
            users.append({
                "user_id": eid,
                "name": f"Employee {i}",
                "email": f"emp{i}@company.com",
                "password": bcrypt.generate_password_hash(f"emppass{i}").decode("utf-8"),
                "role": "employee",
                "employee_id": eid
            })
        db.users.insert_many(users)

    # ======================================
    # EMPLOYEES
    # ======================================
    if db.employees.count_documents({}) == 0:
        employees = []
        random.seed(42)
        for i in range(1, 21):
            eid = generate_id("E", 100 + i)
            dept = random.choice(["Sales", "HR", "Dev", "Support", "Finance", "Marketing"])
            salary = random.choice([30000, 35000, 40000, 45000, 50000, 55000, 60000])
            tenure = random.randint(0, 10)
            perf = random.choice(["Excellent", "Good", "Average", "Below Average"])
            absence = random.randint(0, 8)
            pending = random.choice([False, False, False, True])
            employees.append({
                "employee_id": eid,
                "name": f"Employee {i}",
                "department": dept,
                "salary": salary,
                "tenure_years": tenure,
                "performance": perf,
                "absence_count": absence,
                "salary_pending": pending
            })
        db.employees.insert_many(employees)

    # ======================================
    # PAYROLL
    # ======================================
    if db.payroll.count_documents({}) == 0:
        payrolls = []
        for idx, e in enumerate(db.employees.find(), start=1):
            eid = e.get("employee_id")
            payroll_id = generate_id("PAY", idx)
            amount = e.get("salary", 30000)
            status = random.choice(["processed", "pending"])
            payrolls.append({
                "payroll_id": payroll_id,
                "employee_id": eid,  # FK-like link
                "month": "2025-09",
                "amount": amount,
                "status": status
            })
        db.payroll.insert_many(payrolls)

    # ======================================
    # ATTENDANCE
    # ======================================
    if db.attendance.count_documents({}) == 0:
        attendance = []
        for idx, e in enumerate(db.employees.find(), start=1):
            eid = e.get("employee_id")
            for d in range(1, 11):
                att_id = generate_id("ATT", idx * 10 + d)
                status = random.choice(["present"] * 8 + ["absent"] * 2)
                attendance.append({
                    "attendance_id": att_id,
                    "employee_id": eid,  # FK-like link
                    "date": f"2025-09-{d:02d}",
                    "status": status
                })
        db.attendance.insert_many(attendance)

#DB ACCESS HELPERS
def find_user_by_email(email):
    return db.users.find_one({"email": email})

def insert_user(user_doc):
    return db.users.insert_one(user_doc)

def get_employee_by_id(eid):
    emp = db.employees.find_one({"employee_id": eid})
    return fix_object_ids(emp)

def list_employees():
    return fix_object_ids(list(db.employees.find()))

def list_payroll():
    return fix_object_ids(list(db.payroll.find()))

def list_attendance():
    return fix_object_ids(list(db.attendance.find()))

#MACHINE LEARNING MODEL
# PAYROLL ANOMALY DETECTION MODEL
def train_and_save_model(force=False):
    """
    Train a Machine Learning model to detect payroll anomalies
    based on employee performance, salary, tenure, and absence behaviour.
    """

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

    # Load existing model unless force retraining
    if os.path.exists(MODEL_PATH) and not force:
        try:
            return joblib.load(MODEL_PATH)
        except Exception as e:
            print("⚠️ Payroll model load failed, retraining…", e)

    # Fetch employees data from DB
    employees = list_employees()
    rows = []

    for e in employees:
        tenure = int(e.get("tenure_years", 0))
        salary = int(e.get("salary", 30000))
        absence = int(e.get("absence_count", 0))
        perf = e.get("performance", "Average")
        salary_pending = int(e.get("salary_pending", False))

        perf_score = {
            "Excellent": 3,
            "Good": 2,
            "Average": 1,
            "Below Average": 0
        }.get(perf, 1)

        # -----------------------------
        # LABEL DEFINITION (Anomaly = 1)
        # -----------------------------
        # Payroll anomaly conditions:
        #
        # 1. Salary pending
        # 2. Absences >= 7
        # 3. Very low performance
        # 4. Salary mismatch (performance low but salary very high)
        #
        label = 1 if (
            salary_pending == 1 or
            absence >= 7 or
            perf_score == 0 or
            (perf_score <= 1 and salary > 60000)
        ) else 0

        rows.append([tenure, salary, perf_score, absence, label])

    # Convert to DataFrame
    df = pd.DataFrame(rows,
                      columns=["tenure", "salary", "perf_score", "absence", "label"])

    # Safety backup dataset
    if len(df) < 5:
        df = pd.DataFrame({
            "tenure": [1, 2, 3, 4, 5, 6, 2, 3],
            "salary": [30000, 40000, 60000, 45000, 35000, 75000, 32000, 41000],
            "perf_score": [2, 3, 0, 2, 3, 0, 0, 2],
            "absence": [0, 1, 10, 2, 0, 9, 4, 1],
            "label": [0, 0, 1, 0, 0, 1, 1, 0]     # 1 = anomaly
        })

    # Train model
    X = df[["tenure", "salary", "perf_score", "absence"]]
    y = df["label"]

    model = RandomForestClassifier(n_estimators=120,
                                   max_depth=6,
                                   random_state=42)
    model.fit(X, y)

    # Save model
    joblib.dump(model, MODEL_PATH)
    print("✅ Payroll Anomaly Model Trained & Saved:", MODEL_PATH)

    return model



def load_model():
    """Load the payroll anomaly model."""
    if os.path.exists(MODEL_PATH):
        try:
            return joblib.load(MODEL_PATH)
        except:
            return train_and_save_model(force=True)
    return train_and_save_model(force=True)


# ATTRITION PREDICTION MODEL
def train_attrition_model(force=False):
    """
    Train a Machine Learning model to predict employee attrition (likelihood of leaving).
    Model uses performance, salary, tenure, and attendance behavior.
    """

    os.makedirs(os.path.dirname(ATTRITION_MODEL_PATH), exist_ok=True)

    # Load existing model unless force retrain
    if os.path.exists(ATTRITION_MODEL_PATH) and not force:
        try:
            return joblib.load(ATTRITION_MODEL_PATH)
        except Exception as e:
            print("⚠️ Attrition model load failed, retraining…", e)

    employees = list_employees()
    rows = []

    # Convert employee records to feature rows
    for e in employees:
        tenure = int(e.get("tenure_years", 0))
        salary = int(e.get("salary", 30000))
        absence = int(e.get("absence_count", 0))
        performance = e.get("performance", "Average")

        perf_score = {
            "Excellent": 3,
            "Good": 2,
            "Average": 1,
            "Below Average": 0
        }.get(performance, 1)

        # -------------------------------
        # Attrition Label (1 = high risk)
        # -------------------------------
        # Realistic HR attrition factors:
        #  1. Tenure <= 1 year (new employees leave more often)
        #  2. Low performance
        #  3. High absences
        #  4. Salary too low for their job profile
        #
        label = 1 if (
            tenure <= 1 or
            perf_score == 0 or
            absence >= 6 or
            (performance == "Below Average" and salary < 35000)
        ) else 0
        rows.append([tenure, salary, perf_score, absence, label])
    df = pd.DataFrame(rows, columns=["tenure", "salary", "perf_score", "absence", "label"])
    # Safety fallback dataset
    if len(df) < 5:
        df = pd.DataFrame({
            "tenure": [0, 1, 2, 3, 5, 7, 1, 0],
            "salary": [28000, 35000, 45000, 60000, 70000, 80000, 32000, 30000],
            "perf_score": [0, 1, 2, 3, 2, 3, 0, 1],
            "absence": [7, 4, 2, 0, 1, 0, 8, 5],
            "label": [1, 1, 0, 0, 0, 0, 1, 1]
        })
    # Train the attrition model
    X = df[["tenure", "salary", "perf_score", "absence"]]
    y = df["label"]
    model = RandomForestClassifier(
        n_estimators=120,
        max_depth=6,
        random_state=42
    )
    model.fit(X, y)
    # Save model
    joblib.dump(model, ATTRITION_MODEL_PATH)
    print("✅ Attrition Model Trained & Saved:", ATTRITION_MODEL_PATH)
    return model


def load_attrition_model():
    if os.path.exists(ATTRITION_MODEL_PATH):
        try:
            return joblib.load(ATTRITION_MODEL_PATH)
        except:
            return train_attrition_model(force=True)

    return train_attrition_model(force=True)



def add_trigger(event_type, message, employee_id=None):
    """Insert a trigger record in the database"""
    trigger_doc = {
        "event_type": event_type,  # e.g., 'High Attrition Risk'
        "message": message,
        "employee_id": employee_id,
        "timestamp": pd.Timestamp.now().isoformat()
    }
    db.triggers.insert_one(trigger_doc)
    print(f"⚡ Trigger fired: {event_type} → {message}")
