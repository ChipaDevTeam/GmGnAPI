"""
Basic usage example for GmGnAPI.
"""

import asyncio
import logging
from gmgnapi import GmGnClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def handle_new_pool(data):
    """Handle new pool creation events."""
    logger.info(f"🆕 New pool created!")
    logger.info(f"   Pool: {data.get('pool_address', 'N/A')}")
    logger.info(f"   Token: {data.get('token_address', 'N/A')}")
    logger.info(f"   Chain: {data.get('chain', 'N/A')}")


async def handle_token_launch(data):
    """Handle token launch events."""
    logger.info(f"🚀 Token launched!")
    logger.info(f"   Name: {data.get('name', 'N/A')}")
    logger.info(f"   Symbol: {data.get('symbol', 'N/A')}")
    logger.info(f"   Address: {data.get('token_address', 'N/A')}")


async def handle_pair_update(data):
    """Handle trading pair updates."""
    logger.info(f"📈 Pair update!")
    logger.info(f"   Pair: {data.get('pair_address', 'N/A')}")
    logger.info(f"   Price: ${data.get('price_usd', 'N/A')}")


async def main():
    """Main example function."""
    # Create client instance
    client = GmGnClient(
        auto_reconnect=True,
        max_reconnect_attempts=5
    )
    
    # Register event handlers
    client.on("new_pool_info", handle_new_pool)
    client.on("new_launched_info", handle_token_launch)
    client.on("new_pair_update", handle_pair_update)
    
    try:
        # Connect to GMGN WebSocket
        logger.info("Connecting to GMGN WebSocket...")
        await client.connect()
        
        # Subscribe to data channels
        logger.info("Subscribing to data channels...")
        await client.subscribe_new_pools(chain="sol")
        await client.subscribe_token_launches(chain="sol")
        await client.subscribe_pair_updates(chain="sol")
        await client.subscribe_chain_stats(chain="sol")
        
        logger.info("✅ Connected and subscribed! Listening for messages...")
        logger.info("Press Ctrl+C to stop")
        
        # Listen for messages indefinitely
        await client.run_forever()
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await client.disconnect()
        logger.info("Disconnected from GMGN WebSocket")


if __name__ == "__main__":
    asyncio.run(main())
