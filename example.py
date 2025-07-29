import asyncio
import logging
from src.gmgnapi import GmGnClient

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def handle_new_pool(data):
    """Handle new pool events."""
    logger.info(f"🏊 New pool data: {data}")

async def handle_token_launch(data):
    """Handle token launch events."""
    logger.info(f"🚀 Token launch data: {data}")

async def main():
    client = GmGnClient()
    
    # Register event handlers
    client.on("new_pool_info", handle_new_pool)
    client.on("new_launched_info", handle_token_launch)
    
    try:
        # Connect and subscribe to Solana data
        logger.info("Connecting to GMGN WebSocket...")
        await client.connect()
        
        logger.info("Subscribing to data channels...")
        await client.subscribe_new_pools(chain="sol")
        await client.subscribe_token_launches(chain="sol")
        
        logger.info("✅ Connected and listening for messages...")
        logger.info("Press Ctrl+C to stop")
        
        # Listen for real-time updates
        async for message in client.listen():
            logger.info(f"📨 Message: {message.channel}")
            if message.data:
                logger.info(f"   Data: {str(message.data)[:200]}...")  # First 200 chars
                
    except KeyboardInterrupt:
        logger.info("Stopping...")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await client.disconnect()
        logger.info("Disconnected")

if __name__ == "__main__":
    asyncio.run(main())