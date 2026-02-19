import { useQuery } from '@tanstack/react-query';
import { format, subDays } from 'date-fns';
import { AlertTriangle, TrendingUp } from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { communityApi } from '@/api/community';
import type { Sentiment } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { PageHeader } from '@/components/common/PageHeader';

const SENTIMENT_COLORS: Record<Sentiment, string> = {
  positive: '#22c55e',
  neutral: '#94a3b8',
  negative: '#ef4444',
  crisis: '#dc2626',
};

const SENTIMENT_LABELS: Record<Sentiment, string> = {
  positive: 'Positive',
  neutral: 'Neutral',
  negative: 'Negative',
  crisis: 'Crisis',
};

// Mock crisis events for the timeline (in production these would come from the API)
interface CrisisEvent {
  id: string;
  timestamp: string;
  message: string;
  platform: string;
  resolved: boolean;
}

const MOCK_CRISIS_EVENTS: CrisisEvent[] = [
  {
    id: '1',
    timestamp: new Date(Date.now() - 3600000).toISOString(),
    message: 'Spike in negative comments detected on Instagram post',
    platform: 'Instagram',
    resolved: false,
  },
  {
    id: '2',
    timestamp: new Date(Date.now() - 86400000).toISOString(),
    message: 'Crisis keyword detected in 12 comments',
    platform: 'Facebook',
    resolved: true,
  },
  {
    id: '3',
    timestamp: new Date(Date.now() - 172800000).toISOString(),
    message: 'Rapid negative sentiment increase (34% in 1hr)',
    platform: 'YouTube',
    resolved: true,
  },
];

// Generate mock trend data for 30 days
function generateTrendData() {
  return Array.from({ length: 30 }, (_, i) => {
    const day = subDays(new Date(), 29 - i);
    const base = 100;
    return {
      date: format(day, 'MM/dd'),
      positive: Math.floor(base * (0.5 + Math.random() * 0.3)),
      neutral: Math.floor(base * (0.2 + Math.random() * 0.15)),
      negative: Math.floor(base * (0.05 + Math.random() * 0.1)),
      crisis: Math.floor(Math.random() * 3),
    };
  });
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}

function CustomLineTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-border bg-background p-2 shadow-md text-xs">
      <p className="font-semibold mb-1">{label}</p>
      {payload.map((entry) => (
        <div key={entry.name} className="flex items-center gap-2">
          <span
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span className="capitalize">{entry.name}:</span>
          <span className="font-medium">{entry.value}</span>
        </div>
      ))}
    </div>
  );
}

interface SentimentDashboardProps {
  clientId?: string;
}

export function SentimentDashboard({ clientId }: SentimentDashboardProps) {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['community', 'sentiment', clientId],
    queryFn: async () => {
      const res = await communityApi.getSentiment(clientId);
      return res.data.data;
    },
  });

  const trendData = generateTrendData();

  const pieData = stats
    ? (['positive', 'neutral', 'negative', 'crisis'] as Sentiment[])
        .map((key) => ({
          name: SENTIMENT_LABELS[key],
          value: stats[key],
          color: SENTIMENT_COLORS[key],
          key,
        }))
        .filter((d) => d.value > 0)
    : [];

  const totalComments = stats?.total ?? 0;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Sentiment Dashboard"
        description="Real-time community sentiment analysis and crisis monitoring"
      />

      {/* KPI summary row */}
      {stats && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {(['positive', 'neutral', 'negative', 'crisis'] as Sentiment[]).map((key) => {
            const value = stats[key];
            const pct = totalComments > 0 ? ((value / totalComments) * 100).toFixed(1) : '0';
            return (
              <Card key={key}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-xs font-medium text-muted-foreground capitalize">
                        {SENTIMENT_LABELS[key]}
                      </p>
                      <p className="mt-1 text-2xl font-bold text-foreground">{value}</p>
                      <p className="text-xs text-muted-foreground">{pct}%</p>
                    </div>
                    <span
                      className="h-3 w-3 rounded-full mt-1"
                      style={{ backgroundColor: SENTIMENT_COLORS[key] }}
                    />
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Pie chart */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Sentiment Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex h-60 items-center justify-center text-sm text-muted-foreground">
                Loading...
              </div>
            ) : pieData.length === 0 ? (
              <div className="flex h-60 items-center justify-center text-sm text-muted-foreground">
                No data available
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={3}
                    dataKey="value"
                  >
                    {pieData.map((entry) => (
                      <Cell key={entry.key} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value: number, name: string) => [value, name]}
                    contentStyle={{
                      fontSize: '12px',
                      borderRadius: '8px',
                      border: '1px solid var(--border)',
                      backgroundColor: 'var(--background)',
                    }}
                  />
                  <Legend
                    iconType="circle"
                    iconSize={8}
                    formatter={(value) => (
                      <span className="text-xs text-foreground">{value}</span>
                    )}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Line chart — 30-day trend */}
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">30-Day Trend</CardTitle>
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <TrendingUp className="h-3.5 w-3.5" />
                Last 30 days
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={trendData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 10 }}
                  tickLine={false}
                  axisLine={false}
                  interval={6}
                />
                <YAxis tick={{ fontSize: 10 }} tickLine={false} axisLine={false} />
                <Tooltip content={<CustomLineTooltip />} />
                <Line
                  type="monotone"
                  dataKey="positive"
                  stroke={SENTIMENT_COLORS.positive}
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="neutral"
                  stroke={SENTIMENT_COLORS.neutral}
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="negative"
                  stroke={SENTIMENT_COLORS.negative}
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="crisis"
                  stroke={SENTIMENT_COLORS.crisis}
                  strokeWidth={2}
                  strokeDasharray="4 2"
                  dot={false}
                />
                <Legend
                  iconType="circle"
                  iconSize={8}
                  formatter={(value) => (
                    <span className="text-xs capitalize text-foreground">{value}</span>
                  )}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Crisis alert timeline */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-red-500" />
            <CardTitle className="text-base">Crisis Alert Timeline</CardTitle>
            {MOCK_CRISIS_EVENTS.filter((e) => !e.resolved).length > 0 && (
              <Badge className="bg-red-600 text-white text-xs">
                {MOCK_CRISIS_EVENTS.filter((e) => !e.resolved).length} Active
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {MOCK_CRISIS_EVENTS.map((event) => (
              <div
                key={event.id}
                className={`flex items-start gap-3 rounded-lg border p-3 ${
                  event.resolved
                    ? 'border-border bg-muted/30'
                    : 'border-red-300 bg-red-50 dark:border-red-800 dark:bg-red-900/10'
                }`}
              >
                <div className="flex-shrink-0 mt-0.5">
                  <AlertTriangle
                    className={`h-4 w-4 ${
                      event.resolved ? 'text-muted-foreground' : 'text-red-500'
                    }`}
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span
                      className={`text-sm font-medium ${
                        event.resolved ? 'text-muted-foreground' : 'text-red-700 dark:text-red-400'
                      }`}
                    >
                      {event.message}
                    </span>
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                    <span>{event.platform}</span>
                    <span>·</span>
                    <span>{format(new Date(event.timestamp), 'MMM d, HH:mm')}</span>
                    {event.resolved && (
                      <>
                        <span>·</span>
                        <span className="text-green-600">Resolved</span>
                      </>
                    )}
                  </div>
                </div>
                {!event.resolved && (
                  <Badge className="bg-red-600 text-white text-xs flex-shrink-0">
                    Active
                  </Badge>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
