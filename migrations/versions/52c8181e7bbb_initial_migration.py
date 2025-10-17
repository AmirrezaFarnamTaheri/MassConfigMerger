"""Initial database migration."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "52c8181e7bbb"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "proxies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("config_hash", sa.String(length=64), nullable=True),
        sa.Column("protocol", sa.String(length=50), nullable=True),
        sa.Column("config", sa.Text(), nullable=False),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("country_code", sa.String(length=2), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("asn_name", sa.String(length=200), nullable=True),
        sa.Column("asn_number", sa.Integer(), nullable=True),
        sa.Column("latency", sa.Float(), nullable=True),
        sa.Column("last_test_time", sa.DateTime(), nullable=True),
        sa.Column("success_count", sa.Integer(), nullable=True),
        sa.Column("failure_count", sa.Integer(), nullable=True),
        sa.Column("is_secure", sa.Boolean(), nullable=True),
        sa.Column("security_issues", sa.JSON(), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("remarks", sa.String(length=200), nullable=True),
        sa.Column("discovered_at", sa.DateTime(), nullable=True),
        sa.Column("last_seen", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_active_latency", "proxies", ["is_active", "latency"], unique=False)
    op.create_index("idx_country_protocol", "proxies", ["country", "protocol"], unique=False)
    op.create_index(op.f("ix_proxies_city"), "proxies", ["city"], unique=False)
    op.create_index(op.f("ix_proxies_config_hash"), "proxies", ["config_hash"], unique=True)
    op.create_index(op.f("ix_proxies_country"), "proxies", ["country"], unique=False)
    op.create_index(op.f("ix_proxies_country_code"), "proxies", ["country_code"], unique=False)
    op.create_index(op.f("ix_proxies_protocol"), "proxies", ["protocol"], unique=False)

    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("total_fetched", sa.Integer(), nullable=True),
        sa.Column("total_working", sa.Integer(), nullable=True),
        sa.Column("last_fetch_time", sa.DateTime(), nullable=True),
        sa.Column("last_fetch_count", sa.Integer(), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=True),
        sa.Column("success_rate", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )

    op.create_table(
        "statistics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=True),
        sa.Column("total_proxies", sa.Integer(), nullable=True),
        sa.Column("working_proxies", sa.Integer(), nullable=True),
        sa.Column("failed_proxies", sa.Integer(), nullable=True),
        sa.Column("avg_latency", sa.Float(), nullable=True),
        sa.Column("min_latency", sa.Float(), nullable=True),
        sa.Column("max_latency", sa.Float(), nullable=True),
        sa.Column("protocol_distribution", sa.JSON(), nullable=True),
        sa.Column("country_distribution", sa.JSON(), nullable=True),
        sa.Column("new_proxies_24h", sa.Integer(), nullable=True),
        sa.Column("lost_proxies_24h", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_statistics_timestamp"), "statistics", ["timestamp"], unique=False)

    op.create_table(
        "proxy_test_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("proxy_id", sa.Integer(), nullable=True),
        sa.Column("tested_at", sa.DateTime(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=True),
        sa.Column("latency", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["proxy_id"], ["proxies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_table("proxy_test_results")
    op.drop_index(op.f("ix_statistics_timestamp"), table_name="statistics")
    op.drop_table("statistics")
    op.drop_table("sources")
    op.drop_index(op.f("ix_proxies_protocol"), table_name="proxies")
    op.drop_index(op.f("ix_proxies_country_code"), table_name="proxies")
    op.drop_index(op.f("ix_proxies_country"), table_name="proxies")
    op.drop_index(op.f("ix_proxies_config_hash"), table_name="proxies")
    op.drop_index(op.f("ix_proxies_city"), table_name="proxies")
    op.drop_index("idx_country_protocol", table_name="proxies")
    op.drop_index("idx_active_latency", table_name="proxies")
    op.drop_table("proxies")
