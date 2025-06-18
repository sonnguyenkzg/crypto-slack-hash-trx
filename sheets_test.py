#!/usr/bin/env python3
"""
Google Sheets Connection Test
Simple script to test Google Sheets API connection before main integration
"""

import os
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Configuration
GOOGLE_SHEETS_CREDS_FILE = os.environ.get('GOOGLE_SHEETS_CREDS_FILE', 'service_account.json')
GOOGLE_SHEET_ID = os.environ.get('GOOGLE_SHEET_ID')

print("🧪 GOOGLE SHEETS CONNECTION TEST")
print("=" * 40)

def test_sheets_connection():
    """Test Google Sheets API connection"""
    
    # Check environment variables
    if not GOOGLE_SHEET_ID:
        print("❌ GOOGLE_SHEET_ID not set in .env file")
        return False
    
    if not os.path.exists(GOOGLE_SHEETS_CREDS_FILE):
        print(f"❌ Service account file not found: {GOOGLE_SHEETS_CREDS_FILE}")
        return False
    
    try:
        print(f"📋 Testing connection to sheet: {GOOGLE_SHEET_ID}")
        
        # Define scope
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Load credentials
        print("🔑 Loading service account credentials...")
        creds = Credentials.from_service_account_file(
            GOOGLE_SHEETS_CREDS_FILE,
            scopes=scope
        )
        
        # Initialize client
        print("🔗 Connecting to Google Sheets API...")
        client = gspread.authorize(creds)
        
        # Open the spreadsheet
        print("📊 Opening spreadsheet...")
        sheet = client.open_by_key(GOOGLE_SHEET_ID)
        
        print(f"✅ Successfully connected to: '{sheet.title}'")
        
        # Try to get or create a test worksheet
        try:
            worksheet = sheet.worksheet("Test")
            print("✅ Found existing 'Test' worksheet")
        except:
            print("📝 Creating 'Test' worksheet...")
            worksheet = sheet.add_worksheet(title="Test", rows=100, cols=10)
            print("✅ 'Test' worksheet created")
        
        # Test writing data
        print("✍️ Testing write operations...")
        test_data = [
            ["Timestamp", "Test Message", "Status"],
            [datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "Connection test successful", "✅ PASS"]
        ]
        
        # Clear existing data and write test data
        worksheet.clear()
        worksheet.update('A1', test_data)
        
        print("✅ Test data written successfully")
        
        # Test reading data
        print("👀 Testing read operations...")
        all_values = worksheet.get_all_values()
        print(f"✅ Read {len(all_values)} rows from worksheet")
        
        # Display the data we just wrote
        if len(all_values) >= 2:
            print(f"   Row 1: {all_values[0]}")
            print(f"   Row 2: {all_values[1]}")
        
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Google Sheets integration is ready")
        return True
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Check that GOOGLE_SHEET_ID is correct in .env")
        print("2. Verify service_account.json file exists")
        print("3. Ensure the sheet is shared with service account email")
        print("4. Check that APIs are enabled in Google Cloud Console")
        return False

def main():
    """Main test function"""
    success = test_sheets_connection()
    
    if success:
        print("\n✅ Ready to integrate with main bot!")
    else:
        print("\n❌ Fix the issues above before proceeding")

if __name__ == "__main__":
    main()