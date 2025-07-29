"""
Filtering and alerting example for GMGN API.

This example demonstrates:
- Advanced token filtering configurations
- Real-time alerting system
- Market condition monitoring
- Custom alert conditions
"""

import asyncio
import logging
from decimal import Decimal
from datetime import datetime

from gmgnapi import (
    GmGnEnhancedClient,
    TokenFilter,
    AlertConfig,
    DataExportConfig,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SmartTokenFilter:
    """Advanced token filtering with market intelligence."""
    
    def __init__(self):
        self.alerts_sent = []
        self.market_conditions = {
            'total_pools_seen': 0,
            'high_value_pools': 0,
            'scam_indicators': 0,
            'volume_spikes': 0,
        }
    
    async def setup_conservative_filter(self):
        """Conservative filter for safer investments."""
        return TokenFilter(
            min_market_cap=Decimal("250000"),      # $250k minimum
            min_liquidity=Decimal("100000"),       # $100k minimum
            min_volume_24h=Decimal("50000"),       # $50k daily volume
            min_holder_count=100,                  # 100+ holders
            exchanges=["raydium", "orca"],         # Established DEXs
            exclude_symbols=[                      # Scam indicators
                "SCAM", "TEST", "FAKE", "MEME", "PUMP", "DUMP",
                "MOON", "LAMBO", "ROCKET", "DOGE", "PEPE",
                "SHIB", "FLOKI", "SAFE", "BABY", "MINI"
            ],
            max_risk_score=0.2,  # Very conservative
        )
    
    async def setup_aggressive_filter(self):
        """Aggressive filter for early opportunities."""
        return TokenFilter(
            min_market_cap=Decimal("10000"),       # $10k minimum
            min_liquidity=Decimal("5000"),         # $5k minimum
            min_volume_24h=Decimal("1000"),        # $1k daily volume
            min_holder_count=5,                    # 5+ holders
            exchanges=["raydium", "orca", "jupiter"], # All major DEXs
            exclude_symbols=["SCAM", "TEST", "FAKE"], # Basic scam filter
            max_risk_score=0.8,  # Higher risk tolerance
        )
    
    async def setup_whale_filter(self):
        """Filter for whale-sized opportunities."""
        return TokenFilter(
            min_market_cap=Decimal("1000000"),     # $1M minimum
            min_liquidity=Decimal("500000"),       # $500k minimum
            min_volume_24h=Decimal("200000"),      # $200k daily volume
            min_holder_count=500,                  # 500+ holders
            exchanges=["raydium"],                 # Raydium only
            max_risk_score=0.1,  # Ultra conservative
        )


class AlertSystem:
    """Advanced alerting system for market events."""
    
    def __init__(self):
        self.alert_history = []
        self.last_alert_times = {}
        
    def should_send_alert(self, alert_type: str, cooldown_minutes: int = 5) -> bool:
        """Check if alert should be sent based on cooldown."""
        now = datetime.now()
        last_time = self.last_alert_times.get(alert_type)
        
        if not last_time:
            self.last_alert_times[alert_type] = now
            return True
        
        time_diff = (now - last_time).total_seconds() / 60
        if time_diff >= cooldown_minutes:
            self.last_alert_times[alert_type] = now
            return True
        
        return False
    
    async def send_alert(self, alert_type: str, message: str, data: dict = None):
        """Send alert if conditions are met."""
        if not self.should_send_alert(alert_type):
            return
        
        alert = {
            'type': alert_type,
            'message': message,
            'timestamp': datetime.now(),
            'data': data or {}
        }
        
        self.alert_history.append(alert)
        
        # Log alert (in production, send to webhook/email/SMS)
        logger.warning(f"🚨 ALERT [{alert_type.upper()}]: {message}")
        
        # In production, you would send to external services:
        # await self.send_to_slack(message)
        # await self.send_to_discord(message)
        # await self.send_email(message)
    
    async def check_new_pool_alerts(self, pool_info):
        """Check new pool for alert conditions."""
        if not pool_info.pools:
            return
        
        pool = pool_info.pools[0]
        token_info = pool.bti
        
        if not token_info:
            return
        
        symbol = getattr(token_info, 's', 'Unknown')
        market_cap = getattr(token_info, 'mc', 0)
        liquidity = getattr(pool, 'il', 0)
        
        # High-value pool alert
        if market_cap and market_cap > 500000:  # $500k+
            await self.send_alert(
                'high_value_pool',
                f"🔥 High-value pool detected: {symbol} with ${market_cap:,.0f} market cap",
                {'symbol': symbol, 'market_cap': market_cap, 'pool_address': pool.a}
            )
        
        # High liquidity alert
        if liquidity and liquidity > 200000:  # $200k+
            await self.send_alert(
                'high_liquidity',
                f"💧 High liquidity pool: {symbol} with ${liquidity:,.0f} liquidity",
                {'symbol': symbol, 'liquidity': liquidity, 'pool_address': pool.a}
            )
        
        # Potential scam alert
        scam_indicators = ['SCAM', 'FAKE', 'TEST', 'PUMP', 'DUMP']
        if any(indicator in symbol.upper() for indicator in scam_indicators):
            await self.send_alert(
                'potential_scam',
                f"⚠️  Potential scam detected: {symbol}",
                {'symbol': symbol, 'pool_address': pool.a}
            )
    
    async def check_volume_alerts(self, pair_data):
        """Check for volume spike alerts."""
        if not hasattr(pair_data, 'volume_24h_usd') or not pair_data.volume_24h_usd:
            return
        
        volume = pair_data.volume_24h_usd
        
        # Volume spike alert
        if volume > Decimal("1000000"):  # $1M+ volume
            await self.send_alert(
                'volume_spike',
                f"📈 Volume spike detected: ${volume:,.0f} in 24h",
                {'pair_address': pair_data.pair_address, 'volume': float(volume)},
                cooldown_minutes=15  # Longer cooldown for volume alerts
            )


async def conservative_monitoring_example():
    """Example of conservative token monitoring."""
    logger.info("🛡️  Starting Conservative Monitoring")
    
    filter_system = SmartTokenFilter()
    alert_system = AlertSystem()
    
    # Setup conservative filtering
    token_filter = await filter_system.setup_conservative_filter()
    
    # Configure minimal alerts
    alert_config = AlertConfig(
        enabled=True,
        rate_limit_seconds=300,  # 5-minute cooldown
    )
    
    client = GmGnEnhancedClient(
        token_filter=token_filter,
        alert_config=alert_config,
    )
    
    async def on_new_pool(pool_info):
        filter_system.market_conditions['total_pools_seen'] += 1
        await alert_system.check_new_pool_alerts(pool_info)
        
        if pool_info.pools:
            pool = pool_info.pools[0]
            token_info = pool.bti
            if token_info:
                symbol = getattr(token_info, 's', 'Unknown')
                market_cap = getattr(token_info, 'mc', 0)
                
                logger.info(f"✅ Conservative filter passed: {symbol} (${market_cap:,.0f})")
                filter_system.market_conditions['high_value_pools'] += 1
    
    client.on_new_pool(on_new_pool)
    
    await client.connect()
    await client.subscribe_new_pools()
    
    # Monitor for 5 minutes
    logger.info("⏱️  Conservative monitoring for 5 minutes...")
    await asyncio.sleep(300)
    
    await client.disconnect()
    
    # Report results
    logger.info("📊 Conservative Monitoring Results:")
    logger.info(f"   Total pools seen: {filter_system.market_conditions['total_pools_seen']}")
    logger.info(f"   High-value pools: {filter_system.market_conditions['high_value_pools']}")
    logger.info(f"   Alerts sent: {len(alert_system.alert_history)}")


async def aggressive_monitoring_example():
    """Example of aggressive token monitoring for early opportunities."""
    logger.info("⚡ Starting Aggressive Monitoring")
    
    filter_system = SmartTokenFilter()
    alert_system = AlertSystem()
    
    # Setup aggressive filtering
    token_filter = await filter_system.setup_aggressive_filter()
    
    client = GmGnEnhancedClient(token_filter=token_filter)
    
    opportunities = []
    
    async def on_new_pool(pool_info):
        filter_system.market_conditions['total_pools_seen'] += 1
        await alert_system.check_new_pool_alerts(pool_info)
        
        if pool_info.pools:
            pool = pool_info.pools[0]
            token_info = pool.bti
            if token_info:
                symbol = getattr(token_info, 's', 'Unknown')
                market_cap = getattr(token_info, 'mc', 0)
                
                opportunities.append({
                    'symbol': symbol,
                    'market_cap': market_cap,
                    'pool_address': pool.a,
                    'timestamp': datetime.now(),
                })
                
                logger.info(f"⚡ Early opportunity: {symbol} (${market_cap:,.0f})")
    
    client.on_new_pool(on_new_pool)
    
    await client.connect()
    await client.subscribe_new_pools()
    
    # Monitor for 3 minutes
    logger.info("⏱️  Aggressive monitoring for 3 minutes...")
    await asyncio.sleep(180)
    
    await client.disconnect()
    
    # Report results
    logger.info("📊 Aggressive Monitoring Results:")
    logger.info(f"   Total opportunities: {len(opportunities)}")
    if opportunities:
        logger.info("🎯 Top opportunities:")
        sorted_opps = sorted(opportunities, key=lambda x: x['market_cap'], reverse=True)
        for opp in sorted_opps[:5]:
            logger.info(f"   {opp['symbol']}: ${opp['market_cap']:,.0f}")


async def whale_watching_example():
    """Example of whale-watching with ultra-conservative filters."""
    logger.info("🐋 Starting Whale Watching")
    
    filter_system = SmartTokenFilter()
    alert_system = AlertSystem()
    
    # Setup whale filter
    token_filter = await filter_system.setup_whale_filter()
    
    client = GmGnEnhancedClient(token_filter=token_filter)
    
    whales = []
    
    async def on_new_pool(pool_info):
        await alert_system.check_new_pool_alerts(pool_info)
        
        if pool_info.pools:
            pool = pool_info.pools[0]
            token_info = pool.bti
            if token_info:
                symbol = getattr(token_info, 's', 'Unknown')
                market_cap = getattr(token_info, 'mc', 0)
                
                whales.append({
                    'symbol': symbol,
                    'market_cap': market_cap,
                    'pool_address': pool.a,
                })
                
                logger.warning(f"🐋 WHALE DETECTED: {symbol} with ${market_cap:,.0f} market cap!")
    
    async def on_pair_update(pair_data):
        await alert_system.check_volume_alerts(pair_data)
    
    client.on_new_pool(on_new_pool)
    client.on_pair_update(on_pair_update)
    
    await client.connect()
    await client.subscribe_new_pools()
    await client.subscribe_pair_updates()
    
    # Monitor for 8 minutes (whales are rare)
    logger.info("⏱️  Whale watching for 8 minutes...")
    await asyncio.sleep(480)
    
    await client.disconnect()
    
    # Report results
    logger.info("📊 Whale Watching Results:")
    logger.info(f"   Whales detected: {len(whales)}")
    logger.info(f"   Alerts sent: {len(alert_system.alert_history)}")
    
    if whales:
        logger.info("🐋 Whales found:")
        for whale in whales:
            logger.info(f"   {whale['symbol']}: ${whale['market_cap']:,.0f}")


async def main():
    """Run all filtering and alerting examples."""
    logger.info("🚀 Starting Filtering and Alerting Examples")
    logger.info("="*60)
    
    try:
        # Run examples sequentially
        await conservative_monitoring_example()
        await asyncio.sleep(2)
        
        await aggressive_monitoring_example()
        await asyncio.sleep(2)
        
        await whale_watching_example()
        
        logger.info("="*60)
        logger.info("✅ All filtering and alerting examples completed!")
        
    except Exception as e:
        logger.error(f"❌ Error in filtering examples: {e}")
        raise


if __name__ == "__main__":
    # Run the filtering and alerting examples
    asyncio.run(main())
