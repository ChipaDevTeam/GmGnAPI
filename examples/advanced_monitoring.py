"""
Advanced usage example with wallet monitoring.
"""

import asyncio
import logging
import os
from decimal import Decimal
from gmgnapi import GmGnClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class TradingMonitor:
    """Advanced trading monitor with analytics."""
    
    def __init__(self):
        self.pool_count = 0
        self.launch_count = 0
        self.total_volume = Decimal("0")
        
    async def handle_new_pool(self, data):
        """Track new pool creations."""
        self.pool_count += 1
        
        logger.info(f"🏊 Pool #{self.pool_count} created!")
        logger.info(f"   Token: {data.get('token_address', 'N/A')}")
        
        liquidity = data.get('initial_liquidity_usd')
        if liquidity:
            logger.info(f"   Initial Liquidity: ${Decimal(str(liquidity)):,.2f}")
            
    async def handle_token_launch(self, data):
        """Track token launches."""
        self.launch_count += 1
        
        logger.info(f"🚀 Launch #{self.launch_count}!")
        logger.info(f"   {data.get('name', 'Unknown')} ({data.get('symbol', 'N/A')})")
        
        market_cap = data.get('market_cap_usd')
        if market_cap:
            logger.info(f"   Market Cap: ${Decimal(str(market_cap)):,.2f}")
            
    async def handle_wallet_trade(self, data):
        """Monitor specific wallet trades."""
        logger.info(f"💰 Wallet trade detected!")
        
        for trade in data.get('trades', []):
            trade_type = trade.get('trade_type', 'unknown')
            amount_usd = trade.get('amount_usd', 0)
            token_addr = trade.get('token_address', 'N/A')
            
            self.total_volume += Decimal(str(amount_usd))
            
            logger.info(f"   {trade_type.upper()}: ${Decimal(str(amount_usd)):,.2f}")
            logger.info(f"   Token: {token_addr}")
            
    async def handle_chain_stats(self, data):
        """Log chain statistics."""
        logger.info("📊 Chain Statistics Update:")
        logger.info(f"   Total Pools: {data.get('total_pools', 'N/A'):,}")
        logger.info(f"   New Pools 24h: {data.get('new_pools_24h', 'N/A'):,}")
        
        volume_24h = data.get('total_volume_24h_usd')
        if volume_24h:
            logger.info(f"   24h Volume: ${Decimal(str(volume_24h)):,.2f}")
            
    def print_summary(self):
        """Print monitoring summary."""
        logger.info("📈 Session Summary:")
        logger.info(f"   Pools Detected: {self.pool_count}")
        logger.info(f"   Launches Detected: {self.launch_count}")
        logger.info(f"   Total Volume Tracked: ${self.total_volume:,.2f}")


async def main():
    """Advanced monitoring example."""
    # Get access token from environment (if available)
    access_token = os.getenv('GMGN_ACCESS_TOKEN')
    wallet_to_monitor = os.getenv('WALLET_ADDRESS', '9F5WjUyPaRmFbnwJofAVhPWjCPUQ9Xaiss3ErsJRjGNf')
    
    # Create monitor instance
    monitor = TradingMonitor()
    
    # Create client with custom settings
    client = GmGnClient(
        auto_reconnect=True,
        max_reconnect_attempts=10,
        reconnect_delay=3.0,
        access_token=access_token
    )
    
    # Register all event handlers
    client.on("new_pool_info", monitor.handle_new_pool)
    client.on("new_launched_info", monitor.handle_token_launch)
    client.on("chain_stat", monitor.handle_chain_stats)
    
    # Register wallet monitoring if token available
    if access_token:
        client.on("wallet_trade_data", monitor.handle_wallet_trade)
        logger.info(f"🔐 Will monitor wallet: {wallet_to_monitor}")
    else:
        logger.warning("⚠️  No access token - wallet monitoring disabled")
    
    try:
        logger.info("🌐 Starting advanced GMGN monitoring...")
        await client.connect()
        
        # Subscribe to all public channels
        await client.subscribe_all_channels(chain="sol")
        
        # Subscribe to wallet data if authenticated
        if access_token:
            await client.subscribe_wallet_trades(
                chain="sol",
                wallet_address=wallet_to_monitor
            )
            
        logger.info("✅ All subscriptions active!")
        logger.info("📡 Monitoring Solana blockchain activity...")
        logger.info("Press Ctrl+C to stop and see summary")
        
        # Run monitoring
        await client.run_forever()
        
    except KeyboardInterrupt:
        logger.info("🛑 Stopping monitor...")
        monitor.print_summary()
    except Exception as e:
        logger.error(f"❌ Error: {e}")
    finally:
        await client.disconnect()
        logger.info("👋 Monitor stopped")


if __name__ == "__main__":
    asyncio.run(main())
