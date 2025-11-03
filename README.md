### 🧠 VMaster – Automated Virtual Machine Management App

VMaster is a lightweight and intelligent web application designed to automate the management of virtual machines (VMs).
It allows users to create, configure, and monitor VMs easily — all powered by automation scripts.


🚀 **Main Features**

👤 User Accounts – Create an account and log in securely to manage your VMs.

⚙️ Custom VM Creation – Deploy virtual machines with custom configurations such as:

    - CPU cores

    - RAM size

    - Disk space

    - Operating System (OS)

📊 Real-Time Monitoring – Track the usage of:

    - CPU

    - RAM

    - Disk storage

    - Network traffic

🤖 Automation Scripts – All provisioning and monitoring tasks are handled through automated scripts.

🧠 Quick Launch – Launch the app instantly using the shortcut named 🧠VMaster on your desktop.

********************************************************************************************************

⚙️ **Installation & Setup**

        Clone the project
        git clone https://github.com/dehech/VMaster.git
        cd VMaster


    Launch the shortcut 🧠VMaster

********************************************************************************************************

🧱 **Build an Executable**

    You can create a standalone executable version of VMaster using cx_Freeze.
    The setup.py file is already prepared — just run:

        python setup.py build

    After building, you’ll find the executable inside:    
    
        build/exe.win-amd64-3.13/

********************************************************************************************************

🔄 **Reset Database**

    If you want to recreate the entire database (for a clean start),
    simply run the following command from the project directory:

        python recreate_database.py

    This script will:

    - Drop existing tables

    - Recreate the database schema

    - Prepare it for a fresh start

⚠️ Warning: This will delete all existing data permanently.

********************************************************************************************************

📁 **Project Structure**

    Below is the directory structure of the VMaster project:

        VMaster/
        │
        ├── app.py                  # Main Flask application
        ├── ancien.py               # Old version (kept for reference)
        ├── creator.py              # Handles automated VM creation logic
        ├── database.py             # Database connection and configuration
        ├── metrics.py              # VM resource monitoring and statistics
        ├── models.py               # Database models and ORM setup
        ├── recreate_database.py    # Script to reset and recreate the database
        ├── setup.py                # cx_Freeze configuration for building an executable
        ├── start_flask.bat         # Batch script to start Flask app easily
        ├── README.md               # Project documentation
        ├── VMaster.lnk             # Desktop shortcut to quickly launch the app
        │
        ├── icon/                   # Application icons and assets
        ├── instance/               # Local database files (e.g., app.db)
        ├── static/                 # CSS, JS, and static assets
        ├── templates/              # HTML templates (Flask Jinja2)
        └── __pycache__/            # Auto-generated Python cache files

********************************************************************************************************

🪪 **License**

You are free to use, modify, and distribute it with proper attribution.

********************************************************************************************************

👨‍💻 **Author**

Mohamed Firas Dehech
Email: [firas.dehech@gmail.com]
GitHub: https://github.com/dehech
