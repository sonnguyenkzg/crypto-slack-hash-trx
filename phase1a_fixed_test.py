#!/usr/bin/env python3
"""
Phase 1A - Fixed Environment Setup Test
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
    """Test if required packages can be imported"""
    print("\n📦 Testing package imports...")
    
    # Test packages directly by importing them
    packages_to_test = [
        ('requests', 'requests'),
        ('python-dotenv', 'dotenv'),
        ('slack-sdk', 'slack_sdk')
    ]
    
    all_good = True
    for package_name, import_name in packages_to_test:
        try:
            __import__(import_name)
            print(f"   ✅ {package_name} - OK")
        except ImportError as e:
            print(f"   ❌ {package_name} - Not available: {e}")
            print(f"      Run: pip install {package_name}")
            all_good = False
        except Exception as e:
            print(f"   ⚠️  {package_name} - Error: {e}")
            all_good = False
    
    return all_good

def test_network_connectivity():
    """Test network access to required APIs"""
    print("\n🌐 Testing network connectivity...")
    
    try:
        import requests
    except ImportError:
        print("   ❌ Cannot test network - requests not available")
        return False
    
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

def test_environment_setup():
    """Test if we're in the right environment"""
    print("\n🔧 Testing environment setup...")
    
    # Check if we're in a virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    
    if in_venv:
        print("   ✅ Virtual environment detected")
        print(f"   📁 Python path: {sys.executable}")
    else:
        print("   ⚠️  Not in virtual environment (recommended to use venv)")
        print(f"   📁 Python path: {sys.executable}")
    
    # Check current directory
    current_dir = os.getcwd()
    print(f"   📁 Working directory: {current_dir}")
    
    # Check for project files
    expected_files = ['requirements.txt', '.env.example']
    missing_files = [f for f in expected_files if not os.path.exists(f)]
    
    if not missing_files:
        print("   ✅ Project files present")
    else:
        print(f"   ⚠️  Missing files: {', '.join(missing_files)}")
    
    return True  # This is informational only

def create_minimal_test():
    """Create a minimal test to verify everything works"""
    print("\n🧪 Creating minimal functionality test...")
    
    test_content = '''#!/usr/bin/env python3
"""
Minimal test - verify all imports work
"""

def test_imports():
    """Test that all required packages can be imported"""
    try:
        import requests
        import dotenv
        import slack_sdk
        print("✅ All packages imported successfully!")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

if __name__ == "__main__":
    success = test_imports()
    if success:
        print("🎉 Ready for Phase 1B!")
    else:
        print("❌ Please install missing packages")
'''
    
    with open('test_minimal.py', 'w') as f:
        f.write(test_content)
    
    print("   ✅ Created test_minimal.py")
    
    # Run the minimal test
    try:
        result = subprocess.run([sys.executable, 'test_minimal.py'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("   ✅ Minimal test passed!")
            print(f"   📤 Output: {result.stdout.strip()}")
            return True
        else:
            print("   ❌ Minimal test failed!")
            print(f"   📤 Output: {result.stdout.strip()}")
            print(f"   📤 Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"   ❌ Could not run minimal test: {e}")
        return False

def run_comprehensive_test():
    """Run all tests with better diagnostics"""
    print("🧪 PHASE 1A - COMPREHENSIVE ENVIRONMENT TEST")
    print("=" * 60)
    print(f"⏰ Test started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Test Python version
    results.append(test_python_version())
    
    # Test environment setup (informational)
    test_environment_setup()
    
    # Test package imports
    results.append(test_pip_packages())
    
    # Test network connectivity
    results.append(test_network_connectivity())
    
    # Run minimal functionality test
    results.append(create_minimal_test())
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 COMPREHENSIVE TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"📈 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Environment is ready for Phase 1B - Slack App Setup")
        print("\n🚀 What's working:")
        print("   ✅ Python version compatible")
        print("   ✅ All required packages available")
        print("   ✅ Network connectivity to APIs")
        print("   ✅ Import functionality verified")
        print("\n🎯 Next Phase: Slack App Creation")
        
    else:
        print(f"⚠️  {total - passed} issues found")
        print("\n🔧 Quick fixes to try:")
        print("   1. Make sure you're in virtual environment:")
        print("      source venv/bin/activate")
        print("   2. Install/reinstall packages:")
        print("      pip install -r requirements.txt")
        print("   3. Test individual imports:")
        print("      python -c 'import requests, dotenv, slack_sdk'")
    
    return passed == total

if __name__ == "__main__":
    success = run_comprehensive_test()
    print(f"\n{'🎉 READY FOR PHASE 1B!' if success else '🔧 Please fix issues above'}")
    sys.exit(0 if success else 1)