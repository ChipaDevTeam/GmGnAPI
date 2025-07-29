"""
Comprehensive example demonstrating advanced GMGN API features.

This example shows:
- Real-time data streaming with filtering
- Data export capabilities
- Monitoring and statistics
- Alert configuration
- Multiple channel subscriptions
"""

import asyncio
import logging
from decimal import Decimal
from pathlib import Path

from gmgnapi import (
    GmGnEnhancedClient,
    TokenFilter,
    DataExportConfig,
    AlertConfig,
    MonitoringStats,
)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AdvancedGmGnMonitor:
    """Advanced monitoring class with comprehensive features."""
    
    def __init__(self):
        # Configure advanced token filtering
        self.token_filter = TokenFilter(
            min_market_cap=Decimal("50000"),  # Minimum $50k market cap
            min_liquidity=Decimal("10000"),   # Minimum $10k liquidity
            min_volume_24h=Decimal("5000"),   # Minimum $5k 24h volume
            min_holder_count=10,              # Minimum 10 holders
            exchanges=["raydium", "orca", "jupiter"],  # Only these exchanges
            exclude_symbols=["SCAM", "TEST", "FAKE"],  # Exclude obvious scams
            max_risk_score=0.7,               # Maximum risk score
        )
        
        # Configure data export
        self.export_config = DataExportConfig(
            enabled=True,
            format="json",  # Could be "csv" or "database"
            file_path="./gmgn_exports",
            max_file_size_mb=50,
            rotation_interval_hours=6,
            compress=True,
            include_metadata=True,
        )
        
        # Configure alerts
        self.alert_config = AlertConfig(
            enabled=True,
            webhook_url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
            conditions=[
                {
                    "type": "new_pool",
                    "min_liquidity": 100000,  # Alert for pools > $100k liquidity
                    "description": "High liquidity new pool detected"
                },
                {
                    "type": "volume_spike",
                    "threshold_multiplier": 5.0,  # 5x volume increase
                    "description": "Volume spike detected"
                }
            ],
            rate_limit_seconds=300,  # Max 1 alert per 5 minutes
        )
        
        # Initialize client with advanced features
        self.client = GmGnEnhancedClient(
            chain="sol",
            auto_reconnect=True,
            reconnect_interval=3.0,
            token_filter=self.token_filter,
            export_config=self.export_config,
            alert_config=self.alert_config,
            rate_limit=100,  # Max 100 messages/second
            max_queue_size=5000,
        )
        
        # Statistics tracking
        self.interesting_pools = []
        self.volume_spikes = []
        self.large_trades = []
        
    async def setup_handlers(self):
        """Setup event handlers for different data types."""
        
        # New pool handler with advanced filtering
        self.client.on_new_pool(self.handle_new_pool)
        
        # Pair update handler for price monitoring
        self.client.on_pair_update(self.handle_pair_update)
        
        # Token launch handler
        self.client.on_token_launch(self.handle_token_launch)
        
        # Chain statistics handler
        self.client.on_chain_stats(self.handle_chain_stats)
        
        # Wallet trades handler (requires authentication)
        self.client.on_wallet_trades(self.handle_wallet_trades)
        
        # General message handler for debugging
        self.client.on_message(self.handle_general_message)
    
    async def handle_new_pool(self, pool_info):
        """Handle new pool creation events."""
        try:
            if not pool_info.pools:
                return
            
            pool = pool_info.pools[0]
            token_info = pool.bti
            
            if not token_info:
                return
            
            # Extract relevant information
            symbol = getattr(token_info, 's', 'Unknown')
            name = getattr(token_info, 'n', 'Unknown')
            market_cap = getattr(token_info, 'mc', 0)
            liquidity = getattr(pool, 'il', 0)
            
            logger.info(
                f"🆕 New Pool: {symbol} ({name}) | "
                f"Market Cap: ${market_cap:,.0f} | "
                f"Liquidity: ${liquidity:,.0f} | "
                f"Pool: {pool.a[:8]}..."
            )
            
            # Track interesting pools
            if market_cap and market_cap > 100000:  # $100k+ market cap
                self.interesting_pools.append({
                    'symbol': symbol,
                    'name': name,
                    'market_cap': market_cap,
                    'liquidity': liquidity,
                    'pool_address': pool.a,
                    'token_address': pool.ba,
                    'timestamp': pool_info.model_dump(),
                })
                
                logger.warning(
                    f"🔥 HIGH VALUE POOL: {symbol} with ${market_cap:,.0f} market cap!"
                )
        
        except Exception as e:
            logger.error(f"Error handling new pool: {e}")
    
    async def handle_pair_update(self, pair_data):
        """Handle trading pair updates."""
        try:
            # Extract price and volume information
            if hasattr(pair_data, 'volume_24h_usd') and pair_data.volume_24h_usd:
                volume = pair_data.volume_24h_usd
                
                # Check for volume spikes
                if volume > Decimal("500000"):  # $500k+ volume
                    logger.warning(
                        f"� HIGH VOLUME: {pair_data.pair_address[:8]}... | "
                        f"24h Volume: ${volume:,.0f}"
                    )
                    
                    self.volume_spikes.append({
                        'pair_address': pair_data.pair_address,
                        'volume_24h': float(volume),
                        'timestamp': pair_data.updated_at,
                    })
        
        except Exception as e:
            logger.error(f"Error handling pair update: {e}")
    
    async def handle_token_launch(self, launch_data):
        """Handle token launch events."""
        try:
            logger.info(
                f"🚀 Token Launch: {launch_data.symbol} ({launch_data.name}) | "
                f"Address: {launch_data.token_address[:8]}..."
            )
            
            if launch_data.initial_price_usd:
                logger.info(f"   Initial Price: ${launch_data.initial_price_usd}")
            
            if launch_data.market_cap_usd:
                logger.info(f"   Market Cap: ${launch_data.market_cap_usd:,.0f}")
        
        except Exception as e:
            logger.error(f"Error handling token launch: {e}")
    
    async def handle_chain_stats(self, stats_data):
        """Handle blockchain statistics."""
        try:
            logger.info(f"📊 Chain Stats Update: {stats_data}")
        except Exception as e:
            logger.error(f"Error handling chain stats: {e}")
    
    async def handle_wallet_trades(self, trade_data):
        """Handle wallet trading activity."""
        try:
            for trade in trade_data.trades:
                if trade.amount_usd > Decimal("10000"):  # $10k+ trades
                    logger.warning(
                        f"🐋 LARGE TRADE: {trade.trade_type.upper()} | "
                        f"${trade.amount_usd:,.0f} | "
                        f"Wallet: {trade.wallet_address[:8]}..."
                    )
                    
                    self.large_trades.append({
                        'type': trade.trade_type,
                        'amount_usd': float(trade.amount_usd),
                        'wallet': trade.wallet_address,
                        'token': trade.token_address,
                        'timestamp': trade.timestamp,
                    })
        
        except Exception as e:
            logger.error(f"Error handling wallet trades: {e}")
    
    async def handle_general_message(self, message):
        """Handle all messages for debugging."""
        # Only log every 100th message to avoid spam
        if hasattr(self, '_message_count'):
            self._message_count += 1
        else:
            self._message_count = 1
        
        if self._message_count % 100 == 0:
            logger.debug(f"Processed {self._message_count} messages")
    
    async def print_periodic_stats(self):
        """Print statistics every 60 seconds."""
        while True:
            await asyncio.sleep(60)
            
            try:
                stats = self.client.get_monitoring_stats()
                
                logger.info("="*60)
                logger.info("📈 MONITORING STATISTICS")
                logger.info("="*60)
                logger.info(f"Total Messages: {stats.total_messages:,}")
                logger.info(f"Messages/Minute: {stats.messages_per_minute:.1f}")
                logger.info(f"Unique Tokens: {stats.unique_tokens_seen}")
                logger.info(f"Unique Pools: {stats.unique_pools_seen}")
                logger.info(f"Connection Uptime: {stats.connection_uptime:.0f}s")
                logger.info(f"Error Count: {stats.error_count}")
                
                if stats.last_message_time:
                    logger.info(f"Last Message: {stats.last_message_time}")
                
                # Custom statistics
                logger.info(f"Interesting Pools Found: {len(self.interesting_pools)}")
                logger.info(f"Volume Spikes Detected: {len(self.volume_spikes)}")
                logger.info(f"Large Trades Seen: {len(self.large_trades)}")
                
                # Show recent interesting pools
                if self.interesting_pools:
                    logger.info("\n🔥 Recent High-Value Pools:")
                    for pool in self.interesting_pools[-5:]:  # Last 5
                        logger.info(
                            f"  {pool['symbol']}: ${pool['market_cap']:,.0f} market cap"
                        )
                
                logger.info("="*60)
                
            except Exception as e:
                logger.error(f"Error printing stats: {e}")
    
    async def run(self):
        """Run the advanced monitoring system."""
        try:
            logger.info("🚀 Starting Advanced GMGN Monitor")
            logger.info("="*60)
            logger.info("Features enabled:")
            logger.info(f"  • Token Filtering: {bool(self.token_filter.min_market_cap)}")
            logger.info(f"  • Data Export: {self.export_config.enabled}")
            logger.info(f"  • Alerts: {self.alert_config.enabled}")
            logger.info(f"  • Rate Limiting: {self.client.rate_limit} msg/s")
            logger.info("="*60)
            
            # Setup event handlers
            await self.setup_handlers()
            
            # Connect to WebSocket
            await self.client.connect()
            
            # Subscribe to all available channels
            await self.client.subscribe_all_channels()
            
            # Start periodic statistics
            stats_task = asyncio.create_task(self.print_periodic_stats())
            
            logger.info("✅ Connected and monitoring... Press Ctrl+C to stop")
            
            # Keep running until interrupted
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info("🛑 Shutdown signal received")
            
            # Cleanup
            stats_task.cancel()
            await self.client.disconnect()
            
            # Final statistics
            final_stats = self.client.get_monitoring_stats()
            logger.info(f"🏁 Final Stats: {final_stats.total_messages:,} messages processed")
            logger.info(f"� Discovered {len(self.interesting_pools)} interesting pools")
            
        except Exception as e:
            logger.error(f"❌ Error in monitoring: {e}")
            raise


async def main():
    """Main entry point."""
    monitor = AdvancedGmGnMonitor()
    await monitor.run()


if __name__ == "__main__":
    # Run the advanced monitoring system
    asyncio.run(main())
