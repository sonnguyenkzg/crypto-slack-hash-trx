#!/usr/bin/env python3
"""
Google Sheets Manager Module
Handles all Google Sheets operations for transaction logging
Separate module for scalability and maintainability
"""

import os
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

class SheetsManager:
    def __init__(self, creds_file, sheet_id):
        """Initialize Google Sheets manager"""
        self.creds_file = creds_file
        self.sheet_id = sheet_id
        self.client = None
        self.sheet = None
        self.worksheet = None
        self.is_connected = False
        
        # Try to connect on initialization
        self.connect()
    
    def connect(self):
        """Connect to Google Sheets"""
        try:
            if not os.path.exists(self.creds_file):
                raise FileNotFoundError(f"Credentials file not found: {self.creds_file}")
            
            if not self.sheet_id:
                raise ValueError("Sheet ID not provided")
            
            # Define scope
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Load credentials
            creds = Credentials.from_service_account_file(
                self.creds_file,
                scopes=scope
            )
            
            # Initialize client
            self.client = gspread.authorize(creds)
            
            # Open the spreadsheet
            self.sheet = self.client.open_by_key(self.sheet_id)
            
            # Get or create Transactions worksheet
            try:
                self.worksheet = self.sheet.worksheet("Transactions")
            except:
                self.worksheet = self.sheet.add_worksheet(
                    title="Transactions",
                    rows=1000,
                    cols=15
                )
                self.setup_headers()
            
            self.is_connected = True
            return True, "Connected successfully"
            
        except Exception as e:
            self.is_connected = False
            return False, f"Connection failed: {str(e)}"
    
    def setup_headers(self):
        """Setup spreadsheet headers (only if new sheet)"""
        headers = [
            "Txn Hash",
            "Block", 
            "Time(UTC)",
            "From",
            "To", 
            "Token",
            "Token Symbol",
            "Amount/TokenID",
            "Result",
            "Status",
            "Confirmations",
            "Total Cost TRX",
            "Total Cost USD",
            "Logged By",
            "Logged At(UTC)"
        ]
        
        self.worksheet.insert_row(headers, 1)
    
    def check_duplicate(self, tx_hash):
        """Check if transaction hash already exists"""
        if not self.is_connected:
            return False
        
        try:
            # Get all values in the first column (Txn Hash)
            hash_column = self.worksheet.col_values(1)
            return tx_hash in hash_column
        except Exception as e:
            print(f"Error checking duplicates: {e}")
            return False
    
    def prepare_transaction_row(self, tx_data, tx_hash, user_id, trx_price):
        """Prepare transaction data for spreadsheet row - FIXED VERSION"""
        try:
            # Basic fields
            block = str(tx_data.get('block', ''))
            
            # Format timestamp
            timestamp = tx_data.get('timestamp')
            if timestamp:
                dt = datetime.fromtimestamp(timestamp / 1000)
                time_utc = dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                time_utc = ''
            
            # FIXED: Proper address extraction
            from_addr = tx_data.get('ownerAddress', '')
            
            # Transaction status
            contract_ret = tx_data.get('contractRet', '')
            confirmed = tx_data.get('confirmed', True)
            status = 'CONFIRMED' if confirmed else 'PENDING'
            confirmations = tx_data.get('confirmations', 0)
            
            # FIXED: Token data extraction
            trc20_transfers = tx_data.get('trc20TransferInfo', [])
            if not trc20_transfers and tx_data.get('tokenTransferInfo'):
                transfer = tx_data.get('tokenTransferInfo')
                if isinstance(transfer, dict):
                    trc20_transfers = [transfer]
            
            if trc20_transfers and len(trc20_transfers) > 0:
                transfer = trc20_transfers[0]
                
                # FIXED: Use token transfer addresses, not main transaction addresses
                to_addr = transfer.get('to_address', '')  # ✅ Token transfer recipient
                token_contract = transfer.get('contract_address', '')  # ✅ Token contract
                token_symbol = transfer.get('symbol', '')
                amount_str = transfer.get('amount_str', '0')
                decimals = transfer.get('decimals', 6)
                
                try:
                    amount = int(amount_str) / (10 ** decimals)
                    amount_formatted = f"{amount:.{decimals}f}"
                except:
                    amount_formatted = amount_str
            else:
                # Fallback to main transaction data if no token transfer
                to_addr = tx_data.get('toAddress', '')
                token_contract = ''
                token_symbol = 'TRX'
                amount_formatted = '0.000000'
            
            # Financial data
            cost = tx_data.get('cost', {})
            if isinstance(cost, dict):
                total_cost_trx = (cost.get('fee', 0) + cost.get('energy_fee', 0)) / 1000000
                total_cost_usd = total_cost_trx * trx_price
            else:
                total_cost_trx = total_cost_usd = 0
            
            # Current timestamp for logging (timestamp only, UTC in header)
            logged_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Return row data matching headers
            return [
                tx_hash,
                block,
                time_utc,
                from_addr,
                to_addr,           # ✅ Now correctly uses token transfer 'to_address'
                token_contract,    # ✅ Token contract address
                token_symbol,
                amount_formatted,
                contract_ret,
                status,
                str(confirmations),
                f"{total_cost_trx:.6f}",
                f"{total_cost_usd:.4f}",
                user_id,
                logged_at
            ]
            
        except Exception as e:
            print(f"Error preparing transaction row: {e}")
            return None
    
    def log_transaction(self, tx_data, tx_hash, user_id, trx_price):
        """Log transaction to Google Sheets"""
        if not self.is_connected:
            return False, "Not connected to Google Sheets"
        
        try:
            # Check for duplicates
            if self.check_duplicate(tx_hash):
                return False, "Transaction already logged (duplicate hash)"
            
            # Prepare row data
            row_data = self.prepare_transaction_row(tx_data, tx_hash, user_id, trx_price)
            if not row_data:
                return False, "Failed to prepare transaction data"
            
            # Add row to sheet
            self.worksheet.append_row(row_data)
            
            return True, "Transaction successfully logged to Google Sheets"
            
        except Exception as e:
            print(f"Error logging transaction: {e}")
            return False, f"Error saving to sheets: {str(e)[:100]}"
    
    def get_stats(self):
        """Get basic stats about logged transactions"""
        if not self.is_connected:
            return None
        
        try:
            all_values = self.worksheet.get_all_values()
            total_rows = len(all_values) - 1  # Subtract header row
            return {
                'total_transactions': max(0, total_rows),
                'sheet_title': self.sheet.title,
                'worksheet_title': self.worksheet.title
            }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return None