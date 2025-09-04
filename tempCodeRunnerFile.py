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
      