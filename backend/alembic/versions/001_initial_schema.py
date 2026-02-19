"""Initial schema - 14 tables + indexes + pgvector.

Revision ID: 001
Revises: None
Create Date: 2026-02-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID, ARRAY

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # --- ENUM types ---
    user_role = sa.Enum("admin", "manager", "operator", "client", name="user_role")
    client_status = sa.Enum("active", "paused", "archived", name="client_status")
    platform = sa.Enum("instagram", "facebook", "youtube", name="platform")
    content_type = sa.Enum("feed", "reel", "story", "short", "card_news", name="content_type")
    content_status = sa.Enum("draft", "review", "client_review", "approved", "published", "rejected", name="content_status")
    sentiment = sa.Enum("positive", "neutral", "negative", "crisis", name="sentiment")
    comment_status = sa.Enum("pending", "replied", "hidden", "flagged", name="comment_status")
    role_in_client = sa.Enum("manager", "operator", "viewer", name="role_in_client")
    rule_type = sa.Enum("keyword", "pattern", "user_block", name="rule_type")
    filter_action = sa.Enum("hide", "flag", "delete", name="filter_action")
    notification_type = sa.Enum("approval_request", "publish_result", "crisis_alert", "comment", "system", name="notification_type")
    notification_priority = sa.Enum("low", "normal", "high", "critical", name="notification_priority")
    audit_action = sa.Enum("create", "update", "delete", "approve", "reject", "publish", "login", "logout", name="audit_action")
    publishing_status = sa.Enum("pending", "publishing", "success", "failed", "cancelled", name="publishing_status")
    faq_category = sa.Enum("faq", "tone_manner", "crisis_scenario", "template", name="faq_category")

    # --- 1. users ---
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- 2. clients ---
    op.create_table(
        "clients",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("brand_guidelines", JSONB, nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("manager_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", client_status, nullable=False, server_default=sa.text("'active'")),
        sa.Column("contract_start", sa.Date, nullable=True),
        sa.Column("contract_end", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- 3. user_client_assignments ---
    op.create_table(
        "user_client_assignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("role_in_client", role_in_client, nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "client_id", name="uq_user_client"),
    )

    # --- 4. platform_accounts ---
    op.create_table(
        "platform_accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("platform", platform, nullable=False),
        sa.Column("account_name", sa.String(200), nullable=False),
        sa.Column("access_token", sa.Text, nullable=False),
        sa.Column("refresh_token", sa.Text, nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_connected", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- 5. contents ---
    op.create_table(
        "contents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("content_type", content_type, nullable=False),
        sa.Column("status", content_status, nullable=False, server_default=sa.text("'draft'")),
        sa.Column("media_urls", JSONB, nullable=True),
        sa.Column("hashtags", ARRAY(sa.String), nullable=True),
        sa.Column("target_platforms", ARRAY(sa.String), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("ai_metadata", JSONB, nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- 6. comments_inbox ---
    op.create_table(
        "comments_inbox",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("platform_account_id", UUID(as_uuid=True), sa.ForeignKey("platform_accounts.id"), nullable=False),
        sa.Column("content_id", UUID(as_uuid=True), sa.ForeignKey("contents.id"), nullable=True),
        sa.Column("platform_comment_id", sa.String(200), nullable=False),
        sa.Column("parent_comment_id", UUID(as_uuid=True), sa.ForeignKey("comments_inbox.id"), nullable=True),
        sa.Column("author_name", sa.String(200), nullable=False),
        sa.Column("author_profile_url", sa.String(500), nullable=True),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("sentiment", sentiment, nullable=True),
        sa.Column("sentiment_score", sa.Float, nullable=True),
        sa.Column("status", comment_status, nullable=False, server_default=sa.text("'pending'")),
        sa.Column("ai_reply_draft", sa.Text, nullable=True),
        sa.Column("replied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replied_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("commented_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- 7. analytics_snapshots ---
    op.create_table(
        "analytics_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("platform_account_id", UUID(as_uuid=True), sa.ForeignKey("platform_accounts.id"), nullable=False),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("metrics", JSONB, nullable=False),
        sa.Column("content_id", UUID(as_uuid=True), sa.ForeignKey("contents.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("platform_account_id", "snapshot_date", "content_id", name="uq_analytics_snapshot"),
    )

    # --- 8. notifications ---
    op.create_table(
        "notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", notification_type, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column("reference_id", UUID(as_uuid=True), nullable=True),
        sa.Column("is_read", sa.Boolean, server_default=sa.text("false")),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("priority", notification_priority, server_default=sa.text("'normal'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- 9. audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", audit_action, nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("changes", JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- 10. content_approvals ---
    op.create_table(
        "content_approvals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("content_id", UUID(as_uuid=True), sa.ForeignKey("contents.id"), nullable=False),
        sa.Column("from_status", content_status, nullable=False),
        sa.Column("to_status", content_status, nullable=False),
        sa.Column("reviewer_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("is_urgent", sa.Boolean, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- 11. publishing_logs ---
    op.create_table(
        "publishing_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("content_id", UUID(as_uuid=True), sa.ForeignKey("contents.id"), nullable=False),
        sa.Column("platform_account_id", UUID(as_uuid=True), sa.ForeignKey("platform_accounts.id"), nullable=False),
        sa.Column("status", publishing_status, nullable=False),
        sa.Column("platform_post_id", sa.String(200), nullable=True),
        sa.Column("platform_post_url", sa.String(500), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("retry_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("celery_task_id", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- 12. faq_guidelines ---
    op.create_table(
        "faq_guidelines",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("category", faq_category, nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("tags", ARRAY(sa.String), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("priority", sa.Integer, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- 13. filter_rules ---
    op.create_table(
        "filter_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("rule_type", rule_type, nullable=False),
        sa.Column("value", sa.String(500), nullable=False),
        sa.Column("action", filter_action, nullable=False),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- 14. vector_embeddings ---
    op.create_table(
        "vector_embeddings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("source_id", UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("chunk_text", sa.Text, nullable=False),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # embedding vector column (pgvector)
    op.execute("ALTER TABLE vector_embeddings ADD COLUMN embedding vector(1536) NOT NULL")

    # --- 14 Indexes (from docs/01-database.md) ---
    op.create_index("idx_contents_client_status", "contents", ["client_id", "status"])
    op.create_index("idx_contents_scheduled", "contents", ["scheduled_at"], postgresql_where=sa.text("status = 'approved'"))
    op.create_index("idx_contents_calendar", "contents", ["client_id", "scheduled_at"])
    op.create_index("idx_comments_account_status", "comments_inbox", ["platform_account_id", "status"])
    op.create_index("idx_comments_sentiment_negative", "comments_inbox", ["sentiment"], postgresql_where=sa.text("sentiment = 'negative'"))
    op.create_index("idx_comments_sentiment_crisis", "comments_inbox", ["sentiment"], postgresql_where=sa.text("sentiment = 'crisis'"))
    op.create_index("idx_analytics_account_date", "analytics_snapshots", ["platform_account_id", "snapshot_date"])
    op.create_index("idx_notif_user_unread", "notifications", ["user_id", "is_read"], postgresql_where=sa.text("is_read = false"))
    op.create_index("idx_publog_content", "publishing_logs", ["content_id", "status"])
    op.create_index("idx_approval_content", "content_approvals", ["content_id", "created_at"])
    op.create_index("idx_audit_entity", "audit_logs", ["entity_type", "entity_id", "created_at"])
    op.create_index("idx_uca_user", "user_client_assignments", ["user_id"])
    op.create_index("idx_uca_client", "user_client_assignments", ["client_id"])
    op.create_index("idx_filter_client_active", "filter_rules", ["client_id"], postgresql_where=sa.text("is_active = true"))

    # pgvector IVFFlat index
    op.execute("CREATE INDEX idx_vector_ivfflat ON vector_embeddings USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100)")

    # updated_at auto-update trigger
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    for table in [
        "users", "clients", "platform_accounts", "contents", "comments_inbox",
        "analytics_snapshots", "notifications", "audit_logs", "content_approvals",
        "publishing_logs", "faq_guidelines", "filter_rules", "vector_embeddings",
    ]:
        op.execute(f"""
            CREATE TRIGGER trigger_update_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """)


def downgrade() -> None:
    tables = [
        "vector_embeddings", "filter_rules", "faq_guidelines", "publishing_logs",
        "content_approvals", "audit_logs", "notifications", "analytics_snapshots",
        "comments_inbox", "contents", "platform_accounts", "user_client_assignments",
        "clients", "users",
    ]
    for table in tables:
        op.execute(f"DROP TRIGGER IF EXISTS trigger_update_{table}_updated_at ON {table}")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")

    for table in tables:
        op.drop_table(table)

    enums = [
        "user_role", "client_status", "platform", "content_type", "content_status",
        "sentiment", "comment_status", "role_in_client", "rule_type", "filter_action",
        "notification_type", "notification_priority", "audit_action", "publishing_status",
        "faq_category",
    ]
    for enum in enums:
        op.execute(f"DROP TYPE IF EXISTS {enum}")

    op.execute("DROP EXTENSION IF EXISTS vector")
