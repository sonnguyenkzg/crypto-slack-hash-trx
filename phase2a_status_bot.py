#!/usr/bin/env python3
"""
Phase 2A - Transaction Status Bot
Adds !status command to check transaction details from Tronscan API
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

# Load environment variables
load_dotenv()

# Configuration
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_APP_TOKEN = os.environ.get('SLACK_APP_TOKEN')
CHANNEL_ID = os.environ.get('CHANNEL_ID')

# Transaction hash validation (64 hex characters)
HASH_PATTERN = re.compile(r'^[a-fA-F0-9]{64}$')

print("🚀 PHASE 2A - TRANSACTION STATUS BOT")
print("=" * 50)

class TransactionStatusBot:
    def __init__(self):
        """Initialize the transaction status bot"""
        print("🔧 Initializing Transaction Status Bot...")
        
        # Check environment variables
        if not all([SLACK_BOT_TOKEN, SLACK_APP_TOKEN, CHANNEL_ID]):
            print("❌ Missing environment variables!")
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
            print(f"❌ Authentication failed: {e}")
            self.bot_user_id = None
    
    def validate_hash(self, hash_str):
        """Validate transaction hash format"""
        return bool(HASH_PATTERN.match(hash_str.strip()))
    
    def parse_command(self, message_text):
        """
        Parse command from bot mention message.
        Expected: @bot !status "hash_id"
        """
        # Remove bot mention
        clean_message = message_text.replace(f'<@{self.bot_user_id}>', '').strip()
        
        # Check if it starts with !status
        if not clean_message.startswith('!status'):
            return None, None
        
        # Extract hash from quotes
        hash_match = re.search(r'"([a-fA-F0-9]{64})"', clean_message)
        if hash_match:
            return '!status', hash_match.group(1)
        
        # Try without quotes (direct hash after !status)
        parts = clean_message.split()
        if len(parts) >= 2:
            potential_hash = parts[1]
            if self.validate_hash(potential_hash):
                return '!status', potential_hash
        
        return '!status', None
    
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
                
                # Check if we have transaction data - look for contractRet or other indicators
                if data.get('contractRet') or data.get('contract_map') or data.get('contractInfo'):
                    print("✅ Transaction data retrieved")
                    return True, data  # Return the full response, not data['data']
                else:
                    print(f"⚠️  API Response: {response.text[:200]}")
                    return False, "Transaction not found on TRON blockchain"
            else:
                return False, f"API error: {response.status_code}"
                
        except requests.exceptions.Timeout:
            return False, "Request timeout - please try again"
        except Exception as e:
            return False, f"Network error: {str(e)[:100]}"
    
    def format_transaction_status(self, tx_data, tx_hash):
        """Format transaction data for Slack display"""
        try:
            # Basic info - handle different API response structure
            block = tx_data.get('block', 'N/A')
            confirmed = tx_data.get('confirmed', True)  # Default to true if not specified
            confirmations = tx_data.get('confirmations', 0)
            contract_ret = tx_data.get('contractRet', 'N/A')
            
            # Format timestamp
            timestamp = tx_data.get('timestamp')
            if timestamp:
                dt = datetime.fromtimestamp(timestamp / 1000)
                time_str = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
            else:
                time_str = 'N/A'
            
            # Transaction details
            from_addr = tx_data.get('ownerAddress', 'N/A')
            to_addr = tx_data.get('toAddress', 'N/A')
            
            # Token transfer info
            token_info = ""
            trc20_transfers = tx_data.get('trc20TransferInfo', [])
            
            # Also check for tokenTransferInfo (alternative field name)
            if not trc20_transfers:
                if tx_data.get('tokenTransferInfo'):
                    # Handle single transfer object
                    transfer = tx_data.get('tokenTransferInfo')
                    if isinstance(transfer, dict):
                        trc20_transfers = [transfer]
                    elif isinstance(transfer, list):
                        trc20_transfers = transfer
            
            if trc20_transfers and len(trc20_transfers) > 0:
                transfer = trc20_transfers[0]
                symbol = transfer.get('symbol', 'N/A')
                amount_str = transfer.get('amount_str', '0')
                decimals = transfer.get('decimals', 6)
                
                try:
                    amount = int(amount_str) / (10 ** decimals)
                    token_info = f"• *Amount:* {amount:,.{decimals}f} {symbol}"
                except:
                    token_info = f"• *Amount:* {amount_str} {symbol}"
            
            # Cost info
            cost_info = ""
            cost = tx_data.get('cost', {})
            if isinstance(cost, dict):
                energy_fee = cost.get('energy_fee', 0) / 1000000  # Convert from SUN to TRX
                if energy_fee > 0:
                    cost_info = f"• *Fee:* {energy_fee:.6f} TRX"
            
            # Status icons
            status_icon = "✅" if confirmed else "⏳"
            result_icon = "✅" if contract_ret == "SUCCESS" else "❌"
            
            # Handle block formatting
            block_str = f"{block:,}" if isinstance(block, int) else str(block)
            
            response = f"""🔍 *Transaction Status*

*Hash:* `{tx_hash[:16]}...`

{status_icon} *Status:* {'CONFIRMED' if confirmed else 'PENDING'}
{result_icon} *Result:* {contract_ret}
📊 *Confirmations:* {confirmations:,}
🕐 *Time:* {time_str}
📦 *Block:* {block_str}

📍 *Addresses:*
• *From:* `{from_addr[:20]}...`
• *To:* `{to_addr[:20]}...`

{token_info}
{cost_info}

⏰ *Checked:* {datetime.now().strftime('%H:%M:%S UTC')}"""

            return response
            
        except Exception as e:
            print(f"❌ Error formatting transaction: {e}")
            
            # Fallback: show raw available data
            available_fields = list(tx_data.keys())
            return f"""🔍 *Transaction Found* (Raw Data)

*Hash:* `{tx_hash[:16]}...`
*Result:* {tx_data.get('contractRet', 'N/A')}

*Available Fields:* {', '.join(available_fields[:10])}

_Note: Data formatting needs adjustment_"""
    
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
            
            if command == "!status":
                if tx_hash is None:
                    # Invalid or missing hash
                    error_msg = """❌ *Invalid or missing transaction hash*

*Usage:* `@CryptoHashBot !status "hash_id"`

*Example:* `@CryptoHashBot !status "3bb06f21d607e8c19b0638c6f9ecd3986c377d47116f737ab1964d324223bef9"`

*Note:* Hash must be 64 hexadecimal characters"""

                    self.web_client.chat_postMessage(
                        channel=channel_id,
                        text=error_msg,
                        mrkdwn=True
                    )
                    return
                
                # Valid hash - fetch transaction data
                print(f"🔍 Processing !status command for hash: {tx_hash[:16]}...")
                
                # Send "processing" message
                self.web_client.chat_postMessage(
                    channel=channel_id,
                    text=f"🔍 Checking transaction `{tx_hash[:16]}...` on TRON blockchain...",
                    mrkdwn=True
                )
                
                # Fetch transaction data
                success, result = self.fetch_transaction_data(tx_hash)
                
                if success:
                    # Format and send transaction status
                    status_message = self.format_transaction_status(result, tx_hash)
                    self.web_client.chat_postMessage(
                        channel=channel_id,
                        text=status_message,
                        mrkdwn=True
                    )
                    print("✅ Transaction status sent")
                else:
                    # Send error message
                    error_msg = f"""❌ *Transaction Lookup Failed*

*Hash:* `{tx_hash[:16]}...`
*Error:* {result}

Please verify the hash is correct and try again."""

                    self.web_client.chat_postMessage(
                        channel=channel_id,
                        text=error_msg,
                        mrkdwn=True
                    )
                    print(f"❌ Error: {result}")
            
            elif "!status" in message_text:
                # Recognized !status but couldn't parse properly
                help_msg = """🤖 *Transaction Status Command Help*

*Usage:* `@CryptoHashBot !status "transaction_hash"`

*Examples:*
• `@CryptoHashBot !status "3bb06f21d607e8c19b0638c6f9ecd3986c377d47116f737ab1964d324223bef9"`

*Notes:*
• Hash must be exactly 64 hexadecimal characters
• Use quotes around the hash for best results
• Works with any TRON transaction hash"""

                self.web_client.chat_postMessage(
                    channel=channel_id,
                    text=help_msg,
                    mrkdwn=True
                )
            
            else:
                # General mention without !status
                help_msg = f"""🤖 *Hello! I'm CryptoHashBot*

*Available Commands:*
• `@{self.bot_name} !status "hash_id"` - Check transaction status

*Example:*
`@{self.bot_name} !status "3bb06f21d607e8c19b0638c6f9ecd3986c377d47116f737ab1964d324223bef9"`

*Coming Soon:*
• `!get` - Detailed transaction info  
• `!log` - Save to Google Sheets

Ready to check a transaction? 🚀"""

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
        
        print(f"\n🚀 Starting Transaction Status Bot...")
        print(f"📡 Listening for @{self.bot_name} mentions in channel {CHANNEL_ID}")
        print("\n💬 **NEW COMMAND AVAILABLE:**")
        print(f"   @{self.bot_name} !status \"transaction_hash\"")
        print("\n🧪 **TEST WITH:**")
        print(f"   @{self.bot_name} !status \"3bb06f21d607e8c19b0638c6f9ecd3986c377d47116f737ab1964d324223bef9\"")
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
    bot = TransactionStatusBot()
    if bot.bot_user_id:
        bot.start()
    else:
        print("❌ Bot initialization failed")

if __name__ == "__main__":
    main()