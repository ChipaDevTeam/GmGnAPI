"""
Pydantic models for GMGN API data structures.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, ConfigDict


class Message(BaseModel):
    """Base message structure received from GMGN WebSocket."""
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
            Decimal: str,
        }
    )
    
    channel: str
    data: Any
    action: Optional[str] = None
    id: Optional[str] = None
    timestamp: Optional[datetime] = None


class SubscriptionRequest(BaseModel):
    """WebSocket subscription request structure."""
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat(),
        }
    )
    
    action: str = "subscribe"
    channel: str
    f: str = "w"
    id: str = Field(default_factory=lambda: uuid4().hex[:16])
    data: List[Dict[str, Any]]
    access_token: Optional[str] = None
    retry: Optional[int] = None


class TokenInfo(BaseModel):
    """Basic token information from GMGN API."""
    
    s: Optional[str] = None  # symbol
    n: Optional[str] = None  # name
    l: Optional[str] = None  # logo URL
    ts: Optional[int] = None  # total supply
    v1m: Optional[float] = None  # volume 1 minute
    v5m: Optional[float] = None  # volume 5 minutes
    v1h: Optional[float] = None  # volume 1 hour
    v6h: Optional[float] = None  # volume 6 hours
    v24h: Optional[float] = None  # volume 24 hours
    s1m: Optional[int] = None  # swaps 1 minute
    s5m: Optional[int] = None  # swaps 5 minutes
    s1h: Optional[int] = None  # swaps 1 hour
    s6h: Optional[int] = None  # swaps 6 hours
    s24h: Optional[int] = None  # swaps 24 hours
    p: Optional[float] = None  # price
    hc: Optional[int] = None  # holder count
    pcp1m: Optional[str] = None  # price change percentage 1 minute
    pcp5m: Optional[str] = None  # price change percentage 5 minutes
    pcp1h: Optional[str] = None  # price change percentage 1 hour
    br: Optional[str] = None  # burn rate
    bs: Optional[str] = None  # burn status
    isa: Optional[bool] = None  # is active
    hl: Optional[int] = None  # holder limit
    lqdt: Optional[str] = None  # liquidity data
    t10hr: Optional[float] = None  # top 10 holder ratio
    rm: Optional[int] = None  # risk management
    rfa: Optional[int] = None  # risk factor A
    mc: Optional[int] = None  # market cap
    ctr: Optional[str] = None  # creator
    cbr: Optional[float] = None  # creator balance ratio
    cts: Optional[str] = None  # creator status
    rtar: Optional[float] = None  # risk target ratio
    bop: Optional[int] = None  # burn on purchase
    sdc: Optional[int] = None  # supply decrease count
    rc: Optional[int] = None  # risk count
    pg: Optional[float] = None  # price growth
    dx_ul: Optional[bool] = None  # DEX unlocked
    snp: Optional[int] = None  # snapshot
    f_pre: Optional[str] = None  # freeze pre
    f_t: Optional[str] = None  # freeze total
    cto: Optional[bool] = None  # creator token owned
    d_cic: Optional[int] = None  # daily creator in count
    d_coc: Optional[int] = None  # daily creator out count
    d_ccc: Optional[int] = None  # daily creator change count
    dx_tb: Optional[bool] = None  # DEX token burn
    dx_bf: Optional[int] = None  # DEX burn factor


class PoolData(BaseModel):
    """Individual pool data structure."""
    
    id: Optional[int] = None  # pool ID
    a: str  # pool address
    ex: str  # exchange
    pa: str  # pool address (duplicate)
    ba: str  # base token address
    qa: str  # quote token address
    qr: Optional[str] = None  # quote reserve
    il: Optional[int] = None  # initial liquidity
    iqr: Optional[str] = None  # initial quote reserve
    l: Optional[str] = None  # liquidity provider
    lpp: Optional[str] = None  # liquidity provider protocol
    ot: Optional[int] = None  # open time
    pts: Optional[str] = None  # pool type string
    pt: Optional[int] = None  # pool type
    qs: Optional[str] = None  # quote symbol
    bti: Optional[TokenInfo] = None  # base token info
    bf_: Optional[bool] = None  # some boolean flag


class NewPoolInfo(BaseModel):
    """New liquidity pool information."""
    
    c: str  # chain
    rg: Optional[str] = None  # region
    p: List[PoolData]  # pools
    
    @property
    def chain(self) -> str:
        return self.c
        
    @property
    def pools(self) -> List[PoolData]:
        return self.p


class PairUpdateData(BaseModel):
    """Trading pair update data."""
    
    pair_address: str
    token_address: str
    price_usd: Optional[Decimal] = None
    price_change_24h: Optional[float] = None
    volume_24h_usd: Optional[Decimal] = None
    liquidity_usd: Optional[Decimal] = None
    market_cap_usd: Optional[Decimal] = None
    chain: str
    updated_at: Optional[datetime] = None
    
    @field_validator('price_usd', 'volume_24h_usd', 'liquidity_usd', 'market_cap_usd', mode='before')
    @classmethod
    def parse_decimal_fields(cls, v):
        if v is None or v == "":
            return None
        return Decimal(str(v))


class TokenLaunchData(BaseModel):
    """Token launch information."""
    
    token_address: str
    name: str
    symbol: str
    decimals: int
    total_supply: Optional[Decimal] = None
    initial_price_usd: Optional[Decimal] = None
    market_cap_usd: Optional[Decimal] = None
    chain: str
    launched_at: Optional[datetime] = None
    creator_address: Optional[str] = None
    description: Optional[str] = None
    
    @field_validator('total_supply', 'initial_price_usd', 'market_cap_usd', mode='before')
    @classmethod
    def parse_decimal_fields(cls, v):
        if v is None or v == "":
            return None
        return Decimal(str(v))


class ChainStatistics(BaseModel):
    """Blockchain statistics."""
    
    chain: str
    total_pools: Optional[int] = None
    total_tokens: Optional[int] = None
    total_volume_24h_usd: Optional[Decimal] = None
    total_liquidity_usd: Optional[Decimal] = None
    new_pools_24h: Optional[int] = None
    new_tokens_24h: Optional[int] = None
    updated_at: Optional[datetime] = None
    
    @field_validator('total_volume_24h_usd', 'total_liquidity_usd', mode='before')
    @classmethod
    def parse_decimal_fields(cls, v):
        if v is None or v == "":
            return None
        return Decimal(str(v))


class TokenSocialInfo(BaseModel):
    """Token social media and community information."""
    
    token_address: str
    website: Optional[str] = None
    twitter: Optional[str] = None
    telegram: Optional[str] = None
    discord: Optional[str] = None
    github: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    chain: str
    updated_at: Optional[datetime] = None


class TradeData(BaseModel):
    """Individual trade information."""
    
    transaction_hash: str
    wallet_address: str
    token_address: str
    trade_type: Literal["buy", "sell"]
    amount_token: Decimal
    amount_usd: Decimal
    price_usd: Decimal
    timestamp: datetime
    
    @field_validator('amount_token', 'amount_usd', 'price_usd', mode='before')
    @classmethod
    def parse_decimal_fields(cls, v):
        return Decimal(str(v))


class WalletTradeData(BaseModel):
    """Wallet trading activity data."""
    
    wallet_address: str
    chain: str
    trades: List[TradeData]
    total_volume_24h_usd: Optional[Decimal] = None
    total_trades_24h: Optional[int] = None
    pnl_24h_usd: Optional[Decimal] = None
    updated_at: Optional[datetime] = None
    
    @field_validator('total_volume_24h_usd', 'pnl_24h_usd', mode='before')
    @classmethod
    def parse_decimal_fields(cls, v):
        if v is None or v == "":
            return None
        return Decimal(str(v))


class LimitOrderInfo(BaseModel):
    """Limit order information."""
    
    order_id: str
    wallet_address: str
    token_address: str
    order_type: Literal["buy", "sell"]
    amount_token: Decimal
    price_usd: Decimal
    status: Literal["active", "filled", "cancelled"]
    created_at: datetime
    expires_at: Optional[datetime] = None
    filled_amount: Optional[Decimal] = None
    chain: str
    
    @field_validator('amount_token', 'price_usd', 'filled_amount', mode='before')
    @classmethod
    def parse_decimal_fields(cls, v):
        if v is None or v == "":
            return None
        return Decimal(str(v))


# Filter and Configuration Models
class TokenFilter(BaseModel):
    """Filter configuration for tokens."""
    
    min_market_cap: Optional[Decimal] = None
    max_market_cap: Optional[Decimal] = None
    min_liquidity: Optional[Decimal] = None
    max_liquidity: Optional[Decimal] = None
    min_volume_24h: Optional[Decimal] = None
    max_volume_24h: Optional[Decimal] = None
    exchanges: Optional[List[str]] = None
    symbols: Optional[List[str]] = None
    exclude_symbols: Optional[List[str]] = None
    min_holder_count: Optional[int] = None
    max_risk_score: Optional[float] = None


class DataExportConfig(BaseModel):
    """Configuration for data export."""
    
    enabled: bool = False
    format: Literal["json", "csv", "parquet"] = "json"
    file_path: Optional[str] = None
    max_file_size_mb: int = 100
    rotation_interval_hours: int = 24
    compress: bool = False
    include_metadata: bool = True


class AlertConfig(BaseModel):
    """Configuration for alerts and notifications."""
    
    enabled: bool = False
    webhook_url: Optional[str] = None
    email: Optional[str] = None
    conditions: List[Dict[str, Any]] = Field(default_factory=list)
    rate_limit_seconds: int = 60


class MonitoringStats(BaseModel):
    """Real-time monitoring statistics."""
    
    total_messages: int = 0
    messages_per_minute: float = 0.0
    unique_tokens_seen: int = 0
    unique_pools_seen: int = 0
    total_volume_tracked: Decimal = Decimal("0")
    connection_uptime: float = 0.0
    last_message_time: Optional[datetime] = None
    error_count: int = 0
