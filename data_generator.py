import mysql.connector as connector
import random
from datetime import datetime, timedelta

PASSWD = ""

# List of random names
names = ["John Doe", "Jane Doe", "Alex Smith", "Emily Davis", "Michael Johnson",
         "Sarah Brown", "David Wilson", "Laura Moore", "James Taylor", "Emma Martinez",
         "Daniel Anderson", "Sophia Harris", "Matthew Clark", "Olivia Rodriguez",
         "Joshua Lewis", "Ava Walker", "Ethan Hall", "Isabella Allen", "Jacob Allen",
         "Mia Martinez", "Mason Wilson", "Lucas Moore", "Charlotte Brown", "Amelia Johnson",
         "Benjamin Davis", "Harper Smith", "Evelyn Taylor", "Jackson Anderson", "Henry Harris",
         "Jack Martinez", "Liam Walker", "Elijah Hall", "William Allen", "Sophia Harris",
         "Oliver Lewis", "Mason Clark", "Jacob Hall", "Emma Taylor", "Olivia Rodriguez",
         "James Martinez", "Charlotte Moore", "Benjamin Johnson", "Lucas Wilson", "Amelia Harris",
         "Harper Brown", "Evelyn Davis", "Daniel Walker", "Michael Allen", "Sarah Lewis"]

# List of doctors
doctors = [
    "Dr. Alice Smith", "Dr. Bob Johnson", "Dr. Carol Williams", "Dr. David Brown",
    "Dr. Emma Jones", "Dr. Frank Miller", "Dr. Grace Wilson", "Dr. Henry Moore",
    "Dr. Ivy Taylor", "Dr. Jack Anderson", "Dr. Karen Thomas", "Dr. Louis Martinez",
    "Dr. Mona Harris", "Dr. Nathan Clark", "Dr. Olivia Rodriguez", "Dr. Paul Lewis",
    "Dr. Quincy Lee", "Dr. Rachel Walker", "Dr. Steven Hall", "Dr. Tina Allen"
]

# List of diseases
diseases = ["Diabetes", "Hypertension", "Asthma", "Cancer", "COVID-19",
            "Arthritis", "Heart Disease", "Stroke", "Depression", "Anxiety"]

def connect_to_db(PASSWD):
    db = connector.connect(host="localhost", user="root", passwd=PASSWD, db="medical_db")
    cursor = db.cursor()
    cursor.execute("USE medical_db")
    return db, cursor

def fetch_stats():
    db, cursor = connect_to_db(PASSWD)
    stats = []

    cursor.execute("SELECT COUNT(*) FROM patients;")
    patients = cursor.fetchone()
    stats.append(patients[0])

    cursor.execute("SELECT COUNT(*) FROM doctors;")
    doctors = cursor.fetchone()
    stats.append(doctors[0])

    cursor.execute("SELECT COUNT(*) FROM operations;")
    operations = cursor.fetchone()
    stats.append(operations[0])
    db.close()

    return stats

def store_patient_data(data):
    db, cursor = connect_to_db(PASSWD)
    statement = """INSERT INTO patients 
                   (patient_name, doctor_assigned, contact_number, address, email, age, gender, dob, disease) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
    cursor.executemany(statement, data)
    db.commit()
    cursor.close()
    db.close()
    print("Successful")

# Function to generate random contact number
def generate_contact():
    prefix = random.choice(["+971 60", "+971 65", "+971 67"])
    number = ''.join([str(random.randint(0, 9)) for _ in range(7)])
    return f"{prefix} {number}"

# Function to generate random address
def generate_address():
    streets = ["Elm St.", "Maple St.", "Oak St.", "Pine St.", "Cedar St."]
    cities = ["Springfield", "Riverside", "Greenville", "Franklin", "Fairview"]
    states = ["NY", "CA", "TX", "FL", "IL"]
    return f"{random.randint(1, 999)} {random.choice(streets)}, {random.choice(cities)}, {random.choice(states)}"

# Function to generate random email
def generate_email(name):
    return f"{name.lower().replace(' ', '.')}@email.com"

# Function to calculate age from dob
def calculate_age(dob):
    today = datetime.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

# Function to generate random dob
def generate_dob():
    start_date = datetime.strptime('1950-01-01', '%Y-%m-%d')
    end_date = datetime.strptime('2023-01-01', '%Y-%m-%d')
    random_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
    return random_date

# Generating the list of tuples
def generate_data():
    patients_data = []
    count = int(input("Enter number of records to be inserted: "))
    for _ in range(count):
        name = random.choice(names)
        doctor = random.choice(doctors)
        contact = generate_contact()
        address = generate_address()
        email = generate_email(name)
        dob = generate_dob()
        age = calculate_age(dob)
        gender = random.choice(["Male", "Female"])
        disease = random.choice(diseases)
        patients_data.append((name, doctor, contact, address, email, age, gender, dob.strftime('%Y-%m-%d'), disease))
    
    return patients_data

# Generate data and store in the database
r = generate_data()
store_patient_data(r)