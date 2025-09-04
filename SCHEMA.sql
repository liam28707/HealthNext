CREATE DATABASE medical_db;

USE medical_db;

CREATE TABLE doctors (
    doctor_id INT AUTO_INCREMENT PRIMARY KEY,
    doctor_name VARCHAR(100) NOT NULL UNIQUE,
    field VARCHAR(100),
    school VARCHAR(100),
    degree VARCHAR(100),
    contact_number VARCHAR(15),
    email VARCHAR(100)
);

CREATE TABLE patients (
    patient_id INT AUTO_INCREMENT PRIMARY KEY,
    patient_name VARCHAR(100) NOT NULL,
    date_of_admission DATETIME DEFAULT CURRENT_TIMESTAMP,  
    doctor_assigned VARCHAR(100),
    contact_number VARCHAR(15),
    address TEXT,
    email VARCHAR(100),
    FOREIGN KEY (doctor_assigned) REFERENCES doctors(doctor_name)
);

CREATE TABLE operations (
    operation_id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT,
    doctor_assigned VARCHAR(100),
    operation_date DATE,
    operation_time TIME,
    operation_description TEXT,
    operation_status ENUM('Scheduled', 'In Progress', 'Completed', 'Cancelled') DEFAULT 'Scheduled',
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    FOREIGN KEY (doctor_assigned) REFERENCES doctors(doctor_name)
);

CREATE TABLE beds (
    bed_id INT AUTO_INCREMENT PRIMARY KEY,
    bed_number INT NOT NULL,
    ward VARCHAR(50),
    status ENUM('Available', 'Occupied') DEFAULT 'Available'
);
CREATE TABLE diseases (
    disease_id INT AUTO_INCREMENT PRIMARY KEY,
    disease_name VARCHAR(100) NOT NULL UNIQUE
);
CREATE TABLE patient_diseases (
    patient_id INT,
    disease_id INT,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    FOREIGN KEY (disease_id) REFERENCES diseases(disease_id)
);

