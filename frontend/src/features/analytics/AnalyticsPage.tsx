import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '@/api/analytics';
import { PageHeader } from '@/components/common/PageHeader';
import { LoadingSpinner } from '@/components/feedback/LoadingSpinner';

export function AnalyticsPage() {
  const { data: perf, isLoading } = useQuery({
    queryKey: ['analytics', 'content-perf'],
    queryFn: async () => { const res = await analyticsApi.getContentPerf(); return res.data.data; },
  });

  const { data: trends } = useQuery({
    queryKey: ['analytics', 'trends'],
    queryFn: async () => { const res = await analyticsApi.getTrends({ period: '7d' }); return res.data.data; },
  });

  return (
    <div>
      <PageHeader title="Analytics" description="Performance analysis and insights" />

      {isLoading ? (
        <LoadingSpinner />
      ) : (
        <div className="space-y-6">
          {/* Content type performance */}
          <div className="rounded-lg border bg-card p-6">
            <h3 className="mb-4 font-semibold">Content Performance by Type</h3>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
              {perf?.map((item) => (
                <div key={item.content_type} className="rounded-lg border p-4 text-center">
                  <p className="text-xs text-muted-foreground capitalize">{item.content_type}</p>
                  <p className="mt-1 text-lg font-bold">{item.count}</p>
                  <p className="text-xs text-muted-foreground">posts</p>
                </div>
              ))}
            </div>
          </div>

          {/* Trend data */}
          <div className="rounded-lg border bg-card p-6">
            <h3 className="mb-4 font-semibold">7-Day Trend</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs text-muted-foreground">
                    <th className="pb-2">Date</th>
                    <th className="pb-2">Reach</th>
                    <th className="pb-2">Engagement</th>
                    <th className="pb-2">Followers</th>
                  </tr>
                </thead>
                <tbody>
                  {trends?.map((point) => (
                    <tr key={point.date} className="border-b last:border-0">
                      <td className="py-2">{point.date}</td>
                      <td className="py-2">{point.reach}</td>
                      <td className="py-2">{point.engagement}</td>
                      <td className="py-2">{point.followers}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
