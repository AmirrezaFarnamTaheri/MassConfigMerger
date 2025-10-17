from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session, sessionmaker
from typing import List, Optional
import hashlib
from datetime import datetime, timedelta

from .models import Base, Proxy, ProxyTestResult, Source

class ProxyRepository:
    """Repository for proxy operations"""

    def __init__(self, db_url: str = "sqlite:///configstream.db"):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def _get_config_hash(self, config: str) -> str:
        """Generate hash for config"""
        return hashlib.sha256(config.encode()).hexdigest()

    def save_proxy(self, proxy_data: dict) -> Proxy:
        """Save or update proxy"""
        session: Session = self.SessionLocal()
        try:
            config_hash = self._get_config_hash(proxy_data['config'])

            # Check if exists
            existing = session.query(Proxy).filter_by(
                config_hash=config_hash
            ).first()

            if existing:
                # Update
                for key, value in proxy_data.items():
                    setattr(existing, key, value)
                existing.last_seen = datetime.utcnow()
                proxy = existing
            else:
                # Create new
                proxy = Proxy(
                    config_hash=config_hash,
                    **proxy_data
                )
                session.add(proxy)

            session.commit()
            session.refresh(proxy)
            return proxy
        finally:
            session.close()

    def get_active_proxies(
        self,
        protocol: Optional[str] = None,
        country: Optional[str] = None,
        max_latency: Optional[float] = None,
        limit: Optional[int] = None,
    ) -> List[Proxy]:
        """Get active proxies with filters"""
        session: Session = self.SessionLocal()
        try:
            query = session.query(Proxy).filter_by(is_active=True)

            if protocol:
                query = query.filter_by(protocol=protocol)
            if country:
                query = query.filter_by(country=country)
            if max_latency:
                query = query.filter(Proxy.latency <= max_latency)

            query = query.order_by(Proxy.latency)

            if limit:
                query = query.limit(limit)

            return query.all()
        finally:
            session.close()

    def record_test_result(
        self,
        proxy_id: int,
        success: bool,
        latency: Optional[float] = None,
        error: Optional[str] = None,
    ) -> None:
        """Record test result"""
        session: Session = self.SessionLocal()
        try:
            # Create test result
            result = ProxyTestResult(
                proxy_id=proxy_id,
                success=success,
                latency=latency,
                error_message=error
            )
            session.add(result)

            # Update proxy stats
            proxy = session.query(Proxy).get(proxy_id)
            if proxy:
                if success:
                    proxy.success_count += 1
                    proxy.latency = latency
                else:
                    proxy.failure_count += 1

                proxy.last_test_time = datetime.utcnow()

                # Deactivate if too many failures
                total_tests = proxy.success_count + proxy.failure_count
                if total_tests >= 10:
                    success_rate = proxy.success_count / total_tests
                    if success_rate < 0.3:
                        proxy.is_active = False

            session.commit()
        finally:
            session.close()

    def cleanup_old_proxies(self, days: int = 7) -> int:
        """Remove proxies not seen in N days"""
        session: Session = self.SessionLocal()
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            deleted = session.query(Proxy).filter(
                Proxy.last_seen < cutoff
            ).delete()
            session.commit()
            return deleted
        finally:
            session.close()

    def get_statistics_summary(self) -> dict:
        """Get current statistics"""
        session: Session = self.SessionLocal()
        try:
            total = session.query(Proxy).filter_by(is_active=True).count()

            working = (
                session.query(Proxy)
                .filter(Proxy.is_active.is_(True), Proxy.latency.isnot(None))
                .count()
            )

            avg_latency = (
                session.query(func.avg(Proxy.latency))
                .filter(Proxy.is_active.is_(True))
                .scalar()
            )

            return {
                'total': total,
                'working': working,
                'failed': total - working,
                'avg_latency': avg_latency
            }
        finally:
            session.close()
