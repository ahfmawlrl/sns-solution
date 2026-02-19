"""ORM model definition tests."""
from app.models import (
    Base,
    User, UserRole,
    Client, ClientStatus,
    UserClientAssignment, RoleInClient,
    PlatformAccount, Platform,
    Content, ContentType, ContentStatus,
    CommentInbox, Sentiment, CommentStatus,
    AnalyticsSnapshot,
    Notification, NotificationType, NotificationPriority,
    AuditLog, AuditAction,
    ContentApproval,
    PublishingLog, PublishingStatus,
    FaqGuideline, FaqCategory,
    FilterRule, RuleType, FilterAction,
    VectorEmbedding,
)


def test_all_14_tables_registered():
    table_names = set(Base.metadata.tables.keys())
    expected = {
        "users", "clients", "user_client_assignments", "platform_accounts",
        "contents", "comments_inbox", "analytics_snapshots",
        "notifications", "audit_logs", "content_approvals",
        "publishing_logs", "faq_guidelines", "filter_rules", "vector_embeddings",
    }
    assert expected == table_names


def test_user_role_enum():
    assert UserRole.ADMIN.value == "admin"
    assert UserRole.MANAGER.value == "manager"
    assert UserRole.OPERATOR.value == "operator"
    assert UserRole.CLIENT.value == "client"


def test_content_status_enum():
    assert ContentStatus.DRAFT.value == "draft"
    assert ContentStatus.REVIEW.value == "review"
    assert ContentStatus.CLIENT_REVIEW.value == "client_review"
    assert ContentStatus.APPROVED.value == "approved"
    assert ContentStatus.PUBLISHED.value == "published"
    assert ContentStatus.REJECTED.value == "rejected"


def test_sentiment_enum():
    assert Sentiment.POSITIVE.value == "positive"
    assert Sentiment.CRISIS.value == "crisis"


def test_platform_enum():
    assert Platform.INSTAGRAM.value == "instagram"
    assert Platform.FACEBOOK.value == "facebook"
    assert Platform.YOUTUBE.value == "youtube"


def test_publishing_status_enum():
    assert PublishingStatus.PENDING.value == "pending"
    assert PublishingStatus.SUCCESS.value == "success"
    assert PublishingStatus.FAILED.value == "failed"


def test_faq_category_enum():
    assert FaqCategory.FAQ.value == "faq"
    assert FaqCategory.TONE_MANNER.value == "tone_manner"
    assert FaqCategory.CRISIS_SCENARIO.value == "crisis_scenario"
    assert FaqCategory.TEMPLATE.value == "template"


def test_audit_action_enum():
    assert AuditAction.CREATE.value == "create"
    assert AuditAction.PUBLISH.value == "publish"
    assert AuditAction.LOGIN.value == "login"


def test_notification_type_enum():
    assert NotificationType.CRISIS_ALERT.value == "crisis_alert"
    assert NotificationType.APPROVAL_REQUEST.value == "approval_request"


def test_filter_action_enum():
    assert FilterAction.HIDE.value == "hide"
    assert FilterAction.FLAG.value == "flag"
    assert FilterAction.DELETE.value == "delete"


def test_table_columns_users():
    cols = {c.name for c in Base.metadata.tables["users"].columns}
    expected = {"id", "email", "password_hash", "name", "role", "is_active", "avatar_url", "last_login_at", "created_at", "updated_at"}
    assert expected == cols


def test_table_columns_contents():
    cols = {c.name for c in Base.metadata.tables["contents"].columns}
    expected = {
        "id", "client_id", "title", "body", "content_type", "status",
        "media_urls", "hashtags", "target_platforms", "scheduled_at",
        "published_at", "approved_at", "approved_by", "ai_metadata",
        "created_by", "created_at", "updated_at",
    }
    assert expected == cols


def test_table_columns_comments_inbox():
    cols = {c.name for c in Base.metadata.tables["comments_inbox"].columns}
    expected = {
        "id", "platform_account_id", "content_id", "platform_comment_id",
        "parent_comment_id", "author_name", "author_profile_url", "message",
        "sentiment", "sentiment_score", "status", "ai_reply_draft",
        "replied_at", "replied_by", "commented_at", "created_at", "updated_at",
    }
    assert expected == cols
