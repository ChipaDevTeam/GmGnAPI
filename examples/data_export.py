"""
Data export example for GMGN API.

This example demonstrates:
- Real-time data export to files
- CSV, JSON, and Database export formats
- Data filtering before export
- File rotation and compression
"""

import asyncio
import logging
from decimal import Decimal
from pathlib import Path

from gmgnapi import (
    GmGnEnhancedClient,
    TokenFilter,
    DataExportConfig,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def json_export_example():
    """Example of exporting data to JSON files."""
    logger.info("🗂️  Starting JSON Export Example")
    
    # Configure JSON export
    export_config = DataExportConfig(
        enabled=True,
        format="json",
        file_path="./exports/json_data",
        max_file_size_mb=10,
        rotation_interval_hours=1,
        compress=False,
        include_metadata=True,
    )
    
    # Filter for high-value tokens only
    token_filter = TokenFilter(
        min_market_cap=Decimal("25000"),
        min_liquidity=Decimal("5000"),
        min_holder_count=5,
    )
    
    client = GmGnEnhancedClient(
        export_config=export_config,
        token_filter=token_filter,
    )
    
    async def on_new_pool(pool_info):
        logger.info(f"📝 Exported new pool data to JSON")
    
    client.on_new_pool(on_new_pool)
    
    await client.connect()
    await client.subscribe_new_pools()
    
    # Run for 5 minutes
    logger.info("⏱️  Collecting data for 5 minutes...")
    await asyncio.sleep(300)
    
    await client.disconnect()
    
    # Check exported files
    export_path = Path("./exports/json_data")
    if export_path.exists():
        files = list(export_path.glob("*.json"))
        logger.info(f"✅ Created {len(files)} JSON export files")
        for file in files:
            size_kb = file.stat().st_size / 1024
            logger.info(f"   📄 {file.name}: {size_kb:.1f} KB")


async def csv_export_example():
    """Example of exporting data to CSV files."""
    logger.info("📊 Starting CSV Export Example")
    
    # Configure CSV export
    export_config = DataExportConfig(
        enabled=True,
        format="csv",
        file_path="./exports/csv_data",
        max_file_size_mb=5,
        rotation_interval_hours=2,
        compress=True,  # Enable compression for CSV
        include_metadata=True,
    )
    
    # Filter for active tokens with trading volume
    token_filter = TokenFilter(
        min_volume_24h=Decimal("1000"),
        exchanges=["raydium", "orca"],
        exclude_symbols=["TEST", "FAKE"],
    )
    
    client = GmGnEnhancedClient(
        export_config=export_config,
        token_filter=token_filter,
    )
    
    async def on_pair_update(pair_data):
        logger.info(f"📈 Exported pair update to CSV")
    
    client.on_pair_update(on_pair_update)
    
    await client.connect()
    await client.subscribe_pair_updates()
    
    # Run for 3 minutes
    logger.info("⏱️  Collecting data for 3 minutes...")
    await asyncio.sleep(180)
    
    await client.disconnect()
    
    # Check exported files
    export_path = Path("./exports/csv_data")
    if export_path.exists():
        files = list(export_path.glob("*.csv*"))  # Include compressed files
        logger.info(f"✅ Created {len(files)} CSV export files")
        for file in files:
            size_kb = file.stat().st_size / 1024
            logger.info(f"   📊 {file.name}: {size_kb:.1f} KB")


async def database_export_example():
    """Example of exporting data to SQLite database."""
    logger.info("🗄️  Starting Database Export Example")
    
    # Configure database export
    export_config = DataExportConfig(
        enabled=True,
        format="database",
        file_path="./exports/db_data",
        include_metadata=True,
    )
    
    # No filtering - capture everything for analysis
    client = GmGnEnhancedClient(export_config=export_config)
    
    async def on_message(message):
        # Log every 50th message to avoid spam
        if hasattr(on_message, 'count'):
            on_message.count += 1
        else:
            on_message.count = 1
        
        if on_message.count % 50 == 0:
            logger.info(f"💾 Exported {on_message.count} messages to database")
    
    client.on_message(on_message)
    
    await client.connect()
    await client.subscribe_all_channels()
    
    # Run for 2 minutes
    logger.info("⏱️  Collecting data for 2 minutes...")
    await asyncio.sleep(120)
    
    await client.disconnect()
    
    # Check database file
    db_path = Path("./exports/db_data/gmgn_data.db")
    if db_path.exists():
        size_kb = db_path.stat().st_size / 1024
        logger.info(f"✅ Created database: {size_kb:.1f} KB")
        
        # Simple query to show data
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM messages")
        count = cursor.fetchone()[0]
        logger.info(f"   📊 Total messages in database: {count:,}")
        
        cursor.execute("SELECT channel, COUNT(*) FROM messages GROUP BY channel")
        channel_counts = cursor.fetchall()
        for channel, count in channel_counts:
            logger.info(f"   📡 {channel}: {count:,} messages")
        
        conn.close()


async def filtered_export_example():
    """Example of advanced filtering before export."""
    logger.info("🔍 Starting Filtered Export Example")
    
    # Configure export with strict filtering
    export_config = DataExportConfig(
        enabled=True,
        format="json",
        file_path="./exports/filtered_data",
        include_metadata=True,
    )
    
    # Very strict filtering for high-quality tokens only
    token_filter = TokenFilter(
        min_market_cap=Decimal("100000"),  # $100k minimum
        min_liquidity=Decimal("50000"),    # $50k minimum
        min_volume_24h=Decimal("10000"),   # $10k minimum
        min_holder_count=50,               # 50+ holders
        exchanges=["raydium"],             # Only Raydium
        exclude_symbols=[                  # Exclude potential scams
            "SCAM", "TEST", "FAKE", "MEME", 
            "SHIT", "TRASH", "PUMP", "DUMP"
        ],
        max_risk_score=0.3,  # Very low risk only
    )
    
    client = GmGnEnhancedClient(
        export_config=export_config,
        token_filter=token_filter,
    )
    
    high_quality_pools = []
    
    async def on_new_pool(pool_info):
        """Only high-quality pools pass the filter."""
        if pool_info.pools:
            pool = pool_info.pools[0]
            token_info = pool.bti
            
            if token_info:
                symbol = getattr(token_info, 's', 'Unknown')
                market_cap = getattr(token_info, 'mc', 0)
                
                high_quality_pools.append({
                    'symbol': symbol,
                    'market_cap': market_cap,
                    'pool_address': pool.a,
                })
                
                logger.warning(
                    f"⭐ HIGH QUALITY: {symbol} with ${market_cap:,.0f} market cap"
                )
    
    client.on_new_pool(on_new_pool)
    
    await client.connect()
    await client.subscribe_new_pools()
    
    # Run for 10 minutes to find quality tokens
    logger.info("⏱️  Searching for high-quality tokens for 10 minutes...")
    await asyncio.sleep(600)
    
    await client.disconnect()
    
    # Report results
    logger.info(f"✅ Found {len(high_quality_pools)} high-quality pools")
    if high_quality_pools:
        logger.info("🏆 Top quality pools found:")
        for pool in high_quality_pools[:5]:  # Show top 5
            logger.info(f"   {pool['symbol']}: ${pool['market_cap']:,.0f}")


async def main():
    """Run all export examples."""
    logger.info("🚀 Starting Data Export Examples")
    logger.info("="*60)
    
    try:
        # Create export directories
        Path("./exports").mkdir(exist_ok=True)
        
        # Run examples sequentially
        await json_export_example()
        await asyncio.sleep(2)
        
        await csv_export_example()
        await asyncio.sleep(2)
        
        await database_export_example()
        await asyncio.sleep(2)
        
        await filtered_export_example()
        
        logger.info("="*60)
        logger.info("✅ All export examples completed successfully!")
        
        # Summary of exports
        export_path = Path("./exports")
        if export_path.exists():
            total_files = len(list(export_path.rglob("*")))
            logger.info(f"📁 Total export files created: {total_files}")
            
            # Calculate total size
            total_size = sum(
                f.stat().st_size for f in export_path.rglob("*") if f.is_file()
            )
            total_size_kb = total_size / 1024
            logger.info(f"💾 Total export size: {total_size_kb:.1f} KB")
        
    except Exception as e:
        logger.error(f"❌ Error in export examples: {e}")
        raise


if __name__ == "__main__":
    # Run the data export examples
    asyncio.run(main())
