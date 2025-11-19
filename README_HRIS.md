🧠 HRIS — Human Resource Information System with ML & Triggers

A full-stack **Flask-based HR Management System** with integrated **Machine Learning models** for payroll anomaly detection and employee attrition prediction.  
Includes a **trigger-based alert system**, **role-based access control**, and **MongoDB database** with **unique identifiers and referential integrity**.

## 🚀 Features

### 👥 Role-Based Access
- **HR Login** → Access employee data, payroll analytics, triggers, and ML insights.  
- **Employee Login** → View personal data, attendance, and payroll information.

### 📊 Machine Learning Modules
1. **Payroll Risk Prediction**  
   Detects payroll irregularities using RandomForestClassifier.
2. **Attrition Risk Prediction**  
   Predicts likelihood of employee resignation using HR analytics data.

### ⚡ Trigger System
- Automatically fires triggers (alerts) for:
  - High attrition probability (> 0.8)
  - Payroll anomalies
  - Excessive absences (> 5)
- Stores and displays alerts in a live “System Triggers” feed on the HR dashboard.

### 💾 Data Management
- MongoDB used for data persistence.
- Automatic data seeding for users, employees, payroll, and attendance.
- **Unique Index Constraints**:
  - `employee_id` → Primary key for employees  
  - `email` → Unique across users  
  - `(employee_id, month)` → Unique payroll entry  
  - `(employee_id, date)` → Unique attendance record  

### 🧩 Referential Integrity
- Every payroll and attendance record references a valid `employee_id`.  
- Index-level constraints prevent duplicates or orphan records.

## 🏗️ Tech Stack

| Component | Technology |
|------------|-------------|
| **Backend** | Flask (Python) |
| **Database** | MongoDB |
| **ML Models** | Scikit-learn (RandomForestClassifier) |
| **Frontend** | HTML, CSS, JS (Chart.js) |
| **Authentication** | Flask-Bcrypt |
| **Data Storage** | JSON & MongoDB collections |
| **Triggers/Alerts** | Python-based event simulation |

## ⚙️ Setup Instructions

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/yourusername/hris-flask.git
cd hris-flask
```

### 2️⃣ Create and Activate Virtual Environment
```bash
python -m venv .venv
source .venv/Scripts/activate  # for Windows
```

### 3️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

### 4️⃣ Start MongoDB
Make sure your MongoDB server is running locally:
```
mongodb://localhost:27017/
```

### 5️⃣ Run the Flask App
```bash
python app.py
```

Then open your browser:
👉 http://127.0.0.1:5000/

## 🧩 Default Accounts (Seeded Data)

### HR Users:
| Name   | Email           | Password|
|--------|-----------------|---------|
| HR One | hr1@company.com | hrpass1 |
| HR Two | hr2@company.com | hrpass2 |
| HR Three | hr3@company.com | hrpass3 |

### Employees:
|       Email      | Password |
|------------------|----------|
| emp1@company.com | emppass1 |
| emp2@company.com | emppass2 |
| ... | ... |

## 💡 Key Functionalities

### 🔹 HR Dashboard
- Employee summary (count, avg salary, pending payrolls)
- Payroll bar chart visualization
- Employee performance overview
- AI-driven “At Risk” indicators
- Trigger log panel for system alerts

### 🔹 Employee Dashboard
- Displays employee profile
- Attendance records
- Payroll history

### 🔹 Trigger Log (Real-Time)
- Logged to `db.triggers` on every dashboard load
- Example:
  ```
  ⚡ High Attrition Risk — Employee 103 (E103) 89.5% chance of leaving.
  ⚡ Payroll Anomaly — Employee 111 payroll flagged.
  ⚡ High Absence — Employee 107 has 8 absences.
  ```

## 🧠 Machine Learning Model Details

### 1. Payroll Risk Model
- **Algorithm:** RandomForestClassifier  
- **Features:** tenure, salary, performance score, absences  
- **Label:** 1 (risk) / 0 (normal)

### 2. Attrition Prediction Model
- **Algorithm:** RandomForestClassifier  
- **Features:** tenure, salary, performance, absence  
- **Label:** 1 (high attrition risk), 0 (stable)

Both models are saved under `/ml_models`:
```
payroll_risk_model.joblib
attrition_model.joblib
```

## 📈 Future Enhancements

- Add email or SMS alerts for critical triggers  
- Implement detailed analytics dashboard with filters  
- Add CRUD interfaces for HR to edit employee data  
- Cloud deployment with MongoDB Atlas  
- Add JWT-based authentication for API security

## 👨‍💻 Author

**Lakshay Verma**  
B.Tech AI & Data Science  
Project: *HRIS with Payroll + Attrition Prediction using ML*  
Mentor: *[Your Professor / Guide Name]*  

## 🏁 License

This project is licensed under the **MIT License** — feel free to use, modify, and distribute.
