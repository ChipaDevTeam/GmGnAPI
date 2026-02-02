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
    # Cookies from your browser session (required for connection)
    cookies = {
        "__cf_bm": "AJoMSE2nVGkQBw517YaUKbnh2fTKue.rIiVFPk1adEI-1770052484-1.0.1.1-5_Ma1MK0d4faXcUfqgqkh3icGFL.qfTs0T9.alJfG45Nm9u7yGOaihmp0jQutIrJoP2Q5R6fpjVYmJHOtiKwPAwznSyHmerusjuzfP_LmN8",
        "_ga": "GA1.1.1679316283.1770052488",
        "sid": "gmgn%7Cb832083bf7577661314742d93fcc3fa4",
        "_ga_UGLVBMV4Z0": "GS1.2.1770052551374447.b660ff2d16ef55e527fbd41da44a650a.LPefI3GLwvJAZvcCerWQEA%3D%3D.VXM%2FiSQDiZQqEIk2yytV%2FQ%3D%3D.05A79i5172t4yba6oMhJuQ%3D%3D.oHMWEJIlhkk7YVBO3T8U5w%3D%3D",
        "_ga_0XM0LYXGC8": "GS2.1.s1770052487$o1$g1$t1770052644$j60$l0$h0",
    }

    # Use the device_id from the captured session
    device_id = "f3188121-8e81-4752-9eee-0ea242354a03"
    fp_did = "b4d8308ddd0df730f26ffdffcb5ecd03"
    user_uuid = "f41873c323d65843" # 16 chars from curl (different from device_id)
    
    client = GmGnClient(cookies=cookies, device_id=device_id, fp_did=fp_did, user_uuid=user_uuid)
    
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