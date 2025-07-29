"""
Pydantic models for GMGN API data structures.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, Field, validator


class Message(BaseModel):
    """Base message structure received from GMGN WebSocket."""
    
    action: str
    channel: str
    id: str
    data: Any
    timestamp: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: str,
        }


class SubscriptionRequest(BaseModel):
    """WebSocket subscription request structure."""
    
    action: str = "subscribe"
    channel: str
    f: str = "w"
    id: str = Field(default_factory=lambda: uuid4().hex[:16])
    data: List[Dict[str, Any]]
    access_token: Optional[str] = None
    retry: Optional[int] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class TokenInfo(BaseModel):
    """Basic token information."""
    
    address: str
    name: Optional[str] = None
    symbol: Optional[str] = None
    decimals: Optional[int] = None
    logo_url: Optional[str] = None


class NewPoolInfo(BaseModel):
    """New liquidity pool information."""
    
    pool_address: str
    token_address: str
    base_token_address: str
    quote_token_address: str
    initial_liquidity_usd: Optional[Decimal] = None
    initial_price: Optional[Decimal] = None
    chain: str
    dex: Optional[str] = None
    created_at: Optional[datetime] = None
    token_info: Optional[TokenInfo] = None
    
    @validator('initial_liquidity_usd', 'initial_price', pre=True)
    def parse_decimal_fields(cls, v):
        if v is None or v == "":
            return None
        return Decimal(str(v))


class PairUpdate(BaseModel):
    """Trading pair update information."""
    
    pair_address: str
    token_address: str
    price_usd: Optional[Decimal] = None
    price_change_24h: Optional[float] = None
    volume_24h_usd: Optional[Decimal] = None
    liquidity_usd: Optional[Decimal] = None
    market_cap_usd: Optional[Decimal] = None
    chain: str
    updated_at: Optional[datetime] = None
    
    @validator('price_usd', 'volume_24h_usd', 'liquidity_usd', 'market_cap_usd', pre=True)
    def parse_decimal_fields(cls, v):
        if v is None or v == "":
            return None
        return Decimal(str(v))


class TokenLaunchInfo(BaseModel):
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
    
    @validator('total_supply', 'initial_price_usd', 'market_cap_usd', pre=True)
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
    
    @validator('total_volume_24h_usd', 'total_liquidity_usd', pre=True)
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


class TradeInfo(BaseModel):
    """Individual trade information."""
    
    transaction_hash: str
    wallet_address: str
    token_address: str
    trade_type: str  # "buy" or "sell"
    amount_token: Decimal
    amount_usd: Decimal
    price_usd: Decimal
    timestamp: datetime
    
    @validator('amount_token', 'amount_usd', 'price_usd', pre=True)
    def parse_decimal_fields(cls, v):
        return Decimal(str(v))


class WalletTradeData(BaseModel):
    """Wallet trading activity data."""
    
    wallet_address: str
    chain: str
    trades: List[TradeInfo]
    total_volume_24h_usd: Optional[Decimal] = None
    total_trades_24h: Optional[int] = None
    pnl_24h_usd: Optional[Decimal] = None
    updated_at: Optional[datetime] = None
    
    @validator('total_volume_24h_usd', 'pnl_24h_usd', pre=True)
    def parse_decimal_fields(cls, v):
        if v is None or v == "":
            return None
        return Decimal(str(v))


class LimitOrderInfo(BaseModel):
    """Limit order information."""
    
    order_id: str
    wallet_address: str
    token_address: str
    order_type: str  # "buy" or "sell"
    amount_token: Decimal
    price_usd: Decimal
    status: str  # "active", "filled", "cancelled"
    created_at: datetime
    expires_at: Optional[datetime] = None
    filled_amount: Optional[Decimal] = None
    chain: str
    
    @validator('amount_token', 'price_usd', 'filled_amount', pre=True)
    def parse_decimal_fields(cls, v):
        if v is None or v == "":
            return None
        return Decimal(str(v))
