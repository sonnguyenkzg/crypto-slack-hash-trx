#!/usr/bin/env python3
"""
Phase 1A - Basic Environment Setup Test
This script tests that your environment is properly configured
"""

import sys
import os
import subprocess
from datetime import datetime

def test_python_version():
    """Test Python version compatibility"""
    print("🐍 Testing Python version...")
    version = sys.version_info
    print(f"   Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major >= 3 and version.minor >= 8:
        print("   ✅ Python version OK")
        return True
    else:
        print("   ❌ Need Python 3.8+")
        return False

def test_pip_packages():
    """Test if required packages can be installed"""
    print("\n📦 Testing package installation...")
    
    required_packages = [
        'requests',
        'python-dotenv',
        'slack-sdk'
    ]
    
    all_good = True
    for package in required_packages:
        try:
            result = subprocess.run([sys.executable, '-c', f'import {package.replace("-", "_")}'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"   ✅ {package} - OK")
            else:
                print(f"   ⚠️  {package} - Not installed")
                print(f"      Run: pip install {package}")
                all_good = False
        except Exception as e:
            print(f"   ❌ {package} - Error: {e}")
            all_good = False
    
    return all_good

def test_network_connectivity():
    """Test network access to required APIs"""
    print("\n🌐 Testing network connectivity...")
    
    import requests
    
    test_urls = [
        ('Slack API', 'https://slack.com/api/api.test'),
        ('Tronscan API', 'https://apilist.tronscan.org/api/system/status'),
        ('CoinGecko API', 'https://api.coingecko.com/api/v3/ping')
    ]
    
    all_good = True
    for name, url in test_urls:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"   ✅ {name} - Reachable")
            else:
                print(f"   ⚠️  {name} - Status {response.status_code}")
                all_good = False
        except Exception as e:
            print(f"   ❌ {name} - Error: {str(e)[:50]}...")
            all_good = False
    
    return all_good

def create_project_structure():
    """Create basic project directory structure"""
    print("\n📁 Creating project structure...")
    
    directories = [
        'bot',
        'logs',
        'config',
        'tests'
    ]
    
    files = [
        'bot/__init__.py',
        '.env.example',
        'requirements.txt',
        '.gitignore'
    ]
    
    # Create directories
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"   ✅ Created directory: {directory}/")
    
    # Create files if they don't exist
    for file_path in files:
        if not os.path.exists(file_path):
            if file_path == 'requirements.txt':
                content = """requests==2.31.0
python-dotenv==1.0.0
slack-sdk==3.21.3
google-api-python-client==2.100.0
google-auth==2.23.0
"""
            elif file_path == '.env.example':
                content = """# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here

# Channel IDs
TH_CHANNEL_ID=C1234567890
PH_CHANNEL_ID=C0987654321

# Authorized Users (comma-separated Slack user IDs)
ALLOWED_SLACK_USERS=U123456789,U987654321

# Google Sheets (optional for Phase 1)
GOOGLE_SHEETS_ID=your-sheet-id-here
GOOGLE_SERVICE_ACCOUNT_EMAIL=bot@project.iam.gserviceaccount.com
GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\\nYOUR_PRIVATE_KEY\\n-----END PRIVATE KEY-----"

# API Configuration
TRONSCAN_API_URL=https://apilist.tronscan.org/api
LOG_LEVEL=info
"""
            elif file_path == '.gitignore':
                content = """# Environment variables
.env
.env.local

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
venv/
env/
.venv/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
logs/*.log

# Secrets
*.pem
*.key
config/secrets.json
"""
            else:
                content = "# Auto-generated file\n"
            
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"   ✅ Created file: {file_path}")
        else:
            print(f"   ⚠️  File exists: {file_path}")

def run_basic_tests():
    """Run all basic environment tests"""
    print("🧪 PHASE 1A - ENVIRONMENT SETUP TEST")
    print("=" * 50)
    print(f"⏰ Test started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Test Python version
    results.append(test_python_version())
    
    # Test package availability
    results.append(test_pip_packages())
    
    # Test network connectivity
    results.append(test_network_connectivity())
    
    # Create project structure
    create_project_structure()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Environment is ready for Phase 1B")
        print("\n🚀 Next Steps:")
        print("   1. Run: pip install -r requirements.txt")
        print("   2. Copy .env.example to .env")
        print("   3. Ready for Slack app creation!")
    else:
        print(f"⚠️  {passed}/{total} tests passed")
        print("❌ Please fix the issues above before proceeding")
        print("\n🔧 Common fixes:")
        print("   - Install missing packages: pip install -r requirements.txt")
        print("   - Check internet connection")
        print("   - Update Python to 3.8+")
    
    return passed == total

if __name__ == "__main__":
    success = run_basic_tests()
    sys.exit(0 if success else 1)