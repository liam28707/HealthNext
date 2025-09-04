import sys
import os
import random 
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QFont, QPixmap
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.patheffects as path_effects
import matplotlib.dates as mdates
import mysql.connector as connector
from mysql.connector import Error
from datetime import datetime
import numpy as np
import seaborn as sns
from matplotlib.colors import ListedColormap


# Constants
BACKGROUND_COLOR = "#eff3ff"
DARK_BACKGROUND_COLOR = "#04207d"
BUTTON_HOVER_COLOR = "#021249"
GREY = "#6e6e6c"
ACTIVE_BUTTON_COLOR = "#04207d"
BUTTON_HEIGHT = 50
ICON_SIZE = QSize(32, 32)
FONT_SIZE = 16
STAT_BOX_WIDTH = 200
STAT_BOX_HEIGHT = 120
SCALE_FACTOR = 0.83 # FOR GRAPH PLACEHOLDERS
PASSWD = ""


# HELPER FUNCTIONS(SQL)
def connect_to_db(PASSWD):
    db = connector.connect(host = "localhost", user = "root",passwd = PASSWD, db = "medical_db")
    cursor = db.cursor()
    cursor.execute("USE medical_db")
    return db,cursor

def extract_doctor_names():
    names = []
    db,cursor = connect_to_db(PASSWD)
    statement = "SELECT doctor_name from doctors;"
    cursor.execute(statement)
    R = cursor.fetchall()
    for i in R:
        names.append(i[0])
    return names

def fetch_top_doctors():
    db,cursor = connect_to_db(PASSWD)
    query = """
    SELECT d.doctor_name, COUNT(p.patient_id) AS patient_count
    FROM patients p
    JOIN doctors d ON p.doctor_assigned = d.doctor_name
    GROUP BY d.doctor_name
    ORDER BY patient_count DESC
    LIMIT 5
    """
    cursor.execute(query)
    result = cursor.fetchall()
    db.close()
    return result

def fetch_patient_history():
    try:
        db,cursor = connect_to_db(PASSWD)
        query_new_patients = """
        SELECT DATE(date_of_admission) AS date, COUNT(*) AS new_patients
        FROM patients
        GROUP BY DATE(date_of_admission);
        """
        cursor.execute(query_new_patients)
        new_patients_data = cursor.fetchall()

        query_old_patients = """
        SELECT DATE(date_of_admission) AS date, COUNT(*) AS old_patients
        FROM patients
        WHERE date_of_admission < CURDATE()
        GROUP BY DATE(date_of_admission);
        """
        cursor.execute(query_old_patients)
        old_patients_data = cursor.fetchall()

    except Error as e:
        print(f"Error: {e}")
        return [], [], []

    finally:
        if db.is_connected():
            cursor.close()
            db.close()
    
    # Transform data into lists
    dates = [row[0] for row in new_patients_data]
    new_counts = [row[1] for row in new_patients_data]
    old_counts = [row[1] for row in old_patients_data]
    
    return dates, new_counts, old_counts

def store_patient_data(name,age,gender,doctor,dob,contact,address,email,disease):
        db,cursor = connect_to_db(PASSWD)
        statement = """ INSERT INTO patients (patient_name, doctor_assigned,contact_number,address,email,age,gender,dob,disease) VALUES (%s, %s, %s, %s, %s, %s, %s, %s,%s)"""
        data = (name, doctor, contact, address, email, age, gender, dob, disease)
        cursor.execute(statement,data)
        db.commit()
        cursor.close()

        db.close()

def store_doctor_data(name,dob,age,field,degree,contact,email):
    db,cursor = connect_to_db(PASSWD)
    statement = """ INSERT INTO doctors (doctor_name,age,field,degree,contact_number,email,dob) VALUES (%s,%s,%s,%s,%s,%s,%s)"""
    data = (name,age,field,degree,contact,email,dob)
    cursor.execute(statement,data)
    db.commit()
    cursor.close()
    db.close()

def fetch_stats():
    db,cursor = connect_to_db(PASSWD)
    cursor = db.cursor()
    stats = []

    cursor.execute("SELECT COUNT(*) FROM patients;")
    patients = cursor.fetchone()
    stats.append(patients[0])

    cursor.execute("SELECT COUNT(*) FROM doctors;")
    doctors = cursor.fetchone()
    stats.append(doctors[0])

    cursor.execute("SELECT SUM(capacity) - SUM(current_occupancy) FROM rooms;")
    rooms = cursor.fetchone()
    stats.append(rooms[0])

    cursor.execute("SELECT SUM(current_occupancy) FROM rooms WHERE room_type = 'Operation Theatre';")
    operations = cursor.fetchone()
    stats.append(operations[0])
    db.close()

    return stats

def fetch_disease_counts():
    db,cursor = connect_to_db(PASSWD)
    cursor.execute("SELECT disease, COUNT(*) FROM patients GROUP BY disease")
    result = cursor.fetchall()
    db.close()
    return result

def fetch_patient_history():
    db, cursor = connect_to_db(PASSWD)
    try:
        cursor.execute("SELECT DATE(date_of_admission) as date, COUNT(*) as count FROM patients GROUP BY DATE(date_of_admission)")
        result = cursor.fetchall()
        return [(row[0], row[1]) for row in result]
    except Error as e:
        print(f"Error: {e}")
        return []
    finally:
        db.close()

def fetch_patients_per_day():
    db, cursor = connect_to_db(PASSWD)
    try:
        cursor.execute("SELECT DATE(date_of_admission) as date, COUNT(*) as count FROM patients GROUP BY DATE(date_of_admission)")
        result = cursor.fetchall()
        return [(row[0], row[1]) for row in result]
    finally:
        db.close()

def allocate_bed(patient_id, room_type):
    db,cursor = connect_to_db(PASSWD)
    cursor = db.cursor(dictionary=True)
    
    # Find a room with an available bed
    cursor.execute("SELECT * FROM rooms WHERE room_type = %s AND occupied_beds < total_beds LIMIT 1", (room_type,))
    room = cursor.fetchone()

    if room:
        cursor.execute("UPDATE rooms SET occupied_beds = occupied_beds + 1 WHERE room_id = %s", (room['room_id'],))
        db.commit()

        # Insert the patient assignment into the bed allocation table (if needed)
        cursor.execute("INSERT INTO bed_allocations (room_id, patient_id) VALUES (%s, %s)", (room['room_id'], patient_id))
        db.commit()
    
    cursor.close()


# HELPER CLASSES
class BarChartCanvas(FigureCanvas):
    def __init__(self, parent=None):
        # Define figure size in inches (width, height)
        figsize = (12, 6)  # Example size, adjust as needed
        fig, self.ax = plt.subplots(figsize=figsize)
        super().__init__(fig)
        self.setParent(parent)
        self.figure.tight_layout(pad=3.0)  # Adjust padding to ensure the plot is centered

    def plot_bar_chart(self, data):
        self.ax.clear()
        doctors, counts = zip(*data)
        
        # Create horizontal bars
        bars = self.ax.barh(doctors, counts, color='#04207d', edgecolor='none')
        
        # Add text labels inside the bars
        for bar, doctor, count in zip(bars, doctors, counts):
            width = bar.get_width()
            bar_label = bar.get_y() + bar.get_height() / 2
            
            # Place the doctor's name inside the bar
            self.ax.text(width / 2, bar_label, 
                         doctor,  # Display the name inside the bar
                         va='center', 
                         ha='center', 
                         color='white',  # Text color
                         fontsize=10,
                         fontweight='bold',
                         path_effects=[path_effects.withStroke(linewidth=3, foreground='black')])  # Black outline for text

            # Add the number of patients right next to the end of the bar
            self.ax.text(width, bar_label,  # Adjust the 5 units if needed
                         f'{int(count)}', 
                         va='center', 
                         ha='left', 
                         color='white', 
                         fontsize=10,
                         fontweight='bold',
                         path_effects=[path_effects.withStroke(linewidth=3, foreground='black')])  # Black outline for text

        # Remove y-tick labels to clear names beside the graph
        self.ax.set_yticklabels([])
        self.ax.set_yticks([])  # Ensure y-ticks are also removed
        
        # Style the plot
        self.ax.set_ylabel('')
        self.ax.set_xlabel('No of patients', fontsize=12, fontweight='bold', color='#04207d')  # Label for x-axis
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['left'].set_visible(True)
        self.ax.spines['bottom'].set_visible(True)
        self.ax.spines['left'].set_color('#04207d')
        self.ax.spines['bottom'].set_color('#04207d')
        self.ax.spines['left'].set_linewidth(1)
        self.ax.spines['bottom'].set_linewidth(1)

        # Hide labels and ticks
        self.ax.xaxis.set_tick_params(width=1, color='#04207d')
        self.ax.yaxis.set_visible(False)
        
        # Center the plot
        self.figure.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)  # Adjust spacing around the plot

        self.draw()

class PieChartCanvas(FigureCanvas):
    def __init__(self, parent=None):
        fig, self.ax = plt.subplots()
        super().__init__(fig)
        self.setParent(parent)
        self.ax.set_title('Major Diseases')

    def plot_pie_chart(self, data, threshold=5):
        self.ax.clear()
        labels = []
        sizes = []

        for disease, count in data:
            if count > threshold:
                labels.append(disease)
                sizes.append(count)

        # Plot the pie chart without percentages
        self.ax.pie(sizes, labels=labels, autopct=lambda p: '', startangle=140)
        self.draw()

class PatientHistoryCanvas(FigureCanvas):
    def __init__(self, parent=None):
        fig, self.ax = plt.subplots(figsize=(10, 4))
        super().__init__(fig)
        self.setParent(parent)
        self.setStyleSheet("background-color: #ffffff; border-radius: 25px;")
        self.plot_line_chart([])

    def plot_line_chart(self, data):
        self.ax.clear()
        dates, counts = zip(*data) if data else ([], [])
        
        self.ax.plot(dates, counts, marker='o', linestyle='-', color='#04207d')
        
        # Format the x-axis to display dates in a shortened format
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
        self.ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
        
        # Rotate and align the x-axis labels for better readability
        plt.setp(self.ax.get_xticklabels(), rotation=0, ha='center', fontsize=10, color='#04207d')
        
        # Remove axis labels
        self.ax.set_xlabel('')
        self.ax.set_ylabel('')
        
        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['left'].set_visible(False)
        self.ax.spines['bottom'].set_visible(False)
        self.ax.xaxis.set_tick_params(width=0)
        self.ax.yaxis.set_tick_params(width=0)
        
        self.draw()

class PatientsPerDayCanvas(FigureCanvas):
    def __init__(self, parent=None):
        fig, self.ax = plt.subplots(figsize=(12, 5))
        super().__init__(fig)
        self.setParent(parent)
        self.setStyleSheet("background-color: #ffffff; border-radius: 25px;")
        self.plot_heatmap([])

    def plot_heatmap(self, data):
        self.ax.clear()

        if not data:
            # No data, show an empty heatmap
            empty_data = np.zeros((1, 7))
            sns.heatmap(empty_data, ax=self.ax, cmap=ListedColormap(sns.color_palette("Blues", 10)), cbar=False)
            self.ax.set_xticks(np.arange(0.5, 7, 1))
            self.ax.set_xticklabels(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], fontsize=12)
            self.ax.set_yticks([0.5])
            self.ax.set_yticklabels(['No Data'], fontsize=12)
            self.ax.set_ylabel('Week', fontsize=12)
            self.ax.set_xlabel('Day of Week', fontsize=12)
        else:
            # Process and plot data
            dates, counts = zip(*data)
            dates = np.array(dates, dtype='datetime64[D]')
            min_date, max_date = dates.min(), dates.max()
            date_range = np.arange(min_date, max_date + np.timedelta64(1, 'D'), dtype='datetime64[D]')
            heatmap_data = np.zeros(len(date_range), dtype=int)

            for date, count in data:
                index = np.where(date_range == np.datetime64(date, 'D'))[0][0]
                heatmap_data[index] = count

            # Pad the heatmap data to make its length a multiple of 7
            if len(heatmap_data) % 7 != 0:
                padding = 7 - (len(heatmap_data) % 7)
                heatmap_data = np.pad(heatmap_data, (0, padding), mode='constant', constant_values=0)

            heatmap_data = heatmap_data.reshape(-1, 7)
            sns.heatmap(heatmap_data, ax=self.ax, cmap=ListedColormap(sns.color_palette("Blues", 10)), cbar=False)

            self.ax.set_xticks(np.arange(0.5, 7, 1))
            self.ax.set_xticklabels(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], fontsize=12)
            self.ax.set_yticks(np.arange(0.5, len(heatmap_data), 1))
            self.ax.set_yticks([])
            self.ax.set_yticklabels([])
            self.ax.set_xlabel('Day of Week', fontsize=12)

        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.spines['left'].set_visible(False)
        self.ax.spines['bottom'].set_visible(False)

        self.draw()

class AnimatedButton(QPushButton):

    def __init__(self, label, iconPath, activeIconPath=None):
        super().__init__(label)
        self.defaultIconPath = iconPath
        self.activeIconPath = activeIconPath or iconPath
        self.setIcon(QIcon(self.defaultIconPath))
        self.setIconSize(ICON_SIZE)
        self.setFont(QFont('Poppins', FONT_SIZE, QFont.Bold))
        self.setFixedHeight(BUTTON_HEIGHT)

        # Initial styles
        self.defaultStyle = self.getButtonStyle()
        self.hoverStyle = self.getButtonStyle(hover=True)
        self.activeStyle = self.getButtonStyle(active=True)
        self.setStyleSheet(self.defaultStyle)

    def getButtonStyle(self, hover=False, active=False):
        """Return the button style based on the state."""
        if active:
            backgroundColor = DARK_BACKGROUND_COLOR
            textColor = "#ffffff"
        else:
            backgroundColor = ACTIVE_BUTTON_COLOR if hover else BACKGROUND_COLOR
            textColor = "#ffffff" if hover else GREY
        return f"""
            QPushButton {{
                text-align: left; 
                padding: 10px;
                margin: 0px 10px; 
                background-color: {backgroundColor}; 
                color: {textColor};
                border: none;
                border-radius: 15px;
                font-size: {FONT_SIZE}px;
                font-weight: bold;
            }} """

class StatBox(QWidget):
    """Custom widget to represent a statistic with an icon and label."""

    def __init__(self, iconPath, statName, statValue):
        super().__init__()
        self.statValueLabel = QLabel()
        self.initUI(iconPath, statName, statValue)

    def initUI(self, iconPath, statName, statValue):
        # Main layout for the stat box
        mainLayout = QHBoxLayout()
        mainLayout.setContentsMargins(10, 10, 10, 10)
        mainLayout.setSpacing(5)

        # Background box
        bg_box = QWidget()
        bg_box_layout = QHBoxLayout(bg_box)
        bg_box_layout.setContentsMargins(10, 10, 10, 10)
        bg_box_layout.setSpacing(5)
        bg_box.setStyleSheet("background-color: #ffffff; border-radius: 15px;")

        # Icon
        iconLabel = QLabel()
        iconLabel.setPixmap(QPixmap(iconPath).scaled(64, 64, Qt.KeepAspectRatio))
        iconLabel.setAlignment(Qt.AlignCenter)
        bg_box_layout.addWidget(iconLabel)

        # Stat name and value in a vertical layout
        statLayout = QVBoxLayout()
        statLayout.setContentsMargins(0, 0, 0, 0)
        statLayout.setSpacing(5)

        # Stat name
        statNameLabel = QLabel(statName)
        statNameLabel.setFont(QFont('Poppins', 10))
        statNameLabel.setStyleSheet(f"color: {GREY};")
        statNameLabel.setAlignment(Qt.AlignRight)
        statLayout.addWidget(statNameLabel)

        # Stat value
        self.statValueLabel.setText(statValue)
        self.statValueLabel.setFont(QFont('Poppins', 18, QFont.Bold))
        self.statValueLabel.setStyleSheet(f"color: {DARK_BACKGROUND_COLOR};")
        self.statValueLabel.setAlignment(Qt.AlignRight)
        statLayout.addWidget(self.statValueLabel)

        bg_box_layout.addLayout(statLayout)
        
        # Add the background box to the main layout
        mainLayout.addWidget(bg_box)

        self.setLayout(mainLayout)
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                padding: 0px;
                margin: 0px;
            }
        """)
        self.setFixedSize(STAT_BOX_WIDTH * 1.7, STAT_BOX_HEIGHT)

    def update_stat_value(self, new_value):
        self.statValueLabel.setText(new_value)

class AddPatient(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add a Patient")
        self.setFixedSize(800, 630)
        self.setStyleSheet("""
            QDialog {
                background-color: #eff3ff;
            }
            QLabel {
                font-family: 'Poppins';
                font-size: 18px;
                font-weight: Bolder;
                padding-top:8px;
            }
            QLineEdit, QDateEdit, QComboBox {
                background-color: #ffffff;
                border: 1px solid #dcdcdc;
                border-radius: 15px;
                padding: 10px;
                height: 35px;
                font-family: 'Poppins';
                font-size: 18px;
            }
            QLineEdit:focus, QDateEdit:focus, QComboBox:focus {
                border: 1px solid #04207d;
            }
            QPushButton {
                background-color: #04207d;
                color: #ffffff;
                border-radius: 15px;
                font-weight: bold;
                height: 40px;
            }
            QPushButton:hover {
                background-color: #021249;
            }
            QComboBox {
                padding-left: 10px;
                font-family: 'Poppins';
                font-size: 18px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                selection-background-color: #04207d;
                selection-color: #ffffff;
            }
            QComboBox::drop-down {
                background-color:#04207d;
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border-left-width: 1px;
                border-left-color: #dcdcdc;
                border-left-style: solid;
                border-top-right-radius: 15px;
                border-bottom-right-radius: 15px;
            }
            QComboBox::down-arrow {
                image: url(assets/down.png);  
                width: 15px;
                height: 15px;
            }
            QComboBox QScrollBar:vertical {
                border: none;
                background: #f9faff;
                width: 12px;
                margin: 0px 0px 0px 0px;
                border-radius: 15px;
            }
            QComboBox QScrollBar::handle:vertical {
                background: #04207d;
                min-height: 20px;
                border-radius: 6px;
            }
            QComboBox QScrollBar::add-line:vertical {
                border: none;
                background: #dcdcdc;
                height: 10px;
                subcontrol-position: bottom;
                subcontrol-origin: margin;
                border-bottom-left-radius: 6px;
                border-bottom-right-radius: 6px;
            }
            QComboBox QScrollBar::sub-line:vertical {
                border: none;
                background: #dcdcdc;
                height: 10px;
                subcontrol-position: top;
                subcontrol-origin: margin;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QDateEdit::drop-down {
                background-color:#04207d;
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border-left-width: 1px;
                border-left-color: #dcdcdc;
                border-left-style: solid;
                border-top-right-radius: 15px;
                border-bottom-right-radius: 15px;
            }
            QDateEdit::down-arrow {
                image: url(assets/down.png);  
                width: 15px;
                height: 15px;
            }
            QDateEdit QCalendarWidget {
                background-color: #ffffff;
                border: 1px solid #dcdcdc;
                border-radius: 15px;
                font-family: 'Poppins';
                font-size: 18px;
            }
            QCalendarWidget QToolButton {
                color: #04207d;
                background: #ffffff;
                border: none;
                font-family: 'Poppins';
                font-size: 18px;
            }
            QCalendarWidget QToolButton:hover {
                background-color: #eff3ff;
            }
            QCalendarWidget QMenu {
                background-color: #ffffff;
                border: 1px solid #dcdcdc;
                font-family: 'Poppins';
                font-size: 18px;
            }
            QCalendarWidget QSpinBox {
                background: #ffffff;
                border: none;
                font-family: 'Poppins';
                font-size: 18px;
                margin: 5px;
            }
            QCalendarWidget QSpinBox::up-button, QCalendarWidget QSpinBox::down-button {
                subcontrol-origin: border;
                width: 20px;
                height: 15px;
                background-color: #04207d;
                border-radius: 3px;
            }
            QCalendarWidget QSpinBox::up-arrow, QCalendarWidget QSpinBox::down-arrow {
                image: url(assets/up.png);  
                width: 15px;
                height: 15px;
            }
            QCalendarWidget QAbstractItemView:enabled {
                font-family: 'Poppins';
                font-size: 18px;
                color: #04207d;
                background-color: #ffffff;
                selection-background-color: #04207d;
                selection-color: #ffffff;
            }
            QMessageBox QPushButton {
                background-color: #04207d;
                color: #ffffff;
                border-radius: 10px;
                font-size: 18px;
                font-weight: bold;
                height: 30px;
                width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #021249;
            }       
        """)
        self.initUI()

    def initUI(self):
        layout = QFormLayout()
        self.nameInput = QLineEdit()
        self.ageInput = QLineEdit()
        self.genderInput = QComboBox()
        self.genderInput.addItems(["Male", "Female"])
        self.doctorassignedInput = QComboBox()
        self.doctors_names = extract_doctor_names()
        self.doctorassignedInput.addItems(self.doctors_names)
        self.dobInput = QDateEdit()
        self.dobInput.setCalendarPopup(True)
        self.dobInput.setDisplayFormat("yyyy-MM-dd")
        self.dobInput.dateChanged.connect(self.calculateAge)
        self.ageInput = QLineEdit()
        self.ageInput.setReadOnly(True)
        self.contactInput = QLineEdit()
        self.addressInput = QLineEdit()
        self.emailInput = QLineEdit()
        self.diseaseInput = QLineEdit()

        layout.addRow("Name:", self.nameInput)
        layout.addRow("Gender:", self.genderInput)
        layout.addRow("Doctor:", self.doctorassignedInput)
        layout.addRow("Date of Birth:", self.dobInput)
        layout.addRow("Age:", self.ageInput)
        layout.addRow("Contact:", self.contactInput)
        layout.addRow("Email:",self.emailInput)
        layout.addRow("Address:", self.addressInput)
        layout.addRow("Disease:", self.diseaseInput)

        self.submitButton = QPushButton("Submit")
        self.submitButton.setStyleSheet("""
            QPushButton {
                background-color: #04207d;
                color: #ffffff;
                border-radius: 10px;
                font-size:16px;                                        
                font-weight:bold;                               
                                 }
            QPushButton:hover {
                background-color: #021249;}
                                 
                                 """)
        self.submitButton.clicked.connect(self.submitData)
        layout.addWidget(self.submitButton)
        self.setLayout(layout)

    def calculateAge(self):
        dob = self.dobInput.date().toPyDate()
        today = datetime.today().date()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        self.ageInput.setText(str(age))

    def submitData(self):
        name = self.nameInput.text()
        gender = self.genderInput.currentText()
        doctor = self.doctorassignedInput.currentText()
        dob = self.dobInput.text()
        age = self.ageInput.text()
        contact = self.contactInput.text()
        address = self.addressInput.text()
        email = self.emailInput.text()
        disease = self.diseaseInput.text()

        if not all([name, age, gender, doctor, dob, contact, address,email, disease]):
            QMessageBox.warning(self, "Input Error", "All Fields Required!")
            return
        try:
            store_patient_data(name,age,gender,doctor,dob,contact,address,email,disease)
            QMessageBox.information(self, "Success", "Patient data has been added successfully!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"An error occurred: {e}")

class PatientBox(QWidget):
    def __init__(self, patient):
        super().__init__()
        self.patient = patient
        self.initUI()

    def initUI(self):
        self.setFixedSize(350, 550)  
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignTop)
        main_layout.setSpacing(10)
        self.setLayout(main_layout)

        wrapper_widget = QWidget()
        wrapper_layout = QVBoxLayout()
        wrapper_layout.setAlignment(Qt.AlignTop)
        wrapper_layout.setSpacing(10)
        wrapper_layout.setContentsMargins(10, 10, 10, 10)
        wrapper_widget.setLayout(wrapper_layout)
        
        # Randomize icon based on gender
        icon_folder = 'assets/user_icons/png/male' if self.patient['gender'].lower() == 'male' else 'assets/user_icons/png/female'
        icon_path = os.path.join(icon_folder, random.choice(os.listdir(icon_folder)))

        # Patient Photo
        photo_label = QLabel(self)
        photo_pixmap = QPixmap(icon_path).scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # Increased the size
        photo_label.setPixmap(photo_pixmap)
        photo_label.setAlignment(Qt.AlignCenter)
        wrapper_layout.addWidget(photo_label)

        # Patient Details
        font = QFont("Poppins")
        font.setPointSize(12)

        details = [
            f"Name: {self.patient['patient_name']}",
            f"Age: {self.patient['age']}",
            f"Gender: {self.patient['gender']}",
            f"DOB: {self.patient['dob']}",
            f"DOA: {self.patient['date_of_admission']}",
            f"Disease: {self.patient['disease']}"
        ]

        for detail in details:
            label = QLabel(detail, self)
            label.setFont(font)
            label.setAlignment(Qt.AlignCenter)
            wrapper_layout.addWidget(label)

        # Style the wrapper widget
        wrapper_widget.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-radius: 10px;
                border: 1px solid #dce4ff;
            }
            QLabel {
                color: #04207d;
                padding: 5px;
                background-color: #ffffff; 
                border:none;
            }
        """)

        # Add the wrapper widget to the main layout
        main_layout.addWidget(wrapper_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

class DoctorBox(QWidget):
    def __init__(self,doctor):
        super().__init__()
        self.doctor = doctor
        self.initUI()

    def initUI(self):
        self.setFixedSize(350,550)
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignTop)
        main_layout.setSpacing(10)
        self.setLayout(main_layout)

        wrapper_widget = QWidget()
        wrapper_layout = QVBoxLayout()
        wrapper_layout.setAlignment(Qt.AlignTop)
        wrapper_layout.setSpacing(10)
        wrapper_layout.setContentsMargins(10, 10, 10, 10)
        wrapper_widget.setLayout(wrapper_layout)

        icon_folder = 'assets/doctors_icons/png'
        icon_path = os.path.join(icon_folder, random.choice(os.listdir(icon_folder)))  
        # Doctor Photo
        photo_label = QLabel(self)
        photo_pixmap = QPixmap(icon_path).scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        photo_label.setPixmap(photo_pixmap)
        photo_label.setAlignment(Qt.AlignCenter)
        wrapper_layout.addWidget(photo_label)

        # Doctor Details
        font = QFont("Poppins")
        font.setPointSize(12)

        details = [
            f"Name: {self.doctor['doctor_name']}",
            f"Age: {self.doctor['age']}",
            f"Field: {self.doctor['field']}",
            f"Degree: {self.doctor['degree']}",
            f"Contact: {self.doctor['contact_number']}"
        ]

        for detail in details:
            label = QLabel(detail, self)
            label.setFont(font)
            label.setAlignment(Qt.AlignCenter)
            wrapper_layout.addWidget(label)
        wrapper_widget.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-radius: 10px;
                border: 1px solid #dce4ff;
            }
            QLabel {
                color: #04207d;
                padding: 5px;
                background-color: #ffffff;
                border:none;
            }
        """)

        main_layout.addWidget(wrapper_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

class AddDoctor(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add a Doctor")
        self.setFixedSize(800, 630)
        self.setStyleSheet("""
            QDialog {
                background-color: #eff3ff;
            }
            QLabel {
                font-family: 'Poppins';
                font-size: 18px;
                font-weight: Bolder;
                padding-top:8px;
            }
            QLineEdit, QDateEdit, QComboBox {
                background-color: #ffffff;
                border: 1px solid #dcdcdc;
                border-radius: 15px;
                padding: 10px;
                height: 35px;
                font-family: 'Poppins';
                font-size: 18px;
            }
            QLineEdit:focus, QDateEdit:focus, QComboBox:focus {
                border: 1px solid #04207d;
            }
            QPushButton {
                background-color: #04207d;
                color: #ffffff;
                border-radius: 15px;
                font-weight: bold;
                height: 40px;
            }
            QPushButton:hover {
                background-color: #021249;
            }
            QComboBox {
                padding-left: 10px;
                font-family: 'Poppins';
                font-size: 18px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                selection-background-color: #04207d;
                selection-color: #ffffff;
            }
            QComboBox::drop-down {
                background-color:#04207d;
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border-left-width: 1px;
                border-left-color: #dcdcdc;
                border-left-style: solid;
                border-top-right-radius: 15px;
                border-bottom-right-radius: 15px;
            }
            QComboBox::down-arrow {
                image: url(assets/down.png);  
                width: 15px;
                height: 15px;
            }
            QComboBox QScrollBar:vertical {
                border: none;
                background: #f9faff;
                width: 12px;
                margin: 0px 0px 0px 0px;
                border-radius: 15px;
            }
            QComboBox QScrollBar::handle:vertical {
                background: #04207d;
                min-height: 20px;
                border-radius: 6px;
            }
            QComboBox QScrollBar::add-line:vertical {
                border: none;
                background: #dcdcdc;
                height: 10px;
                subcontrol-position: bottom;
                subcontrol-origin: margin;
                border-bottom-left-radius: 6px;
                border-bottom-right-radius: 6px;
            }
            QComboBox QScrollBar::sub-line:vertical {
                border: none;
                background: #dcdcdc;
                height: 10px;
                subcontrol-position: top;
                subcontrol-origin: margin;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QDateEdit::drop-down {
                background-color:#04207d;
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border-left-width: 1px;
                border-left-color: #dcdcdc;
                border-left-style: solid;
                border-top-right-radius: 15px;
                border-bottom-right-radius: 15px;
            }
            QDateEdit::down-arrow {
                image: url(assets/down.png);  
                width: 15px;
                height: 15px;
            }
            QDateEdit QCalendarWidget {
                background-color: #ffffff;
                border: 1px solid #dcdcdc;
                border-radius: 15px;
                font-family: 'Poppins';
                font-size: 18px;
            }
            QCalendarWidget QToolButton {
                color: #04207d;
                background: #ffffff;
                border: none;
                font-family: 'Poppins';
                font-size: 18px;
            }
            QCalendarWidget QToolButton:hover {
                background-color: #eff3ff;
            }
            QCalendarWidget QMenu {
                background-color: #ffffff;
                border: 1px solid #dcdcdc;
                font-family: 'Poppins';
                font-size: 18px;
            }
            QCalendarWidget QSpinBox {
                background: #ffffff;
                border: none;
                font-family: 'Poppins';
                font-size: 18px;
                margin: 5px;
            }
            QCalendarWidget QSpinBox::up-button, QCalendarWidget QSpinBox::down-button {
                subcontrol-origin: border;
                width: 20px;
                height: 15px;
                background-color: #04207d;
                border-radius: 3px;
            }
            QCalendarWidget QSpinBox::up-arrow, QCalendarWidget QSpinBox::down-arrow {
                image: url(assets/up.png);  
                width: 15px;
                height: 15px;
            }
            QCalendarWidget QAbstractItemView:enabled {
                font-family: 'Poppins';
                font-size: 18px;
                color: #04207d;
                background-color: #ffffff;
                selection-background-color: #04207d;
                selection-color: #ffffff;
            }
            QMessageBox QPushButton {
                background-color: #04207d;
                color: #ffffff;
                border-radius: 10px;
                font-size: 18px;
                font-weight: bold;
                height: 30px;
                width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #021249;
            }       
        """)
        self.initUI()
    
    def initUI(self):
        layout = QFormLayout()
        self.nameInput = QLineEdit()
        self.dobInput = QDateEdit()
        self.dobInput.setCalendarPopup(True)
        self.dobInput.setDisplayFormat("yyyy-MM-dd")
        self.dobInput.dateChanged.connect(self.calculateAge)
        self.ageInput = QLineEdit()
        self.ageInput.setReadOnly(True)
        self.fieldInput = QComboBox()
        self.fieldInput.addItems([
            "Allergy and Immunology",
        "Anesthesiology",
        "Cardiology",
        "Dermatology",
        "Emergency Medicine",
        "Endocrinology",
        "Family Medicine",
        "Gastroenterology",
        "General Surgery",
        "Geriatrics",
        "Hematology",
        "Infectious Disease",
        "Internal Medicine",
        "Nephrology",
        "Neurology",
        "Neurosurgery",
        "Obstetrics and Gynecology",
        "Oncology",
        "Ophthalmology",
        "Orthopedics",
        "Otolaryngology (ENT)",
        "Pathology",
        "Pediatrics",
        "Physical Medicine and Rehabilitation",
        "Plastic Surgery",
        "Podiatry",
        "Psychiatry",
        "Pulmonology",
        "Radiology",
        "Rheumatology",
        "Sports Medicine",
        "Thoracic Surgery",
        "Urology",
        "Vascular Surgery"
        ])
        self.degreeInput = QComboBox()
        self.degreeInput.addItems([
            "MBBS","MD","PhD","DO","MS","DM","DNB","MCh","BDS","MDS","FRCP","FRCS","MPH","MSc",
])
        self.contactInput = QLineEdit()
        self.emailInput = QLineEdit()

        layout.addRow("Name:", self.nameInput)
        layout.addRow("Date of Birth:", self.dobInput)
        layout.addRow("Age:", self.ageInput)
        layout.addRow("Specialization:",self.fieldInput)
        layout.addRow("Degree:",self.degreeInput)
        layout.addRow("Contact:", self.contactInput)
        layout.addRow("Email:",self.emailInput)

        self.submitButton = QPushButton("Submit")
        self.submitButton.setStyleSheet("""
            QPushButton {
                background-color: #04207d;
                color: #ffffff;
                border-radius: 10px;
                font-size:16px;                                        
                font-weight:bold;                               
                                 }
            QPushButton:hover {
                background-color: #021249;}
                                 
                                 """)
        self.submitButton.clicked.connect(self.submitData)
        layout.addWidget(self.submitButton)
        self.setLayout(layout)
    
    def calculateAge(self):
        dob = self.dobInput.date().toPyDate()
        today = datetime.today().date()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        self.ageInput.setText(str(age))
    
    def submitData(self):
        name = "Dr. " + self.nameInput.text()
        dob = self.dobInput.text()
        age = self.ageInput.text()
        field = self.fieldInput.currentText()
        degree = self.degreeInput.currentText()
        contact = self.contactInput.text()
        email = self.emailInput.text()

        if not all([name,dob,age,field,degree,contact,email]):
            QMessageBox.warning(self, "Input Error", "All Fields Required!")
            return
        
        try:
            store_doctor_data(name,dob,age,field,degree,contact,email)
            QMessageBox.information(self, "Success", "Doctor data has been added successfully!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"An error occurred: {e}")


# MAIN APP PAGES
class Dashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignTop)  

        # Create a container for the stats with a light background box
        BackgroundBox = QGroupBox()
        BackgroundBoxLayout = QVBoxLayout()
        BackgroundBoxLayout.setContentsMargins(10, 10, 10, 10)
        BackgroundBoxLayout.setSpacing(10)  
        BackgroundBoxLayout.setAlignment(Qt.AlignTop)  
        BackgroundBox.setLayout(BackgroundBoxLayout)
        BackgroundBox.setStyleSheet("QGroupBox { background-color: #f9faff; border-radius: 20px; }")

        # Create a grid layout for the stat boxes
        statsGridLayout = QGridLayout()
        statsGridLayout.setContentsMargins(0, 0, 0, 0)
        statsGridLayout.setSpacing(80)  

        # Adding individual StatBox widgets for each statistic
        self.stats = [
            ('assets/patient-dashboard.png', "Total Patients", "0"),
            ('assets/doctor-dashboard.png', "Available Doctors", "0"),
            ('assets/bed-dashboard.png', "Available Beds", "0"),
            ('assets/operation-dashboard.png', "Today's Operations", "0")
        ]

        self.stat_boxes = []


        for i, (iconPath, statName, statValue) in enumerate(self.stats):
            statBox = StatBox(iconPath, statName, statValue)
            self.stat_boxes.append(statBox)
            statsGridLayout.addWidget(statBox, 0, i)

        # Set column stretch to make the stat boxes span across the width of the screen
        for i in range(len(self.stats)):
            statsGridLayout.setColumnStretch(i, 1)
        BackgroundBoxLayout.addLayout(statsGridLayout)
        BackgroundBox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Create a grid layout for the graphs
        graphsGridLayout = QGridLayout()
        graphsGridLayout.setContentsMargins(0, 0, 0, 0)
        graphsGridLayout.setHorizontalSpacing(10)
        graphsGridLayout.setVerticalSpacing(10)

        leftSpacer = QSpacerItem(10, 0, QSizePolicy.Fixed, QSizePolicy.Minimum)
        graphsGridLayout.addItem(leftSpacer, 0, 0)

        # Patient History
        patientHistoryLayout = QVBoxLayout()
        patientHistoryHeader = QLabel("Patient History")
        patientHistoryHeader.setFont(QFont("Poppins", 13, QFont.Bold))
        patientHistoryHeader.setStyleSheet(f"color: {DARK_BACKGROUND_COLOR}; background-color: transparent;")
        patientHistoryLayout.addWidget(patientHistoryHeader)

        self.patientHistoryGraph = PatientHistoryCanvas(self)
        self.patientHistoryGraph.setFixedSize(SCALE_FACTOR * 1000, SCALE_FACTOR * 400)
        patientHistoryLayout.addWidget(self.patientHistoryGraph)
        graphsGridLayout.addLayout(patientHistoryLayout, 0, 1, 1, 1, alignment=Qt.AlignLeft)
        middleSpacer = QSpacerItem(10, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
        graphsGridLayout.addItem(middleSpacer, 0, 2)

        # Major Diseases
        majorDiseasesLayout = QVBoxLayout()
        majorDiseasesHeader = QLabel("Major Diseases")
        majorDiseasesHeader.setFont(QFont("Poppins", 13, QFont.Bold))
        majorDiseasesHeader.setStyleSheet(f"color: {DARK_BACKGROUND_COLOR}; background-color: transparent;")
        majorDiseasesLayout.addWidget(majorDiseasesHeader)

        self.majorDiseasesGraph = PieChartCanvas(self)
        self.majorDiseasesGraph.setFixedSize(SCALE_FACTOR * 480, SCALE_FACTOR * 400)
        self.majorDiseasesGraph.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-radius: 25px;
            }
        """)
        majorDiseasesLayout.addWidget(self.majorDiseasesGraph)
        graphsGridLayout.addLayout(majorDiseasesLayout, 0, 3,1,1, alignment=Qt.AlignRight)
        rightSpacer = QSpacerItem(10, 0, QSizePolicy.Fixed, QSizePolicy.Minimum)
        graphsGridLayout.addItem(rightSpacer, 0, 4)

        BackgroundBoxLayout.addLayout(graphsGridLayout)

        # Create a grid layout for the second set of graphs
        graphsGridLayout1 = QGridLayout()
        graphsGridLayout1.setContentsMargins(0, 0, 0, 0)
        graphsGridLayout1.setHorizontalSpacing(10)
        graphsGridLayout1.setVerticalSpacing(10)

        leftSpacer1 = QSpacerItem(10, 0, QSizePolicy.Fixed, QSizePolicy.Minimum)
        graphsGridLayout1.addItem(leftSpacer1, 0, 0)

        # Patients Per Day
        PatientsPerDayLayout = QVBoxLayout()
        PatientsPerDayHeader = QLabel("Patients Per Day")
        PatientsPerDayHeader.setFont(QFont("Poppins", 13, QFont.Bold))
        PatientsPerDayHeader.setStyleSheet(f"color: {DARK_BACKGROUND_COLOR}; background-color: transparent;")
        PatientsPerDayLayout.addWidget(PatientsPerDayHeader)

        self.PatientsPerDayGraph = PatientsPerDayCanvas(self)
        self.PatientsPerDayGraph.setFixedSize(SCALE_FACTOR * 1000, SCALE_FACTOR * 400)
        PatientsPerDayLayout.addWidget(self.PatientsPerDayGraph)
        graphsGridLayout1.addLayout(PatientsPerDayLayout, 0, 1, 1, 1, alignment=Qt.AlignLeft)
        middleSpacer1 = QSpacerItem(10, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
        graphsGridLayout1.addItem(middleSpacer1, 0, 2)

        # Top Doctors
        TopDoctorsLayout = QVBoxLayout()
        TopDoctorsHeader = QLabel("Top Doctors")
        TopDoctorsHeader.setFont(QFont("Poppins", 13, QFont.Bold))
        TopDoctorsHeader.setStyleSheet(f"color: {DARK_BACKGROUND_COLOR}; background-color: transparent;")
        TopDoctorsLayout.addWidget(TopDoctorsHeader)

        self.topDoctorsGraph = BarChartCanvas(self)
        self.topDoctorsGraph.setFixedSize(SCALE_FACTOR * 600, SCALE_FACTOR * 400)
        self.topDoctorsGraph.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border-radius: 25px;
            }
        """)
        TopDoctorsLayout.addWidget(self.topDoctorsGraph)
        graphsGridLayout1.addLayout(TopDoctorsLayout, 0, 3, 1, 1, alignment=Qt.AlignRight)
        rightSpacer1 = QSpacerItem(10, 0, QSizePolicy.Fixed, QSizePolicy.Minimum)
        graphsGridLayout1.addItem(rightSpacer1, 0, 4)

        BackgroundBoxLayout.addLayout(graphsGridLayout1)

        layout.addWidget(BackgroundBox)
        self.setLayout(layout)

        self.update_stats()

    def update_stats(self):
        stats = fetch_stats()
        for stat_box, stat_value in zip(self.stat_boxes, stats):
            stat_box.update_stat_value(str(stat_value))
        self.update_pie_chart()
        self.update_bar_chart()
        self.update_line_chart()
        self.update_heatmap()

    def update_pie_chart(self):
        data = fetch_disease_counts()
        self.majorDiseasesGraph.plot_pie_chart(data)

    def update_heatmap(self):
        data = fetch_patients_per_day() 
        self.PatientsPerDayGraph.plot_heatmap(data)

    def update_bar_chart(self):
        data = fetch_top_doctors()
        self.topDoctorsGraph.plot_bar_chart(data)

    def update_line_chart(self):
        data = fetch_patient_history() 
        self.patientHistoryGraph.plot_line_chart(data)

class Patients(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;            
            }
            QScrollArea QScrollBar:vertical {
                border: none;
                background: #f9faff;
                width: 15px;
                margin: 0px 0px 0px 0px;
                border-radius: 15px;
            }
            QScrollArea QScrollBar::handle:vertical {
                background: #04207d;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollArea QScrollBar::add-line:vertical {
                border: none;
                background: #dcdcdc;
                height: 10px;
                subcontrol-position: bottom;
                subcontrol-origin: margin;
                border-bottom-left-radius: 6px;
                border-bottom-right-radius: 6px;
            }
            QScrollArea QScrollBar::sub-line:vertical {
                border: none;
                background: #dcdcdc;
                height: 10px;
                subcontrol-position: top;
                subcontrol-origin: margin;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
        """)
        layout.addWidget(self.scroll_area)

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("""
            QWidget {
                background-color: #f9faff;
                border-radius: 10px;
                border: none;
            }
        """)
        self.scroll_area.setWidget(self.content_widget)
        
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(10)  
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        self.content_widget.setLayout(self.grid_layout)

        self.loadPatients()
    
    def loadPatients(self, search_query=None):
        db, cursor = connect_to_db(PASSWD)
        try:
            cursor = db.cursor(dictionary=True)
            if search_query:
                cursor.execute("SELECT patient_name, age, gender, dob, date_of_admission, disease FROM patients WHERE patient_name LIKE %s", (f'%{search_query}%',))
            else:
                cursor.execute("SELECT patient_name, age, gender, dob, date_of_admission, disease FROM patients")
            patients = cursor.fetchall()

            # Clear the existing widgets
            for i in reversed(range(self.grid_layout.count())): 
                widget_to_remove = self.grid_layout.itemAt(i).widget()
                self.grid_layout.removeWidget(widget_to_remove)
                widget_to_remove.setParent(None)
            
            # Add new patient widgets
            for i, patient in enumerate(patients):
                row = i // 4
                col = i % 4
                patient_box = PatientBox(patient)
                self.grid_layout.addWidget(patient_box, row, col)
        finally:
            db.close()
        
        self.grid_layout.setSpacing(10)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)

class Doctors(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Add a horizontal layout for the Add Doctor button
        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignRight)
        layout.addLayout(button_layout)

        AddDoctor = QPushButton("+ Add a Doctor")
        AddDoctor.setStyleSheet("""
            QPushButton {
                background-color: #04207d;
                color: #ffffff;
                border-radius: 10px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #021249;
            }
        """)
        AddDoctor.setFixedHeight(50)
        AddDoctor.setFixedWidth(200)
        AddDoctor.clicked.connect(self.doctorForm)
        button_layout.addWidget(AddDoctor)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollArea QScrollBar:vertical {
                border: none;
                background: #f9faff;
                width: 15px;
                margin: 0px 0px 0px 0px;
                border-radius: 15px;
            }
            QScrollArea QScrollBar::handle:vertical {
                background: #04207d;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollArea QScrollBar::add-line:vertical {
                border: none;
                background: #dcdcdc;
                height: 10px;
                subcontrol-position: bottom;
                subcontrol-origin: margin;
                border-bottom-left-radius: 6px;
                border-bottom-right-radius: 6px;
            }
            QScrollArea QScrollBar::sub-line:vertical {
                border: none;
                background: #dcdcdc;
                height: 10px;
                subcontrol-position: top;
                subcontrol-origin: margin;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
        """)
        layout.addWidget(self.scroll_area)

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("""
            QWidget {
                background-color: #f9faff;
                border-radius: 10px;
                border: none;
            }
        """)
        self.scroll_area.setWidget(self.content_widget)

        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(10)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        self.content_widget.setLayout(self.grid_layout)

        self.loadDoctors()

    def loadDoctors(self):
        db, cursor = connect_to_db(PASSWD)
        try:
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT doctor_name, age, field, degree, contact_number FROM doctors")
            doctors = cursor.fetchall()

            for i in reversed(range(self.grid_layout.count())):
                widget_to_remove = self.grid_layout.itemAt(i).widget()
                self.grid_layout.removeWidget(widget_to_remove)
                widget_to_remove.setParent(None)

            for i, doctor in enumerate(doctors):
                row = i // 4
                col = i % 4
                doctor_box = DoctorBox(doctor)
                self.grid_layout.addWidget(doctor_box, row, col)
        finally:
            db.close()

        self.grid_layout.setSpacing(10)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)

    def doctorForm(self):
        AddDoctorForm = AddDoctor(self)
        AddDoctorForm.exec_()

class Operations(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;            
            }
            QScrollArea QScrollBar:vertical {
                border: none;
                background: #f9faff;
                width: 15px;
                margin: 0px 0px 0px 0px;
                border-radius: 15px;
            }
            QScrollArea QScrollBar::handle:vertical {
                background: #04207d;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollArea QScrollBar::add-line:vertical {
                border: none;
                background: #dcdcdc;
                height: 10px;
                subcontrol-position: bottom;
                subcontrol-origin: margin;
                border-bottom-left-radius: 6px;
                border-bottom-right-radius: 6px;
            }
            QScrollArea QScrollBar::sub-line:vertical {
                border: none;
                background: #dcdcdc;
                height: 10px;
                subcontrol-position: top;
                subcontrol-origin: margin;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QDialog {
                background-color: #eff3ff;
            }
            QLabel {
                font-family: 'Poppins';
                font-size: 18px;
                font-weight: Bolder;
                padding-top:8px;
            }
            QLineEdit, QDateEdit, QComboBox {
                background-color: #ffffff;
                border: 1px solid #dcdcdc;
                border-radius: 15px;
                padding: 10px;
                height: 35px;
                font-family: 'Poppins';
                font-size: 18px;
            }
            QLineEdit:focus, QDateEdit:focus, QComboBox:focus {
                border: 1px solid #04207d;
            }
            QPushButton {
                background-color: #04207d;
                color: #ffffff;
                border-radius: 15px;
                font-weight: bold;
                height: 40px;
            }
            QPushButton:hover {
                background-color: #021249;
            }
            QComboBox {
                padding-left: 10px;
                font-family: 'Poppins';
                font-size: 18px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                selection-background-color: #04207d;
                selection-color: #ffffff;
            }
            QComboBox::drop-down {
                background-color:#04207d;
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border-left-width: 1px;
                border-left-color: #dcdcdc;
                border-left-style: solid;
                border-top-right-radius: 15px;
                border-bottom-right-radius: 15px;
            }
            QComboBox::down-arrow {
                image: url(assets/down.png);  
                width: 15px;
                height: 15px;
            }
            QComboBox QScrollBar:vertical {
                border: none;
                background: #f9faff;
                width: 12px;
                margin: 0px 0px 0px 0px;
                border-radius: 15px;
            }
            QComboBox QScrollBar::handle:vertical {
                background: #04207d;
                min-height: 20px;
                border-radius: 6px;
            }
            QComboBox QScrollBar::add-line:vertical {
                border: none;
                background: #dcdcdc;
                height: 10px;
                subcontrol-position: bottom;
                subcontrol-origin: margin;
                border-bottom-left-radius: 6px;
                border-bottom-right-radius: 6px;
            }
            QComboBox QScrollBar::sub-line:vertical {
                border: none;
                background: #dcdcdc;
                height: 10px;
                subcontrol-position: top;
                subcontrol-origin: margin;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QDateEdit::drop-down {
                background-color:#04207d;
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border-left-width: 1px;
                border-left-color: #dcdcdc;
                border-left-style: solid;
                border-top-right-radius: 15px;
                border-bottom-right-radius: 15px;
            }
            QDateEdit::down-arrow {
                image: url(assets/down.png);  
                width: 15px;
                height: 15px;
            }
            QDateEdit QCalendarWidget {
                background-color: #ffffff;
                border: 1px solid #dcdcdc;
                border-radius: 15px;
                font-family: 'Poppins';
                font-size: 18px;
            }
            QCalendarWidget QToolButton {
                color: #04207d;
                background: #ffffff;
                border: none;
                font-family: 'Poppins';
                font-size: 18px;
            }
            QCalendarWidget QToolButton:hover {
                background-color: #eff3ff;
            }
            QCalendarWidget QMenu {
                background-color: #ffffff;
                border: 1px solid #dcdcdc;
                font-family: 'Poppins';
                font-size: 18px;
            }
            QCalendarWidget QSpinBox {
                background: #ffffff;
                border: none;
                font-family: 'Poppins';
                font-size: 18px;
                margin: 5px;
            }
            QCalendarWidget QSpinBox::up-button, QCalendarWidget QSpinBox::down-button {
                subcontrol-origin: border;
                width: 20px;
                height: 15px;
                background-color: #04207d;
                border-radius: 3px;
            }
            QCalendarWidget QSpinBox::up-arrow, QCalendarWidget QSpinBox::down-arrow {
                image: url(assets/up.png);  
                width: 15px;
                height: 15px;
            }
            QCalendarWidget QAbstractItemView:enabled {
                font-family: 'Poppins';
                font-size: 18px;
                color: #04207d;
                background-color: #ffffff;
                selection-background-color: #04207d;
                selection-color: #ffffff;
            }
            QMessageBox QPushButton {
                background-color: #04207d;
                color: #ffffff;
                border-radius: 10px;
                font-size: 18px;
                font-weight: bold;
                height: 30px;
                width: 80px;
            }
            QMessageBox QPushButton:hover {
                background-color: #021249;
            }
        """)

        # Scroll Area
        scrollArea = QScrollArea(self)
        scrollArea.setWidgetResizable(True)
        scrollAreaWidget = QWidget()
        scrollArea.setWidget(scrollAreaWidget)
        mainLayout = QVBoxLayout(scrollAreaWidget)
        self.setLayout(QVBoxLayout(self))
        self.layout().addWidget(scrollArea)

        mainLayout.setContentsMargins(10, 10, 10, 10)
        mainLayout.setSpacing(20)

        # Room Overview Section
        roomOverviewLabel = QLabel("Room Overview")
        roomOverviewLabel.setStyleSheet(f"font-family: Poppins;font-size: 24px; font-weight: bold;color: {DARK_BACKGROUND_COLOR};")
        mainLayout.addWidget(roomOverviewLabel)

        self.roomOverviewLayout = QGridLayout()
        mainLayout.addLayout(self.roomOverviewLayout)

        # Load Rooms from Database and Add to Layout
        self.loadRooms()

        # Spacer between sections
        mainLayout.addSpacing(20)

        # Patient Assignment Section
        patientAssignmentLabel = QLabel("Patient Assignment")
        patientAssignmentLabel.setStyleSheet(f"font-family: Poppins;font-size: 24px; font-weight: bold;color: {DARK_BACKGROUND_COLOR};")
        mainLayout.addWidget(patientAssignmentLabel)

        formLayout = QFormLayout()
        self.patientSelect = QComboBox()
        self.patientSelect.addItems(self.loadPatientNames())  # Load patient names
        formLayout.addRow("Select Patient:", self.patientSelect)

        self.roomSelect = QComboBox()
        self.roomSelect.addItems(self.loadAvailableRooms())  # Load available rooms
        formLayout.addRow("Select Room:", self.roomSelect)

        self.assignButton = QPushButton("Assign Patient to Room")
        self.assignButton.setStyleSheet("background-color: #04207d; color: #fff; font-weight: bold;")
        self.assignButton.clicked.connect(self.assignPatientToRoom)
        formLayout.addRow(self.assignButton)

        mainLayout.addLayout(formLayout)

    def loadRooms(self):
        db, cursor = connect_to_db(PASSWD)
        cursor.execute("SELECT room_id, room_number, room_type, capacity, current_occupancy FROM Rooms")
        rooms = cursor.fetchall()

        for i, room in enumerate(rooms):
            roomWidget = self.createRoomWidget(room)
            self.roomOverviewLayout.addWidget(roomWidget, i // 4, i % 4)  # 4 rooms per row

    def createRoomWidget(self, room):
        roomWidget = QFrame()
        roomWidget.setFrameShape(QFrame.StyledPanel)

        # Determine if the room is full by comparing occupancy and capacity
        isFull = room[4] == room[3]
        roomColor = '#f8d7da' if isFull else '#d4edda'
        roomWidget.setStyleSheet(f"background-color: {roomColor}; padding: 10px;")
        layout = QVBoxLayout(roomWidget)

        roomNumberLabel = QLabel(f"Room {room[1]}")
        roomNumberLabel.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(roomNumberLabel)

        roomTypeLabel = QLabel(f"Type: {room[2]}")
        layout.addWidget(roomTypeLabel)

        occupancyLabel = QLabel(f"Occupancy: {room[4]}/{room[3]}")
        layout.addWidget(occupancyLabel)

        statusLabel = QLabel(f"Status: {'Full' if isFull else 'Available'}")
        layout.addWidget(statusLabel)

        # Add patients and remove button if there are any
        if room[4] > 0:
            patients = self.loadPatientsInRoom(room[0])
            for patient in patients:
                patientLabel = QLabel(f"Patient: {patient[0]}")
                layout.addWidget(patientLabel)

                removeButton = QPushButton("X")
                removeButton.setFixedSize(30, 30)
                removeButton.setStyleSheet("""
                    QPushButton {
                        background-color: #dc3545;
                        color: #fff;
                        font-size: 18px;
                        font-weight: bold;
                        border-radius: 15px;
                    }
                    QPushButton:hover {
                        background-color: #b21f2d;
                    }
                """)
                removeButton.clicked.connect(lambda _, p=patient, r=room[0]: self.removePatientFromRoom(p, r))
                layout.addWidget(removeButton)

        return roomWidget

    def loadPatientNames(self):
        db, cursor = connect_to_db(PASSWD)
        
        # Fetch patients who do not have an active room assignment (i.e., discharge_date is NULL)
        cursor.execute("""
            SELECT p.patient_id, p.patient_name
            FROM patients p
            LEFT JOIN PatientRoomAssignment pra ON p.patient_id = pra.patient_id AND pra.discharge_date IS NULL
            WHERE pra.patient_id IS NULL
        """)
        
        patients = cursor.fetchall()
        return [patient[1] for patient in patients]

    def loadAvailableRooms(self):
        db, cursor = connect_to_db(PASSWD)
        cursor.execute("SELECT room_number FROM Rooms WHERE current_occupancy < capacity")
        rooms = cursor.fetchall()
        return [room[0] for room in rooms]

    def assignPatientToRoom(self):
        db, cursor = connect_to_db(PASSWD)
        cursor = db.cursor(buffered=True)
        selectedPatient = self.patientSelect.currentText()
        selectedRoom = self.roomSelect.currentText()

        try:
            # Get patient_id
            cursor.execute("SELECT patient_id FROM patients WHERE patient_name = %s", (selectedPatient,))
            patient_id = cursor.fetchone()
            
            if not patient_id:
                QMessageBox.warning(self, "Warning", f"Patient '{selectedPatient}' not found.")
                return

            patient_id = patient_id[0]

            # Check if the patient is already assigned to a room
            cursor.execute("""
                SELECT room_id FROM Rooms
                WHERE room_id = (SELECT room_id FROM patients WHERE patient_id = %s)
            """, (patient_id,))
            assigned_room = cursor.fetchone()

            if assigned_room:
                assigned_room_id = assigned_room[0]
                if assigned_room_id == selectedRoom:
                    QMessageBox.warning(self, "Warning", f"Patient '{selectedPatient}' is already assigned to Room {selectedRoom}.")
                else:
                    QMessageBox.warning(self, "Warning", f"Patient '{selectedPatient}' is already assigned to another room.")
                return

            # Get room_id
            cursor.execute("SELECT room_id FROM Rooms WHERE room_number = %s", (selectedRoom,))
            room_id = cursor.fetchone()
            
            if not room_id:
                QMessageBox.warning(self, "Warning", f"Room '{selectedRoom}' not found.")
                return

            room_id = room_id[0]

            # Update the patient's room assignment
            cursor.execute("UPDATE patients SET room_id = %s WHERE patient_id = %s", (room_id, patient_id))

            # Update the room's occupancy
            cursor.execute("UPDATE Rooms SET current_occupancy = current_occupancy + 1 WHERE room_id = %s", (room_id,))

            db.commit()

            QMessageBox.information(self, "Success", f"Patient '{selectedPatient}' has been assigned to Room {selectedRoom}.")

        except Error as err:
            QMessageBox.critical(self, "Error", f"An error occurred: {err}")
        
        finally:
            try:
                # Ensure that the cursor and connection are properly closed
                if cursor is not None:
                    cursor.close()
                if db is not None:
                    db.close()
            except Error as err:
                QMessageBox.critical(self, "Error", f"An error occurred during cleanup: {err}")

        self.refreshUI()

    def removePatientFromRoom(self, patient, room_id):
        db, cursor = connect_to_db(PASSWD)
        cursor = db.cursor(buffered=True)
        cursor.execute("SELECT patient_id FROM patients WHERE patient_name = %s", (patient[0],))
        patient_id = cursor.fetchone()[0]

        # Update the patient's room assignment to NULL
        cursor.execute("UPDATE patients SET room_id = NULL WHERE patient_id = %s", (patient_id,))

        # Update the room's occupancy
        cursor.execute("UPDATE Rooms SET current_occupancy = current_occupancy - 1 WHERE room_id = %s", (room_id,))

        db.commit()
        cursor.close()
        db.close()

        QMessageBox.information(self, "Success", f"Patient '{patient[0]}' has been removed from Room {room_id}.")
        self.refreshUI()

    def loadPatientsInRoom(self, room_id):
        db, cursor = connect_to_db(PASSWD)
        cursor.execute("SELECT patient_name FROM patients WHERE room_id = %s", (room_id,))
        patients = cursor.fetchall()
        cursor.close()
        db.close()
        return patients

    def refreshUI(self):
        # Clear the current layout
        while self.roomOverviewLayout.count():
            child = self.roomOverviewLayout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Reload the rooms
        self.loadRooms()

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle('HealthNext')
        self.setStyleSheet(f'background-color: {BACKGROUND_COLOR};') 

        # Main Layout of the Window
        mainLayout = QHBoxLayout()
        mainLayout.setContentsMargins(0, 0, 0, 0) 
        mainLayout.setSpacing(0)  
        self.setLayout(mainLayout)

        # Sidebar Widget
        sidebarWidget = QFrame()
        sidebarWidget.setFixedWidth(250)
        sidebarWidget.setStyleSheet(f"background-color: {BACKGROUND_COLOR}; color: #fff;") 

        # Sidebar Layout
        sidebarLayout = QVBoxLayout()
        sidebarLayout.setContentsMargins(10, 10, 10, 10)
        sidebarLayout.setSpacing(75) 
        sidebarWidget.setLayout(sidebarLayout)

        # Logo at the top of the sidebar
        logo_label = QLabel()
        logo_pixmap = QPixmap('assets/project_logo.png')  
        if logo_pixmap.isNull():
            print("Failed to load logo image.")
        else:
            print("Logo image loaded successfully.")
        logo_label.setPixmap(logo_pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))  # Adjust size as needed
        logo_label.setAlignment(Qt.AlignCenter)  # Center the logo
        sidebarLayout.addWidget(logo_label)

        # Add a spacer below the logo to maintain spacing
        sidebarLayout.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Sidebar buttons
        sidebarButtons = [
            ('Dashboard', 'assets/dashboard.png', 'assets/dashboard-active.png'),
            ('Patients', 'assets/patients.png', 'assets/patients-active.png'),
            ('Doctors', 'assets/doctor.png', 'assets/doctor-active.png'),
            ('Operations', 'assets/operation.png', 'assets/operation-active.png')
        ]

        self.buttonMapping = {}

        for index, (label, iconPath, activeIconPath) in enumerate(sidebarButtons):
            button = AnimatedButton(label, iconPath, activeIconPath)
            button.clicked.connect(lambda checked, idx=index: self.switchPage(idx))
            sidebarLayout.addWidget(button)
            self.buttonMapping[index] = button

        # Add stretch to push buttons upwards and ensure proper spacing
        sidebarLayout.addStretch()

        mainLayout.addWidget(sidebarWidget)

        # Vertical Line Divider
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet(f"color: {BACKGROUND_COLOR};")  
        mainLayout.addWidget(line)

        # Create a vertical layout for the header and main content
        contentLayout = QVBoxLayout()
        contentLayout.setContentsMargins(10, 10, 10, 10)
        contentLayout.setSpacing(10)

        # Header
        headerLayout = QHBoxLayout()
        headerLayout.setContentsMargins(0, 0, 0, 0)
        headerLayout.setSpacing(10)

        searchBar = QLineEdit()
        searchBar.setPlaceholderText("Search Patients")
        searchBar.setFixedHeight(50)
        searchBar.setFixedWidth(600)
        searchBar.setStyleSheet("""
            QLineEdit {
                background-color: #f9faff;
                border: none;
                border-radius: 25px;
                padding-left: 40px;
                font-size: 16px;
            }
        """)

        searchAction = QAction(QIcon('assets/search.png'), '', searchBar)
        searchBar.addAction(searchAction, QLineEdit.LeadingPosition)
        searchBar.returnPressed.connect(self.on_search_enter_pressed)
        self.searchBar = searchBar
        headerLayout.addWidget(searchBar)

        # Add a spacer to push the search bar to the left
        headerLayout.addItem(QSpacerItem(500, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Refresh Button and Add Patient Button Container
        buttonLayout = QHBoxLayout()
        buttonLayout.setSpacing(10)

        # Refresh Button
        refreshButton = QPushButton()
        refreshButton.setIcon(QIcon('assets/refresh.png'))
        refreshButton.setIconSize(QSize(15, 15))
        refreshButton.setFixedSize(40, 40)
        refreshButton.setStyleSheet("""
            QPushButton {
                background-color: #eff3ff;
                border: none;
            }
            QPushButton:hover {
                background-color: #dce4ff;
            }
        """)
        #refreshButton.clicked.connect(self.refreshStats)  
        buttonLayout.addWidget(refreshButton)

        # Add Patient Button
        AddPatient = QPushButton("+ Add a Patient")
        AddPatient.setStyleSheet("""
            QPushButton {
                background-color: #04207d;
                color: #ffffff;
                border-radius: 10px;
                font-size:16px;                                        
                font-weight:bold;                               
            }
            QPushButton:hover {
                background-color: #021249;
            }
        """)
        AddPatient.setFixedHeight(50)
        AddPatient.setFixedWidth(200)
        AddPatient.clicked.connect(self.patientForm)
        buttonLayout.addWidget(AddPatient)

        headerLayout.addLayout(buttonLayout)
        contentLayout.addLayout(headerLayout)

        # Add the stacked widget with pages to the content layout
        self.stackedWidget = QStackedWidget()
        self.pages = {
            'Dashboard': Dashboard(),
            'Patients': Patients(),
            'Doctors': Doctors(),
            'Operations': Operations()    
        }
        for pageName, pageWidget in self.pages.items():
            self.stackedWidget.addWidget(pageWidget)
        contentLayout.addWidget(self.stackedWidget)
        
        mainLayout.addLayout(contentLayout)

        # Show dashboard by default
        self.switchPage(0)

        # USAGE : Refresh button
        refreshButton.clicked.connect(self.pages['Dashboard'].update_stats)
        refreshButton.clicked.connect(self.pages['Patients'].loadPatients)
        refreshButton.clicked.connect(self.pages['Doctors'].loadDoctors)
        refreshButton.clicked.connect(self.pages['Operations'].refreshUI)
      
    def patientForm(self):
        AddPatientForm = AddPatient(self)
        AddPatientForm.exec_()    

    def switchPage(self, index):
        self.stackedWidget.setCurrentIndex(index)
        for idx, button in self.buttonMapping.items():
            if idx == index:
                button.setIcon(QIcon(button.activeIconPath))
                button.setStyleSheet(button.activeStyle)
            else:
                button.setIcon(QIcon(button.defaultIconPath))
                button.setStyleSheet(button.defaultStyle)

    def on_search_enter_pressed(self):
        search_text = self.searchBar.text()
        self.pages['Patients'].loadPatients(search_text)
        self.switchPage(1)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.showMaximized()
    sys.exit(app.exec_())