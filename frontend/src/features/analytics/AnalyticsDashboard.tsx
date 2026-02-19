import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { format, subDays } from 'date-fns';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Users,
  Eye,
  Heart,
  Video,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
  CartesianGrid,
} from 'recharts';
import { analyticsApi } from '@/api/analytics';
import type { MetricWithChange } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { PageHeader } from '@/components/common/PageHeader';
import { cn } from '@/utils/cn';

type DateRange = '7d' | '30d' | '90d';
type PlatformFilter = 'all' | 'instagram' | 'facebook' | 'youtube';

const DATE_RANGE_OPTIONS: { value: DateRange; label: string }[] = [
  { value: '7d', label: '7 Days' },
  { value: '30d', label: '30 Days' },
  { value: '90d', label: '90 Days' },
];

const PLATFORM_OPTIONS: { value: PlatformFilter; label: string }[] = [
  { value: 'all', label: 'All Platforms' },
  { value: 'instagram', label: 'Instagram' },
  { value: 'facebook', label: 'Facebook' },
  { value: 'youtube', label: 'YouTube' },
];

function formatNumber(num: number): string {
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
  return num.toString();
}

interface KpiCardProps {
  title: string;
  metric: MetricWithChange;
  icon: React.ReactNode;
  format?: (v: number) => string;
}

function KpiCard({ title, metric, icon, format: fmt }: KpiCardProps) {
  const isUp = metric.trend === 'up';
  const isDown = metric.trend === 'down';
  const isFlat = metric.trend === 'flat';

  const TrendIcon = isUp ? ArrowUpRight : isDown ? ArrowDownRight : Minus;
  const trendColor = isUp
    ? 'text-green-600'
    : isDown
    ? 'text-red-500'
    : 'text-muted-foreground';

  return (
    <Card>
      <CardContent className="p-5">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="mt-1 text-2xl font-bold text-foreground">
              {fmt ? fmt(metric.value) : formatNumber(metric.value)}
            </p>
            <div className={cn('mt-1 flex items-center gap-1 text-xs', trendColor)}>
              <TrendIcon className="h-3.5 w-3.5" />
              <span>
                {isFlat ? 'No change' : `${Math.abs(metric.change_percent).toFixed(1)}%`}
                {!isFlat && (isUp ? ' up' : ' down')}
              </span>
            </div>
          </div>
          <div className="rounded-lg bg-primary/10 p-2 text-primary">{icon}</div>
        </div>
      </CardContent>
    </Card>
  );
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}

function ChartTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-border bg-background p-2 shadow-md text-xs">
      <p className="font-semibold mb-1">{label}</p>
      {payload.map((entry) => (
        <div key={entry.name} className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: entry.color }} />
          <span className="capitalize">{entry.name}:</span>
          <span className="font-medium">{formatNumber(entry.value)}</span>
        </div>
      ))}
    </div>
  );
}

// Generate fallback trend data
function generateFallbackTrends(days: number) {
  return Array.from({ length: days }, (_, i) => {
    const day = subDays(new Date(), days - 1 - i);
    return {
      date: format(day, 'MM/dd'),
      reach: Math.floor(5000 + Math.random() * 8000),
      engagement: Math.floor(200 + Math.random() * 600),
      followers: Math.floor(100 + Math.random() * 300),
    };
  });
}

// Platform comparison data (mock)
const PLATFORM_COMPARISON = [
  { platform: 'Instagram', reach: 45000, engagement: 3200, followers: 1200 },
  { platform: 'Facebook', reach: 28000, engagement: 1800, followers: 650 },
  { platform: 'YouTube', reach: 62000, engagement: 4100, followers: 2300 },
];

interface AnalyticsDashboardProps {
  clientId?: string;
}

export function AnalyticsDashboard({ clientId }: AnalyticsDashboardProps) {
  const [dateRange, setDateRange] = useState<DateRange>('30d');
  const [platform, setPlatform] = useState<PlatformFilter>('all');

  const days = dateRange === '7d' ? 7 : dateRange === '30d' ? 30 : 90;
  const startDate = format(subDays(new Date(), days), 'yyyy-MM-dd');
  const endDate = format(new Date(), 'yyyy-MM-dd');

  const params: Record<string, string> = {
    start_date: startDate,
    end_date: endDate,
  };
  if (platform !== 'all') params.platform = platform;
  if (clientId) params.client_id = clientId;

  const { data: kpi, isLoading: kpiLoading } = useQuery({
    queryKey: ['analytics', 'dashboard', dateRange, platform, clientId],
    queryFn: async () => {
      const res = await analyticsApi.getDashboard(params);
      return res.data.data;
    },
  });

  const { data: trends } = useQuery({
    queryKey: ['analytics', 'trends', dateRange, platform, clientId],
    queryFn: async () => {
      const res = await analyticsApi.getTrends(params);
      return res.data.data;
    },
  });

  const trendChartData = trends?.map((p) => ({
    date: format(new Date(p.date), 'MM/dd'),
    reach: p.reach,
    engagement: p.engagement,
    followers: p.followers,
  })) ?? generateFallbackTrends(days > 30 ? 30 : days);

  // Fallback KPI when API is not connected
  const fallbackKpi = {
    reach: { value: 135000, change_percent: 12.4, trend: 'up' as const },
    engagement_rate: { value: 4.8, change_percent: -2.1, trend: 'down' as const },
    follower_change: { value: 3250, change_percent: 8.7, trend: 'up' as const },
    video_views: { value: 89000, change_percent: 0, trend: 'flat' as const },
    top_content: kpi?.top_content ?? [],
    worst_content: kpi?.worst_content ?? [],
  };

  const displayKpi = kpi ?? fallbackKpi;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Analytics Dashboard"
        description="Performance insights across all platforms"
      />

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-card p-3">
        <div className="flex items-center gap-1">
          {DATE_RANGE_OPTIONS.map((opt) => (
            <Button
              key={opt.value}
              variant={dateRange === opt.value ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setDateRange(opt.value)}
            >
              {opt.label}
            </Button>
          ))}
        </div>
        <div className="h-5 w-px bg-border hidden sm:block" />
        <div className="flex items-center gap-1">
          {PLATFORM_OPTIONS.map((opt) => (
            <Button
              key={opt.value}
              variant={platform === opt.value ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setPlatform(opt.value)}
            >
              {opt.label}
            </Button>
          ))}
        </div>
      </div>

      {/* KPI cards */}
      {kpiLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardContent className="p-5">
                <div className="h-16 animate-pulse rounded bg-muted" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard
            title="Total Reach"
            metric={displayKpi.reach}
            icon={<Eye className="h-5 w-5" />}
          />
          <KpiCard
            title="Engagement Rate"
            metric={displayKpi.engagement_rate}
            icon={<Heart className="h-5 w-5" />}
            format={(v) => `${v.toFixed(1)}%`}
          />
          <KpiCard
            title="New Followers"
            metric={displayKpi.follower_change}
            icon={<Users className="h-5 w-5" />}
          />
          <KpiCard
            title="Video Views"
            metric={displayKpi.video_views}
            icon={<Video className="h-5 w-5" />}
          />
        </div>
      )}

      {/* Charts row */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Line chart — trends */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Performance Trends</CardTitle>
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <TrendingUp className="h-3.5 w-3.5" />
                {dateRange}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={trendChartData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10 }}
                  tickLine={false}
                  axisLine={false}
                  interval={Math.floor(trendChartData.length / 6)}
                />
                <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={formatNumber} />
                <Tooltip content={<ChartTooltip />} />
                <Line
                  type="monotone"
                  dataKey="reach"
                  stroke="#6366f1"
                  strokeWidth={2}
                  dot={false}
                  name="Reach"
                />
                <Line
                  type="monotone"
                  dataKey="engagement"
                  stroke="#22c55e"
                  strokeWidth={2}
                  dot={false}
                  name="Engagement"
                />
                <Line
                  type="monotone"
                  dataKey="followers"
                  stroke="#f59e0b"
                  strokeWidth={2}
                  dot={false}
                  name="Followers"
                />
                <Legend
                  iconType="circle"
                  iconSize={8}
                  formatter={(v) => <span className="text-xs text-foreground">{v}</span>}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Bar chart — platform comparison */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Platform Comparison</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart
                data={PLATFORM_COMPARISON}
                margin={{ top: 4, right: 8, left: -20, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                <XAxis
                  dataKey="platform"
                  tick={{ fontSize: 10 }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={formatNumber} />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="reach" name="Reach" fill="#6366f1" radius={[4, 4, 0, 0]} />
                <Bar dataKey="engagement" name="Engagement" fill="#22c55e" radius={[4, 4, 0, 0]} />
                <Bar dataKey="followers" name="Followers" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                <Legend
                  iconType="circle"
                  iconSize={8}
                  formatter={(v) => <span className="text-xs text-foreground">{v}</span>}
                />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Content ranking tables */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Top content */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-green-500" />
              <CardTitle className="text-base">Top Performing Content</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            {displayKpi.top_content.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">No data yet</p>
            ) : (
              <div className="space-y-2">
                {displayKpi.top_content.slice(0, 5).map((content, idx) => (
                  <div
                    key={content.id}
                    className="flex items-center gap-3 rounded-lg border border-border p-2.5"
                  >
                    <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-green-100 text-xs font-bold text-green-700 dark:bg-green-900/30 dark:text-green-400">
                      {idx + 1}
                    </span>
                    <p className="flex-1 truncate text-sm text-foreground">{content.title}</p>
                    <Badge variant="secondary" className="flex-shrink-0 text-xs">
                      {content.engagement_rate.toFixed(1)}%
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Worst content */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <TrendingDown className="h-4 w-4 text-red-500" />
              <CardTitle className="text-base">Lowest Performing Content</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            {displayKpi.worst_content.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">No data yet</p>
            ) : (
              <div className="space-y-2">
                {displayKpi.worst_content.slice(0, 5).map((content, idx) => (
                  <div
                    key={content.id}
                    className="flex items-center gap-3 rounded-lg border border-border p-2.5"
                  >
                    <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-red-100 text-xs font-bold text-red-700 dark:bg-red-900/30 dark:text-red-400">
                      {idx + 1}
                    </span>
                    <p className="flex-1 truncate text-sm text-foreground">{content.title}</p>
                    <Badge variant="secondary" className="flex-shrink-0 text-xs">
                      {content.engagement_rate.toFixed(1)}%
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
