import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { contentsApi } from '@/api/contents';
import { PageHeader } from '@/components/common/PageHeader';
import type { ContentType } from '@/types';

export function ContentCreatePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [contentType, setContentType] = useState<ContentType>('feed');
  const [platforms, setPlatforms] = useState<string[]>(['instagram']);
  const [clientId, setClientId] = useState('');

  const mutation = useMutation({
    mutationFn: () =>
      contentsApi.create({
        client_id: clientId,
        title,
        body: body || undefined,
        content_type: contentType,
        target_platforms: platforms,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contents'] });
      navigate('/content');
    },
  });

  const togglePlatform = (p: string) => {
    setPlatforms((prev) => (prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]));
  };

  return (
    <div>
      <PageHeader title="Create Content" />

      <form
        onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}
        className="mx-auto max-w-2xl space-y-4"
      >
        <div>
          <label className="mb-1 block text-sm font-medium">Client ID</label>
          <input
            value={clientId}
            onChange={(e) => setClientId(e.target.value)}
            required
            className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            placeholder="Client UUID"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium">Title</label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium">Body</label>
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={6}
            className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium">Content Type</label>
          <select
            value={contentType}
            onChange={(e) => setContentType(e.target.value as ContentType)}
            className="w-full rounded-md border bg-background px-3 py-2 text-sm"
          >
            <option value="feed">Feed</option>
            <option value="reel">Reel</option>
            <option value="story">Story</option>
            <option value="short">Short</option>
            <option value="card_news">Card News</option>
          </select>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium">Target Platforms</label>
          <div className="flex gap-2">
            {['instagram', 'facebook', 'youtube'].map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => togglePlatform(p)}
                className={`rounded-md px-3 py-1.5 text-xs font-medium ${
                  platforms.includes(p) ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        <div className="flex gap-2 pt-4">
          <button
            type="submit"
            disabled={mutation.isPending}
            className="rounded-md bg-primary px-6 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {mutation.isPending ? 'Creating...' : 'Create'}
          </button>
          <button
            type="button"
            onClick={() => navigate('/content')}
            className="rounded-md border px-6 py-2 text-sm hover:bg-accent"
          >
            Cancel
          </button>
        </div>

        {mutation.isError && <p className="text-sm text-destructive">Failed to create content</p>}
      </form>
    </div>
  );
}
