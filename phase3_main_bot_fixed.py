#!/usr/bin/env python3
"""
Phase 3 - Complete Transaction Bot with !log Command - FIXED VERSION
Clean integration with modular Google Sheets manager
"""

import os
import time
import re
import requests
from datetime import datetime
from slack_sdk import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from dotenv import load_dotenv

# Import our Google Sheets manager
from sheets_manager import SheetsManager

# Load environment variables
load_dotenv()

# Configuration
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_APP_TOKEN = os.environ.get('SLACK_APP_TOKEN')
CHANNEL_ID = os.environ.get('CHANNEL_ID')
GOOGLE_SHEETS_CREDS_FILE = os.environ.get('GOOGLE_SHEETS_CREDS_FILE', 'service_account.json')
GOOGLE_SHEET_ID = os.environ.get('GOOGLE_SHEET_ID')

# Transaction hash validation (64 hex characters)
HASH_PATTERN = re.compile(r'^[a-fA-F0-9]{64}$')

print("🚀 PHASE 3 - COMPLETE TRANSACTION BOT WITH !log COMMAND - FIXED")
print("=" * 60)

class CompleteTransactionBot:
    def __init__(self):
        """Initialize the complete transaction bot"""
        print("🔧 Initializing Complete Transaction Bot...")
        
        # Check Slack environment variables
        if not all([SLACK_BOT_TOKEN, SLACK_APP_TOKEN, CHANNEL_ID]):
            print("❌ Missing Slack environment variables!")
            self.bot_user_id = None
            return
        
        # Initialize Slack clients
        self.web_client = WebClient(token=SLACK_BOT_TOKEN)
        self.socket_client = SocketModeClient(
            app_token=SLACK_APP_TOKEN,
            web_client=self.web_client
        )
        
        # Get bot info
        try:
            auth_response = self.web_client.auth_test()
            self.bot_user_id = auth_response["user_id"]
            self.bot_name = auth_response["user"]
            print(f"✅ Bot authenticated as: {self.bot_name} ({self.bot_user_id})")
        except Exception as e:
            print(f"❌ Slack authentication failed: {e}")
            self.bot_user_id = None
            return
        
        # Initialize Google Sheets manager
        self.sheets_manager = None
        if GOOGLE_SHEET_ID and os.path.exists(GOOGLE_SHEETS_CREDS_FILE):
            print("🔗 Initializing Google Sheets connection...")
            self.sheets_manager = SheetsManager(GOOGLE_SHEETS_CREDS_FILE, GOOGLE_SHEET_ID)
            
            if self.sheets_manager.is_connected:
                stats = self.sheets_manager.get_stats()
                if stats:
                    print(f"✅ Google Sheets connected: {stats['total_transactions']} transactions logged")
                else:
                    print("✅ Google Sheets connected")
            else:
                print("⚠️ Google Sheets connection failed - !log command will be disabled")
        else:
            print("⚠️ Google Sheets not configured - !log command disabled")
    
    def validate_hash(self, hash_str):
        """Validate transaction hash format"""
        return bool(HASH_PATTERN.match(hash_str.strip()))
    
    def get_trx_price(self):
        """Get current TRX price in USD"""
        try:
            response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=tron&vs_currencies=usd", timeout=5)
            if response.status_code == 200:
                return response.json()['tron']['usd']
        except:
            pass
        return 0.07  # Fallback price
    
    def parse_command(self, message_text):
        """Parse command from bot mention message"""
        # Remove bot mention
        clean_message = message_text.replace(f'<@{self.bot_user_id}>', '').strip()
        
        # Check command type
        if clean_message.startswith('!get'):
            command = '!get'
            clean_message = clean_message[4:].strip()
        elif clean_message.startswith('!log'):
            command = '!log'
            clean_message = clean_message[4:].strip()
        elif clean_message.startswith('!help'):
            command = '!help'
            return command, None  # No hash needed for help
        else:
            return None, None
        
        # Extract hash from quotes
        hash_match = re.search(r'"([a-fA-F0-9]{64})"', clean_message)
        if hash_match:
            return command, hash_match.group(1)
        
        # Try without quotes (direct hash)
        parts = clean_message.split()
        if len(parts) >= 1:
            potential_hash = parts[0]
            if self.validate_hash(potential_hash):
                return command, potential_hash
        
        return command, None
    
    def fetch_transaction_data(self, tx_hash):
        """Fetch transaction data from Tronscan API"""
        url = "https://apilist.tronscan.org/api/transaction-info"
        
        try:
            print(f"📡 Fetching transaction: {tx_hash[:16]}...")
            
            response = requests.get(
                url, 
                params={'hash': tx_hash}, 
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('contractRet') or data.get('contract_map') or data.get('contractInfo'):
                    print("✅ Transaction data retrieved")
                    return True, data
                else:
                    return False, "Transaction not found on TRON blockchain"
            else:
                return False, f"API error: {response.status_code}"
                
        except requests.exceptions.Timeout:
            return False, "Request timeout - please try again"
        except Exception as e:
            return False, f"Network error: {str(e)[:100]}"
    
    def format_comprehensive_analysis(self, tx_data, tx_hash):
        """Format comprehensive transaction analysis (for !get command) - FIXED VERSION"""
        try:
            trx_price = self.get_trx_price()
            
            # Extract CSV fields
            block = tx_data.get('block', '')
            confirmed = tx_data.get('confirmed', True)
            confirmations = tx_data.get('confirmations', 0)
            contract_ret = tx_data.get('contractRet', '')
            status = 'CONFIRMED' if confirmed else 'PENDING'
            
            # Format timestamp
            timestamp = tx_data.get('timestamp')
            if timestamp:
                dt = datetime.fromtimestamp(timestamp / 1000)
                time_utc = dt.strftime('%Y-%m-%d %H:%M:%S')
            else:
                time_utc = ''
            
            # FIXED: Proper address and token extraction
            from_addr = tx_data.get('ownerAddress', '')
            
            # Token data
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
                total_cost_usdt = total_cost_trx * trx_price
            else:
                total_cost_trx = total_cost_usdt = 0
            
            block_display = str(block)
            
            # Check if sheets are enabled for ready-to-log message
            sheets_enabled = self.sheets_manager and self.sheets_manager.is_connected
            ready_to_log_msg = f"\n💾 *Ready to log?* Use: `@{self.bot_name} !log \"{tx_hash}\"`" if sheets_enabled else ""
            
            response = f"""🔍 *Transaction Details* (CSV Fields)

*Hash:* {tx_hash}

• *Block:* {block_display}
• *Time (UTC):* {time_utc}
• *From:* {from_addr}
• *To:* {to_addr}
• *Token:* {token_contract}
• *Token Symbol:* {token_symbol}
• *Amount:* {amount_formatted} {token_symbol}
• *Result:* {contract_ret}
• *Status:* {status}

💰 *Costs:*
• *Total Cost:* {total_cost_trx:.6f} TRX (${total_cost_usdt:.4f} USD)
• *Confirmations:* {confirmations:,}

⏰ *Checked:* {datetime.now().strftime('%H:%M:%S UTC')}
📊 *Ready for logging to CSV*{ready_to_log_msg}"""

            return response
            
        except Exception as e:
            print(f"Error in analysis: {e}")
            return f"""Analysis Error

*Hash:* {tx_hash}
*Error:* {str(e)[:100]}"""
    
    def handle_app_mentions(self, client: SocketModeClient, req: SocketModeRequest):
        """Handle app mention events"""
        try:
            # Acknowledge the request
            response = SocketModeResponse(envelope_id=req.envelope_id)
            client.send_socket_mode_response(response)
            
            # Extract event data
            event = req.payload.get("event", {})
            if event.get("type") != "app_mention":
                return
            
            channel_id = event.get("channel")
            user_id = event.get("user")
            message_text = event.get("text", "")
            
            print(f"\n📨 Received mention from {user_id}: {message_text}")
            
            # Don't respond to own messages
            if user_id == self.bot_user_id:
                return
            
            # Parse command
            command, tx_hash = self.parse_command(message_text)
            
            if command in ['!get', '!log', '!help']:
                
                # Handle !help command first (no hash needed)
                if command == '!help':
                    sheets_status = "✅ Enabled" if (self.sheets_manager and self.sheets_manager.is_connected) else "❌ Disabled"
                    
                    # Create Google Sheets URL
                    sheets_url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}" if GOOGLE_SHEET_ID else "Not configured"
                    
                    help_message = f"""🤖 *CryptoHashBot v3.0 - User Guide*

*Available Commands:*

📊 *@{self.bot_name} !get "hash_id"*  
• Comprehensive transaction analysis
• All CSV fields displayed
• Cost calculations with USD conversion
• Ready-to-log format preview

💾 *@{self.bot_name} !log "hash_id"*  {sheets_status}
• Automatically save to Google Sheets
• Includes duplicate prevention
• Full audit trail with user tracking
• Real-time TRX pricing included

❓ *@{self.bot_name} !help*
• Show this user guide

*Usage Example:*
`@{self.bot_name} !get "3bb06f21d607e8c19b0638c6f9ecd3986c377d47116f737ab1964d324223bef9"`

*Important Notes:*
• Hash must be exactly 64 hexadecimal characters
• Use quotes around the hash for best results
• !log command prevents duplicate entries
• All times displayed in UTC timezone

*Google Sheets Integration:* {sheets_status}
• Professional accounting format
• Real-time cost calculations  
• Full transaction audit trail
• 📋 *View all logged transactions:* <{sheets_url}|Open Transaction Log>

*Transaction Database:*
All successful !log commands are saved to our comprehensive Google Sheets database with complete transaction details, costs, and audit information.

Ready to analyze TRON transactions! 🚀"""

                    self.web_client.chat_postMessage(
                        channel=channel_id,
                        text=help_message,
                        mrkdwn=True
                    )
                    return
                
                # For other commands, check if hash is provided
                if tx_hash is None:
                    # Invalid or missing hash
                    error_msg = f"""Invalid or missing transaction hash

*Usage:* `@{self.bot_name} {command} "hash_id"`

*Example:* `@{self.bot_name} {command} "3bb06f21d607e8c19b0638c6f9ecd3986c377d47116f737ab1964d324223bef9"`

*Note:* Hash must be 64 hexadecimal characters

*Need help?* Try `@{self.bot_name} !help`"""

                    self.web_client.chat_postMessage(
                        channel=channel_id,
                        text=error_msg,
                        mrkdwn=True
                    )
                    return
                
                # Check if !log command when sheets not available
                if command == '!log' and (not self.sheets_manager or not self.sheets_manager.is_connected):
                    error_msg = """Google Sheets Integration Not Available

The `!log` command is currently unavailable. 

*Available Commands:*
• `!get` - Comprehensive analysis
• `!help` - User guide

Please contact admin to enable Google Sheets logging."""

                    self.web_client.chat_postMessage(
                        channel=channel_id,
                        text=error_msg,
                        mrkdwn=True
                    )
                    return
                
                # Valid hash - fetch transaction data
                print(f"🔍 Processing {command} command for hash: {tx_hash[:16]}...")
                
                # Send "processing" message
                if command == '!log':
                    processing_msg = f"💾 Logging transaction *{tx_hash}* to Google Sheets..."
                else:
                    processing_msg = f"🔍 Analyzing transaction *{tx_hash}* on TRON blockchain..."
                
                self.web_client.chat_postMessage(
                    channel=channel_id,
                    text=processing_msg,
                    mrkdwn=True
                )
                
                # Fetch transaction data
                success, result = self.fetch_transaction_data(tx_hash)
                
                if success:
                    # Handle different commands
                    if command == '!get':
                        response_message = self.format_comprehensive_analysis(result, tx_hash)
                    
                    elif command == '!log':
                        # Save to Google Sheets (using user_id directly)
                        trx_price = self.get_trx_price()
                        save_success, save_result = self.sheets_manager.log_transaction(
                            result, tx_hash, user_id, trx_price
                        )
                        
                        if save_success:
                            stats = self.sheets_manager.get_stats()
                            total_logged = stats['total_transactions'] if stats else 'N/A'
                            
                            # Create Google Sheets URL
                            sheets_url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}"
                            
                            response_message = f"""✅ *Transaction Successfully Logged*

*Hash:* {tx_hash}
*Result:* {save_result}
*Logged by:* <@{user_id}>
*Timestamp:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

📊 *Total transactions logged:* {total_logged}
🔒 *Duplicate protection:* Active
📋 *View spreadsheet:* <{sheets_url}|{stats['sheet_title'] if stats else 'Open Google Sheets'}>"""
                        else:
                            response_message = f"""⚠️ *Logging Failed*

*Hash:* {tx_hash}
*Error:* {save_result}

Please try again or contact admin if the issue persists."""
                    
                    self.web_client.chat_postMessage(
                        channel=channel_id,
                        text=response_message,
                        mrkdwn=True
                    )
                    print(f"✅ {command} response sent")
                else:
                    # Send error message
                    error_msg = f"""Transaction Lookup Failed

*Hash:* {tx_hash}
*Error:* {result}

Please verify the hash is correct and try again.

*Need help?* Try `@{self.bot_name} !help`"""

                    self.web_client.chat_postMessage(
                        channel=channel_id,
                        text=error_msg,
                        mrkdwn=True
                    )
                    print(f"❌ Error: {result}")
            
            elif any(cmd in message_text for cmd in ['!get', '!log', '!help']):
                # Recognized command but couldn't parse properly
                sheets_status = "✅ Enabled" if (self.sheets_manager and self.sheets_manager.is_connected) else "❌ Disabled"
                
                help_msg = f"""🤖 *Transaction Commands Help*

*Available Commands:*
• `@{self.bot_name} !get "hash"` - Comprehensive analysis
• `@{self.bot_name} !log "hash"` - Save to Google Sheets {sheets_status}
• `@{self.bot_name} !help` - Complete user guide

*Examples:*
• `@{self.bot_name} !help`
• `@{self.bot_name} !get "3bb06f21d607e8c19b0638c6f9ecd3986c377d47116f737ab1964d324223bef9"`
• `@{self.bot_name} !log "3bb06f21d607e8c19b0638c6f9ecd3986c377d47116f737ab1964d324223bef9"`

*Notes:*
• Hash must be exactly 64 hexadecimal characters
• Use quotes around the hash for best results
• !log command includes duplicate prevention"""

                self.web_client.chat_postMessage(
                    channel=channel_id,
                    text=help_msg,
                    mrkdwn=True
                )
            
            else:
                # General mention without specific command
                sheets_status = "✅ Ready" if (self.sheets_manager and self.sheets_manager.is_connected) else "⚠️ Setup Required"
                
                help_msg = f"""🤖 *Hello! I'm CryptoHashBot v3.0*

*Available Commands:*
• `@{self.bot_name} !get "hash_id"` - Comprehensive analysis
• `@{self.bot_name} !log "hash_id"` - Save to Google Sheets
• `@{self.bot_name} !help` - Complete user guide

*Google Sheets Integration:* {sheets_status}

*Quick Start:*
• `@{self.bot_name} !help` _(complete guide)_
• `@{self.bot_name} !get "abc123..."` _(analyze transaction)_
• `@{self.bot_name} !log "abc123..."` _(save to spreadsheet)_

*Features:*
🔒 Duplicate prevention
📊 Automatic CSV formatting
💰 Real-time TRX pricing

Ready to analyze and log transactions! 🚀"""

                self.web_client.chat_postMessage(
                    channel=channel_id,
                    text=help_msg,
                    mrkdwn=True
                )
        
        except Exception as e:
            print(f"❌ Error in mention handler: {e}")
    
    def start(self):
        """Start the bot"""
        if not self.bot_user_id:
            print("❌ Cannot start bot - authentication failed")
            return
        
        # Register the mention handler
        self.socket_client.socket_mode_request_listeners.append(self.handle_app_mentions)
        
        sheets_status = "✅ ENABLED" if (self.sheets_manager and self.sheets_manager.is_connected) else "❌ DISABLED"
        
        print(f"\n🚀 Starting Complete Transaction Bot...")
        print(f"📡 Listening for @{self.bot_name} mentions in channel {CHANNEL_ID}")
        print(f"📊 Google Sheets Integration: {sheets_status}")
        print("\n💬 *AVAILABLE COMMANDS:*")
        print(f"   @{self.bot_name} !get \"hash\"      - Comprehensive analysis")
        print(f"   @{self.bot_name} !log \"hash\"      - Save to Google Sheets {sheets_status}")
        print(f"   @{self.bot_name} !help             - Complete user guide")
        print("\n🧪 *TEST WITH:*")
        print(f"   @{self.bot_name} !help")
        print(f"   @{self.bot_name} !get \"3bb06f21d607e8c19b0638c6f9ecd3986c377d47116f737ab1964d324223bef9\"")
        print("\n🔄 Bot running... Press Ctrl+C to stop")
        
        try:
            self.socket_client.connect()
            
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user")
        except Exception as e:
            print(f"❌ Bot error: {e}")
        finally:
            self.socket_client.disconnect()

def main():
    """Main entry point"""
    bot = CompleteTransactionBot()
    if bot.bot_user_id:
        bot.start()
    else:
        print("❌ Bot initialization failed")

if __name__ == "__main__":
    main()