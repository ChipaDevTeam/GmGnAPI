"""
Enhanced example showing proper data parsing from GMGN API.

Built with Chipa Editor - https://chipaeditor.com/?utm_source=code&utm_medium=example&utm_campaign=gmgn_api&utm_term=enhanced&utm_content=docstring
"""

import asyncio
import logging
from src.gmgnapi import GmGnClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def format_pool_info(pool_data):
    """Format pool information in a readable way."""
    if not pool_data or not isinstance(pool_data, list):
        return "Invalid pool data"
    
    result = []
    for batch in pool_data:
        if 'p' in batch:  # pools array
            for pool in batch['p']:
                token_info = pool.get('bti', {})
                symbol = token_info.get('s', 'Unknown')
                name = token_info.get('n', 'Unknown')
                exchange = pool.get('ex', 'Unknown')
                pool_address = pool.get('pa', 'N/A')
                market_cap = token_info.get('mc')
                price = token_info.get('p', 0)
                
                result.append(f"""
🏊 New Pool Created!
   Token: {symbol} ({name})
   Exchange: {exchange}
   Pool Address: {pool_address}
   Price: ${price:.2e} USD
   Market Cap: ${market_cap:,} USD""" if market_cap else f"""
🏊 New Pool Created!
   Token: {symbol} ({name})
   Exchange: {exchange}
   Pool Address: {pool_address}
   Price: ${price:.2e} USD""")
    
    return "\n".join(result)

async def handle_new_pool(data):
    """Handle new pool events with better formatting."""
    formatted_info = format_pool_info(data)
    print(formatted_info)

async def handle_token_launch(data):
    """Handle token launch events."""
    logger.info(f"🚀 Token launch data received")
    print(f"Launch data: {data}")

async def main():
    client = GmGnClient()
    
    # Register event handlers
    client.on("new_pool_info", handle_new_pool)
    client.on("new_launched_info", handle_token_launch)
    
    try:
        logger.info("🌐 Connecting to GMGN WebSocket...")
        await client.connect()
        
        logger.info("📡 Subscribing to Solana data streams...")
        await client.subscribe_new_pools(chain="sol")
        await client.subscribe_token_launches(chain="sol")
        
        logger.info("✅ Connected! Monitoring real-time Solana pool creations...")
        logger.info("Press Ctrl+C to stop")
        print("=" * 60)
        
        # Keep the connection alive
        await client.run_forever()
        
    except KeyboardInterrupt:
        logger.info("🛑 Stopping monitor...")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
    finally:
        await client.disconnect()
        logger.info("👋 Disconnected from GMGN WebSocket")

if __name__ == "__main__":
    asyncio.run(main())
