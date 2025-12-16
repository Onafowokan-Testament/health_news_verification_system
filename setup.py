
#!/usr/bin/env python3
import os
import sys
import subprocess

def check_python_version():
    if sys.version_info < (3, 9):
        print("❌ Python 3.9 or higher is required")
        sys.exit(1)
    print("✓ Python version OK")

def install_dependencies():
    print("\n📦 Installing dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    print("✓ Dependencies installed")

def create_directories():
    print("\n📁 Creating directories...")
    os.makedirs("data/chroma_db", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    print("✓ Directories created")

def check_env_file():
    if not os.path.exists(".env"):
        print("\n⚠️  No .env file found. Creating from template...")
        with open(".env.example", "r") as template:
            with open(".env", "w") as env_file:
                env_file.write(template.read())
        print("✓ .env file created. Please edit it with your API keys!")
        return False
    return True

def main():
    print("🏥 Nigerian Health Claim Checker - Setup")
    print("=" * 50)
    
    check_python_version()
    install_dependencies()
    create_directories()
    
    has_env = check_env_file()
    
    print("\n" + "=" * 50)
    if has_env:
        print("✅ Setup complete! Run: streamlit run app.py")
    else:
        print("⚠️  Please edit .env file with your API keys")
        print("   Then run: streamlit run app.py")

if __name__ == "__main__":
    main()
