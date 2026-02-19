/* ============================
   SNS Solution - TypeScript Types
   ============================ */

// --- Enums ---

export type UserRole = 'admin' | 'manager' | 'operator' | 'client';
export type ClientStatus = 'active' | 'paused' | 'archived';
export type ContentType = 'feed' | 'reel' | 'story' | 'short' | 'card_news';
export type ContentStatus = 'draft' | 'review' | 'client_review' | 'approved' | 'published' | 'rejected';
export type Platform = 'instagram' | 'facebook' | 'youtube';
export type Sentiment = 'positive' | 'neutral' | 'negative' | 'crisis';
export type CommentStatus = 'pending' | 'replied' | 'hidden' | 'flagged';
export type PublishingStatus = 'pending' | 'publishing' | 'success' | 'failed' | 'cancelled';
export type NotificationType = 'approval_request' | 'publish_result' | 'crisis_alert' | 'comment' | 'system';
export type NotificationPriority = 'low' | 'normal' | 'high' | 'critical';
export type FaqCategory = 'faq' | 'tone_manner' | 'crisis_scenario' | 'template';
export type RuleType = 'keyword' | 'pattern' | 'user_block';
export type FilterAction = 'hide' | 'flag' | 'delete';

// --- Common ---

export interface APIResponse<T = unknown> {
  status: 'success' | 'error';
  data: T;
  message?: string;
  pagination?: PaginationMeta;
}

export interface PaginationMeta {
  total: number;
  page?: number;
  per_page?: number;
  cursor?: string;
  has_next: boolean;
}

export interface ErrorDetail {
  type: string;
  title: string;
  status: number;
  detail: string;
}

// --- Auth ---

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserInfo {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  avatar_url?: string;
}

// --- User ---

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  is_active: boolean;
  avatar_url?: string;
  last_login_at?: string;
  created_at: string;
  updated_at: string;
}

export interface UserCreate {
  email: string;
  password: string;
  name: string;
  role: UserRole;
  client_ids?: string[];
}

// --- Client ---

export interface Client {
  id: string;
  name: string;
  industry?: string;
  brand_guidelines?: Record<string, unknown>;
  logo_url?: string;
  manager_id: string;
  status: ClientStatus;
  contract_start?: string;
  contract_end?: string;
  created_at: string;
  updated_at: string;
}

export interface ClientCreate {
  name: string;
  industry?: string;
  manager_id: string;
  contract_start?: string;
  contract_end?: string;
}

// --- Platform Account ---

export interface PlatformAccount {
  id: string;
  client_id: string;
  platform: Platform;
  account_name: string;
  is_connected: boolean;
  token_expires_at?: string;
  created_at: string;
}

// --- Content ---

export interface Content {
  id: string;
  client_id: string;
  title: string;
  body?: string;
  content_type: ContentType;
  status: ContentStatus;
  media_urls?: Record<string, unknown>;
  hashtags?: string[];
  target_platforms: string[];
  scheduled_at?: string;
  published_at?: string;
  approved_at?: string;
  approved_by?: string;
  ai_metadata?: Record<string, unknown>;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface ContentCreate {
  client_id: string;
  title: string;
  body?: string;
  content_type: ContentType;
  target_platforms: string[];
  hashtags?: string[];
  scheduled_at?: string;
}

export interface ContentApproval {
  id: string;
  content_id: string;
  from_status: ContentStatus;
  to_status: ContentStatus;
  reviewer_id: string;
  comment?: string;
  is_urgent: boolean;
  created_at: string;
}

// --- Publishing ---

export interface PublishingLog {
  id: string;
  content_id: string;
  platform_account_id: string;
  status: PublishingStatus;
  platform_post_id?: string;
  platform_post_url?: string;
  error_message?: string;
  retry_count: number;
  scheduled_at?: string;
  published_at?: string;
  celery_task_id?: string;
  created_at: string;
}

// --- Comment ---

export interface Comment {
  id: string;
  platform_account_id: string;
  content_id?: string;
  platform_comment_id: string;
  parent_comment_id?: string;
  author_name: string;
  author_profile_url?: string;
  message: string;
  sentiment?: Sentiment;
  sentiment_score?: number;
  status: CommentStatus;
  ai_reply_draft?: string;
  replied_at?: string;
  replied_by?: string;
  commented_at: string;
  created_at: string;
}

export interface SentimentStats {
  positive: number;
  neutral: number;
  negative: number;
  crisis: number;
  total: number;
}

// --- Filter Rule ---

export interface FilterRule {
  id: string;
  client_id: string;
  rule_type: RuleType;
  value: string;
  action: FilterAction;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// --- Notification ---

export interface Notification {
  id: string;
  user_id: string;
  type: NotificationType;
  title: string;
  message: string;
  reference_type?: string;
  reference_id?: string;
  is_read: boolean;
  read_at?: string;
  priority: NotificationPriority;
  created_at: string;
}

// --- Analytics ---

export interface MetricWithChange {
  value: number;
  change_percent: number;
  trend: 'up' | 'down' | 'flat';
}

export interface DashboardKPI {
  reach: MetricWithChange;
  engagement_rate: MetricWithChange;
  follower_change: MetricWithChange;
  video_views: MetricWithChange;
  top_content: ContentSummary[];
  worst_content: ContentSummary[];
  trend_data?: { date: string; reach: number; engagement: number }[];
  platform_data?: { platform: string; followers: number; engagement: number }[];
}

export interface ContentSummary {
  id: string;
  title: string;
  engagement_rate: number;
}

export interface TrendPoint {
  date: string;
  reach: number;
  engagement: number;
  followers: number;
}

// --- Settings ---

export interface WorkflowSettings {
  approval_steps: string[];
  auto_publish_on_approve: boolean;
  urgent_skip_enabled: boolean;
  notification_channels: Record<string, string[]>;
}

export interface NotificationPreferences {
  email_enabled: boolean;
  slack_webhook_url?: string;
  kakao_enabled: boolean;
  crisis_alert: string[];
  approval_request: string[];
  publish_result: string[];
}

// --- FAQ/Guideline ---

export interface FaqGuideline {
  id: string;
  client_id: string;
  category: FaqCategory;
  title: string;
  content: string;
  tags?: string[];
  is_active: boolean;
  priority: number;
  created_at: string;
  updated_at: string;
}
