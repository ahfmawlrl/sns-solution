import { useQuery } from '@tanstack/react-query';
import { TrendingUp, TrendingDown, Minus, Eye, Heart, UserPlus, Play } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { analyticsApi } from '@/api/analytics';
import { PageHeader } from '@/components/common/PageHeader';
import { LoadingSpinner } from '@/components/feedback/LoadingSpinner';
import type { MetricWithChange } from '@/types';

const MOCK_TREND = [
  { date: 'Mon', reach: 2400, engagement: 400 },
  { date: 'Tue', reach: 1398, engagement: 300 },
  { date: 'Wed', reach: 9800, engagement: 500 },
  { date: 'Thu', reach: 3908, engagement: 480 },
  { date: 'Fri', reach: 4800, engagement: 380 },
  { date: 'Sat', reach: 3800, engagement: 430 },
  { date: 'Sun', reach: 4300, engagement: 450 },
];

const MOCK_PLATFORM = [
  { platform: 'Instagram', followers: 12400, engagement: 980 },
  { platform: 'Facebook', followers: 8200, engagement: 620 },
  { platform: 'YouTube', followers: 5600, engagement: 440 },
];

function KPICard({ label, metric, icon: Icon }: { label: string; metric: MetricWithChange; icon: React.ElementType }) {
  const TrendIcon = metric.trend === 'up' ? TrendingUp : metric.trend === 'down' ? TrendingDown : Minus;
  const trendColor = metric.trend === 'up' ? 'text-green-500' : metric.trend === 'down' ? 'text-red-500' : 'text-muted-foreground';

  return (
    <div className="rounded-lg border bg-card p-5">
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">{label}</span>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </div>
      <p className="mt-2 text-2xl font-bold">{metric.value.toLocaleString()}</p>
      <div className={`mt-1 flex items-center gap-1 text-xs ${trendColor}`}>
        <TrendIcon className="h-3 w-3" />
        <span>{metric.change_percent >= 0 ? '+' : ''}{metric.change_percent}%</span>
      </div>
    </div>
  );
}

export function DashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['analytics', 'dashboard'],
    queryFn: async () => {
      const res = await analyticsApi.getDashboard();
      return res.data.data;
    },
    staleTime: 30_000,
  });

  if (isLoading) return <LoadingSpinner />;

  const kpi = data;

  return (
    <div>
      <PageHeader title="Dashboard" description="Overview of your SNS performance" />

      {kpi && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KPICard label="Reach" metric={kpi.reach} icon={Eye} />
          <KPICard label="Engagement Rate" metric={kpi.engagement_rate} icon={Heart} />
          <KPICard label="Follower Change" metric={kpi.follower_change} icon={UserPlus} />
          <KPICard label="Video Views" metric={kpi.video_views} icon={Play} />
        </div>
      )}

      {/* Trend Charts */}
      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Reach Trend */}
        <div className="rounded-lg border bg-card p-5">
          <h3 className="mb-4 text-sm font-semibold">Reach Trend (7 days)</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={kpi?.trend_data ?? MOCK_TREND}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} className="text-muted-foreground" />
              <YAxis tick={{ fontSize: 12 }} className="text-muted-foreground" />
              <Tooltip />
              <Line type="monotone" dataKey="reach" stroke="#3b82f6" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="engagement" stroke="#10b981" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Platform Performance */}
        <div className="rounded-lg border bg-card p-5">
          <h3 className="mb-4 text-sm font-semibold">Platform Performance</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={kpi?.platform_data ?? MOCK_PLATFORM}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis dataKey="platform" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="followers" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              <Bar dataKey="engagement" fill="#10b981" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
