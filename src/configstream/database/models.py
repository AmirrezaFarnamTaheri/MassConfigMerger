from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, JSON, ForeignKey, Text, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Proxy(Base):
    """Proxy model"""
    __tablename__ = 'proxies'

    id = Column(Integer, primary_key=True)
    config_hash = Column(String(64), unique=True, index=True)
    protocol = Column(String(50), index=True)
    config = Column(Text, nullable=False)

    # Location
    country = Column(String(100), index=True)
    country_code = Column(String(2), index=True)
    city = Column(String(100), index=True)
    asn_name = Column(String(200))
    asn_number = Column(Integer)

    # Performance
    latency = Column(Float)
    last_test_time = Column(DateTime)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)

    # Security
    is_secure = Column(Boolean, default=True)
    security_issues = Column(JSON)

    # Metadata
    source_url = Column(String(500))
    remarks = Column(String(200))
    discovered_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Relationships
    test_results = relationship("ProxyTestResult", back_populates="proxy")

    __table_args__ = (
        Index('idx_active_latency', 'is_active', 'latency'),
        Index('idx_country_protocol', 'country', 'protocol'),
    )

class ProxyTestResult(Base):
    """Individual test result"""
    __tablename__ = 'proxy_test_results'

    id = Column(Integer, primary_key=True)
    proxy_id = Column(Integer, ForeignKey('proxies.id'))

    tested_at = Column(DateTime, default=datetime.utcnow)
    success = Column(Boolean)
    latency = Column(Float)
    error_message = Column(Text)

    proxy = relationship("Proxy", back_populates="test_results")

class Source(Base):
    """Proxy source"""
    __tablename__ = 'sources'

    id = Column(Integer, primary_key=True)
    url = Column(String(500), unique=True)
    name = Column(String(200))
    is_active = Column(Boolean, default=True)

    # Statistics
    total_fetched = Column(Integer, default=0)
    total_working = Column(Integer, default=0)
    last_fetch_time = Column(DateTime)
    last_fetch_count = Column(Integer)

    # Health
    consecutive_failures = Column(Integer, default=0)
    success_rate = Column(Float)

class Statistics(Base):
    """Historical statistics"""
    __tablename__ = 'statistics'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    total_proxies = Column(Integer)
    working_proxies = Column(Integer)
    failed_proxies = Column(Integer)

    avg_latency = Column(Float)
    min_latency = Column(Float)
    max_latency = Column(Float)

    protocol_distribution = Column(JSON)
    country_distribution = Column(JSON)

    # Trends
    new_proxies_24h = Column(Integer)
    lost_proxies_24h = Column(Integer)
