#!/usr/bin/env python3
"""
adhoc.py - Bulk Load Transactions from CSV to Google Sheets
Reads Transfers_20250616.csv and loads each hash to Google Sheets using the bot's logic
UPDATED with latest address fix
"""

import os
import csv
import requests
import time
from datetime import datetime
from dotenv import load_dotenv

# Import our Google Sheets manager
from sheets_manager import SheetsManager

# Load environment variables
load_dotenv()

# Configuration
GOOGLE_SHEETS_CREDS_FILE = os.environ.get('GOOGLE_SHEETS_CREDS_FILE', 'service_account.json')
GOOGLE_SHEET_ID = os.environ.get('GOOGLE_SHEET_ID')
CSV_FILE = 'Transfers_20250616.csv'  # Your CSV file
USER_ID_FOR_BULK = 'BULK_IMPORT'     # User ID for bulk imports

print("📋 ADHOC BULK LOADER - CSV TO GOOGLE SHEETS (UPDATED)")
print("=" * 55)

class BulkLoader:
    def __init__(self):
        """Initialize the bulk loader"""
        print("🔧 Initializing Bulk Loader...")
        
        # Check if CSV file exists
        if not os.path.exists(CSV_FILE):
            print(f"❌ CSV file not found: {CSV_FILE}")
            self.csv_exists = False
            return
        else:
            print(f"✅ Found CSV file: {CSV_FILE}")
            self.csv_exists = True
        
        # Initialize Google Sheets manager
        self.sheets_manager = None
        if GOOGLE_SHEET_ID and os.path.exists(GOOGLE_SHEETS_CREDS_FILE):
            print("🔗 Initializing Google Sheets connection...")
            self.sheets_manager = SheetsManager(GOOGLE_SHEETS_CREDS_FILE, GOOGLE_SHEET_ID)
            
            if self.sheets_manager.is_connected:
                stats = self.sheets_manager.get_stats()
                if stats:
                    print(f"✅ Google Sheets connected: {stats['total_transactions']} transactions already logged")
                else:
                    print("✅ Google Sheets connected")
            else:
                print("❌ Google Sheets connection failed")
        else:
            print("❌ Google Sheets not configured")
    
    def get_trx_price(self):
        """Get current TRX price in USD"""
        try:
            response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=tron&vs_currencies=usd", timeout=5)
            if response.status_code == 200:
                return response.json()['tron']['usd']
        except:
            pass
        return 0.07  # Fallback price
    
    def fetch_transaction_data(self, tx_hash):
        """Fetch transaction data from Tronscan API"""
        url = "https://apilist.tronscan.org/api/transaction-info"
        
        try:
            response = requests.get(
                url, 
                params={'hash': tx_hash}, 
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('contractRet') or data.get('contract_map') or data.get('contractInfo'):
                    return True, data
                else:
                    return False, "Transaction not found on TRON blockchain"
            else:
                return False, f"API error: {response.status_code}"
                
        except requests.exceptions.Timeout:
            return False, "Request timeout"
        except Exception as e:
            return False, f"Network error: {str(e)[:100]}"
    
    def read_csv_hashes(self):
        """Read transaction hashes from CSV file"""
        hashes = []
        
        try:
            with open(CSV_FILE, 'r', encoding='utf-8') as file:
                # Skip header if it exists
                csv_reader = csv.reader(file)
                header = next(csv_reader, None)
                
                print(f"📄 CSV Header: {header}")
                
                # Assume first column contains the transaction hash
                for row_num, row in enumerate(csv_reader, start=2):
                    if row and len(row) > 0:
                        potential_hash = row[0].strip()
                        
                        # Validate hash format (64 hex characters)
                        if len(potential_hash) == 64 and all(c in '0123456789abcdefABCDEF' for c in potential_hash):
                            hashes.append(potential_hash)
                        else:
                            print(f"⚠️ Row {row_num}: Invalid hash format: {potential_hash[:20]}...")
                
                print(f"✅ Found {len(hashes)} valid transaction hashes")
                return hashes
                
        except Exception as e:
            print(f"❌ Error reading CSV: {e}")
            return []
    
    def process_hash(self, tx_hash, index, total):
        """Process a single transaction hash"""
        print(f"\n📡 [{index}/{total}] Processing: {tx_hash[:16]}...")
        
        # Check if already exists
        if self.sheets_manager.check_duplicate(tx_hash):
            print(f"⏭️ Skipping (already exists): {tx_hash[:16]}...")
            return True, "Already exists"
        
        # Fetch transaction data
        success, result = self.fetch_transaction_data(tx_hash)
        
        if not success:
            print(f"❌ Failed to fetch: {result}")
            return False, result
        
        # Get TRX price
        trx_price = self.get_trx_price()
        
        # Save to Google Sheets
        save_success, save_result = self.sheets_manager.log_transaction(
            result, tx_hash, USER_ID_FOR_BULK, trx_price
        )
        
        if save_success:
            print(f"✅ Logged: {tx_hash[:16]}...")
            return True, "Successfully logged"
        else:
            print(f"❌ Failed to log: {save_result}")
            return False, save_result
    
    def bulk_import(self, delay_seconds=2):
        """Perform bulk import with rate limiting"""
        if not self.csv_exists:
            print("❌ Cannot proceed - CSV file not found")
            return
        
        if not self.sheets_manager or not self.sheets_manager.is_connected:
            print("❌ Cannot proceed - Google Sheets not connected")
            return
        
        # Read hashes from CSV
        hashes = self.read_csv_hashes()
        
        if not hashes:
            print("❌ No valid hashes found in CSV")
            return
        
        print(f"\n🚀 Starting bulk import of {len(hashes)} transactions...")
        print(f"⏱️ Rate limit: {delay_seconds} seconds between requests")
        print("🔧 Using UPDATED address extraction logic")
        
        # Stats tracking
        stats = {
            'total': len(hashes),
            'success': 0,
            'skipped': 0,
            'failed': 0,
            'errors': []
        }
        
        start_time = time.time()
        
        # Process each hash
        for i, tx_hash in enumerate(hashes, 1):
            try:
                success, message = self.process_hash(tx_hash, i, len(hashes))
                
                if success:
                    if "already exists" in message.lower():
                        stats['skipped'] += 1
                    else:
                        stats['success'] += 1
                else:
                    stats['failed'] += 1
                    stats['errors'].append(f"{tx_hash[:16]}: {message}")
                
                # Rate limiting (except for last item)
                if i < len(hashes):
                    time.sleep(delay_seconds)
                    
            except KeyboardInterrupt:
                print("\n🛑 Bulk import interrupted by user")
                break
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                stats['failed'] += 1
                stats['errors'].append(f"{tx_hash[:16]}: {str(e)}")
        
        # Final report
        elapsed_time = time.time() - start_time
        
        print(f"\n📊 BULK IMPORT COMPLETE")
        print("=" * 30)
        print(f"⏱️ Total time: {elapsed_time:.1f} seconds")
        print(f"📋 Total processed: {stats['total']}")
        print(f"✅ Successfully logged: {stats['success']}")
        print(f"⏭️ Skipped (duplicates): {stats['skipped']}")
        print(f"❌ Failed: {stats['failed']}")
        
        if stats['errors']:
            print(f"\n❌ ERRORS ({len(stats['errors'])}):")
            for error in stats['errors'][:10]:  # Show first 10 errors
                print(f"   {error}")
            if len(stats['errors']) > 10:
                print(f"   ... and {len(stats['errors']) - 10} more errors")
        
        # Show final stats
        if self.sheets_manager:
            final_stats = self.sheets_manager.get_stats()
            if final_stats:
                print(f"\n📊 Google Sheets now contains: {final_stats['total_transactions']} total transactions")
        
        sheets_url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}"
        print(f"📋 View results: {sheets_url}")
        print("✅ All transactions now have correct TO and TOKEN addresses!")

def main():
    """Main entry point"""
    loader = BulkLoader()
    
    if not loader.csv_exists:
        print("\n❌ Setup required:")
        print(f"   1. Place your CSV file as: {CSV_FILE}")
        print("   2. Ensure first column contains transaction hashes")
        return
    
    if not loader.sheets_manager or not loader.sheets_manager.is_connected:
        print("\n❌ Setup required:")
        print("   1. Ensure GOOGLE_SHEET_ID is set in .env")
        print("   2. Ensure service_account.json exists")
        print("   3. Verify Google Sheets permissions")
        return
    
    # Confirmation prompt
    try:
        print(f"\n⚠️ This will bulk import transactions from {CSV_FILE}")
        print("   Duplicates will be automatically skipped")
        print("   This operation may take several minutes")
        print("   🔧 UPDATED: Now uses correct TO/TOKEN address extraction")
        
        confirm = input("\n🤔 Continue? (y/N): ").strip().lower()
        
        if confirm in ['y', 'yes']:
            loader.bulk_import(delay_seconds=2)
        else:
            print("❌ Bulk import cancelled")
            
    except KeyboardInterrupt:
        print("\n❌ Bulk import cancelled")

if __name__ == "__main__":
    main()