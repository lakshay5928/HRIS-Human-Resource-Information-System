HRIS – Human Resource Information System

A complete Human Resource Information System (HRIS) built using Python, Flask, SQLAlchemy, and HTML/CSS, providing a secure and efficient platform for managing employee data, attendance, roles, and HR workflows.

🚀 Project Overview

The HRIS (Human Resource Information System) is a web-based application that helps organizations digitally manage their workforce.
It provides separate dashboards for:

Admin/HR

Employees

The system simplifies HR operations such as employee registration, attendance tracking, profile management, leave monitoring, and more.

⭐ Features
👨‍💼 HR / Admin Features

Login with HR credentials

View all employees

Manage employee data

Approve or reject employee requests (optional future module)

Dashboard with employee statistics

Secure access to all employee details

👨‍🔧 Employee Features

Employee login

View & update their profile

Access personal dashboard

View organization information

Request updates (optional future module)

🛠️ System Features

Flask-based backend

SQLAlchemy ORM

Secure authentication

Modular folder structure

Clean UI with HTML/CSS

Session handling

Config-based secret key management

📂 Project Structure
HRIS/
│
├── app.py                     # Main application file
├── config.py                  # Config & database setup
├── models.py                  # Database models
├── requirements.txt           # Project dependencies
├── README_HRIS.md             # Documentation
│
├── static/
│   └── css/
│       └── styles.css         # Main stylesheet
│
└── templates/
    ├── base.html              # Base layout
    ├── index.html             # Home page
    ├── login_hr.html          # HR login
    ├── login_employee.html    # Employee login
    ├── register.html          # New employee registration
    ├── hr_dashboard.html      # HR dashboard
    ├── employee_dashboard.html# Employee dashboard
    └── employee_view.html     # Employee details

⚙️ Installation & Setup
1️⃣ Clone the repository
git clone https://github.com/lakshay5928/HRIS-Human-Resource-Information-System.git
cd HRIS-Human-Resource-Information-System

2️⃣ Create a virtual environment
python -m venv venv
venv\Scripts\activate     # For Windows

3️⃣ Install dependencies
pip install -r requirements.txt

4️⃣ Initialize the database

In app.py, database tables will auto-create on first run.

▶️ How to Run

Start the Flask application:

python app.py


The system will run on:

👉 http://127.0.0.1:5000

🔐 Authentication Flow

User chooses HR Login or Employee Login

Flask validates credentials using SQLAlchemy models

On success → redirected to respective dashboard

Sessions ensure secure access

🛠️ Technology Stack
Component	Technology
Backend	Python, Flask
Database	SQLAlchemy (SQLite / MySQL optional)
Frontend	HTML5, CSS3
Authentication	Flask Sessions
Deployment	Gunicorn / Render / Railway (optional)
📌 Future Enhancements

Attendance system

Leave management

Payroll integration

Export data as PDF/Excel

Role-based access control

Notification system

🤝 Contributing

Pull requests are welcome!
For major changes, please open an issue first to discuss what you’d like to modify.

📜 License

This project is open-source. Add your preferred license if needed (MIT recommended).

👤 Author

Lakshay Verma
HRIS – Human Resource Information System Developer
