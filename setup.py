#!/usr/bin/env python3
"""
Quick Setup Script for Gemini SQL Assistant

This script helps you set up the entire system in one go.
Run: python setup.py
"""

import sys
import subprocess
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import base64

def print_header():
    """Print a beautiful header"""
    print("\n" + "="*70)
    print("🤖  AetherDB- SETUP WIZARD  🤖".center(70))
    print("="*70 + "\n")


def check_python_version():
    """Ensure Python 3.8+"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python 3.8+ is required. You have Python {version.major}.{version.minor}.{version.micro}")
        sys.exit(1)
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} detected")


def create_requirements_file():
    """Create requirements.txt if it doesn't exist"""
    if not Path("requirements.txt").exists():
        requirements_content = """streamlit>=1.28.0
pandas>=2.0.0
plotly>=5.17.0
python-dotenv>=1.0.0
sqlglot>=19.0.0
sqlparse>=0.4.4
google-generativeai>=0.3.0
pymysql>=1.1.0
psycopg2-binary>=2.9.0
"""
        print("\n📝 Creating requirements.txt...")
        with open("requirements.txt", "w") as f:
            f.write(requirements_content)
        print("✅ requirements.txt created")
    else:
        print("✅ requirements.txt already exists")


def install_dependencies():
    """Install Python dependencies"""
    print("\n📦 Installing dependencies...")
    print("This may take a few minutes...\n")
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("\n✅ All dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError:
        print("\n❌ Failed to install dependencies")
        print("Try manually: pip install -r requirements.txt")
        return False


def create_env_file():
    """Create .env file with user input (now encrypts API key)"""
    if Path(".env").exists():
        response = input("\n⚠️  .env file already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("✅ Keeping existing .env file")
            return
    
    print("\n🔑 Setting up environment variables...")
    print("\nTo get your Gemini API key:")
    print("1. Visit: https://makersuite.google.com/app/apikey")
    print("2. Create a new API key")
    print("3. Copy and paste it below\n")
    
    api_key = input("Enter your Gemini API Key (or press Enter to skip): ").strip()
    if api_key:
        print("\n🔒 For security, your API key will be encrypted before storage.")
        password = input("Set a password to encrypt your API key (keep this safe!): ").strip()
        password_bytes = password.encode()
        salt = b"gemini-setup-salt"  # In production, generate a random salt and store it.
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100_000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password_bytes))
        fernet = Fernet(key)
        encrypted_api_key = fernet.encrypt(api_key.encode()).decode()
        gemini_key_line = f"GEMINI_API_KEY_ENCRYPTED={encrypted_api_key}\nGEMINI_API_KEY_SALT={salt.decode(errors='ignore')}\n"
    else:
        gemini_key_line = "GEMINI_API_KEY_ENCRYPTED=\nGEMINI_API_KEY_SALT=\n"
    
    
    env_content = f"""# Gemini AI Configuration
{gemini_key_line}GEMINI_MODEL=models/gemini-2.5-pro
GEMINI_MAX_TOKENS=8192

# SQL Configuration
DEFAULT_DIALECT=mysql
MAX_SCHEMA_PROMPT_CHARS=14000
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    if api_key:
        print("\n✅ .env file created with your ENCRYPTED API key!")
        print("  ⚠️ To use Gemini API, your application must decrypt the key using your password.")
    else:
        print("\n✅ .env file created (remember to add your API key later)")

def verify_files():
    """Verify all required files exist"""
    required_files = [
        "sqlm.py",
        "schema_awareness.py",
        "db_executor.py",
        "streamlit_app.py",
        "command_processor.py"
    ]
    
    print("\n📋 Verifying required files...")
    all_present = True
    
    for file in required_files:
        if Path(file).exists():
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} - MISSING!")
            all_present = False
    
    return all_present


def create_sample_database():
    """Create a sample SQLite database for testing"""
    import sqlite3
    
    response = input("\n🗄️  Create a sample database for testing? (Y/n): ")
    if response.lower() == 'n':
        return
    
    print("\n📊 Creating sample database 'sample.db'...")
    
    conn = sqlite3.connect("sample.db")
    cursor = conn.cursor()
    
    # Create students table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY,
            firstname TEXT NOT NULL,
            surname TEXT NOT NULL,
            age INTEGER,
            class_id INTEGER,
            FOREIGN KEY (class_id) REFERENCES classes(id)
        )
    """)
    
    # Create classes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY,
            classname TEXT NOT NULL,
            teacher TEXT
        )
    """)
    
    # Insert sample data
    cursor.execute("DELETE FROM students")
    cursor.execute("DELETE FROM classes")
    
    classes_data = [
        (1, 'Mathematics 101', 'Dr. Smith'),
        (2, 'English Literature', 'Prof. Johnson'),
        (3, 'Computer Science', 'Dr. Williams'),
    ]
    cursor.executemany("INSERT INTO classes VALUES (?, ?, ?)", classes_data)
    
    students_data = [
        (1, 'Alice', 'Anderson', 20, 1),
        (2, 'Bob', 'Brown', 21, 2),
        (3, 'Charlie', 'Chen', 19, 3),
        (4, 'Diana', 'Davis', 22, 1),
        (5, 'Eve', 'Evans', 20, 2),
        (6, 'Frank', 'Foster', 21, 3),
        (7, 'Grace', 'Garcia', 19, 1),
        (8, 'Henry', 'Harris', 22, 2),
    ]
    cursor.executemany("INSERT INTO students VALUES (?, ?, ?, ?, ?)", students_data)
    
    conn.commit()
    conn.close()
    
    print("✅ Sample database created with 8 students and 3 classes")


def show_next_steps():
    """Display next steps to the user"""
    print("\n" + "="*70)
    print("🎉  SETUP COMPLETE!  🎉".center(70))
    print("="*70)
    
    print("\n📝 Next Steps:\n")
    print("1. Make sure you've added your Gemini API key to .env")
    print("   Edit .env and replace 'your_api_key_here' with your actual key")
    print()
    print("2. Run the Streamlit app:")
    print("   streamlit run streamlit_app.py")
    print()
    print("3. Or run the CLI version:")
    print("   python command_processor.py")
    print()
    print("4. Or test with sample data:")
    print("   python sqlm.py --run-test")
    print()
    print("📚 For detailed documentation, see the Integration Guide")
    print()
    print("💡 Quick test with sample database:")
    print("   1. Run: streamlit run streamlit_app.py")
    print("   2. Connect to: sample.db (SQLite)")
    print("   3. Try: 'Show me all students whose surname starts with A'")
    print()
    print("Happy querying! 🚀✨")
    print("="*70 + "\n")


def main():
    """Main setup function"""
    print_header()
    
    # Step 1: Check Python version
    check_python_version()
    
    # Step 2: Create requirements file
    create_requirements_file()
    
    # Step 3: Install dependencies
    response = input("\n📦 Install dependencies now? (Y/n): ")
    if response.lower() != 'n' and not install_dependencies():
        print("\n⚠️  You'll need to install dependencies manually")
    
    # Step 4: Create .env file
    create_env_file()
    
    # Step 5: Verify files
    if not verify_files():
        print("\n⚠️  Some required files are missing!")
        print("Make sure all module files are in the same directory")
    
    # Step 6: Create sample database
    create_sample_database()
    
    # Step 7: Show next steps
    show_next_steps()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Setup failed: {e}")
        sys.exit(1)