import { Heart, MessageCircle, Share2, ThumbsUp, Eye } from 'lucide-react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import type { Platform } from '@/types';
import { cn } from '@/utils/cn';

interface PlatformPreviewProps {
  title?: string;
  body?: string;
  mediaUrls?: string[];
  defaultPlatform?: Platform;
}

interface InstagramPreviewProps {
  title?: string;
  body?: string;
  mediaUrl?: string;
}

function InstagramPreview({ title, body, mediaUrl }: InstagramPreviewProps) {
  return (
    <div className="mx-auto w-full max-w-sm rounded-xl border border-border bg-white dark:bg-gray-900 overflow-hidden shadow-sm">
      {/* Header */}
      <div className="flex items-center gap-3 px-3 py-2.5">
        <div className="h-8 w-8 rounded-full bg-gradient-to-br from-pink-500 to-orange-400" />
        <div>
          <p className="text-xs font-semibold text-gray-900 dark:text-gray-100">your_brand</p>
          <p className="text-xs text-gray-500">Just now</p>
        </div>
        <span className="ml-auto text-xs font-semibold text-blue-500">Follow</span>
      </div>

      {/* Image area — square 1:1 */}
      <div className="aspect-square w-full bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-800 flex items-center justify-center overflow-hidden">
        {mediaUrl ? (
          <img src={mediaUrl} alt="Content" className="h-full w-full object-cover" />
        ) : (
          <span className="text-xs text-gray-400">No image</span>
        )}
      </div>

      {/* Actions */}
      <div className="px-3 pt-2.5 pb-1">
        <div className="flex items-center gap-3 text-gray-700 dark:text-gray-300">
          <Heart className="h-5 w-5" />
          <MessageCircle className="h-5 w-5" />
          <Share2 className="h-5 w-5" />
        </div>
        <p className="mt-1.5 text-xs font-semibold text-gray-900 dark:text-gray-100">1,234 likes</p>
        <p className="mt-0.5 text-xs text-gray-900 dark:text-gray-100">
          <span className="font-semibold">your_brand</span>{' '}
          <span className="text-gray-700 dark:text-gray-300 line-clamp-3">
            {body ?? title ?? 'No caption yet.'}
          </span>
        </p>
      </div>
    </div>
  );
}

interface FacebookPreviewProps {
  title?: string;
  body?: string;
  mediaUrl?: string;
}

function FacebookPreview({ title, body, mediaUrl }: FacebookPreviewProps) {
  return (
    <div className="mx-auto w-full max-w-md rounded-xl border border-border bg-white dark:bg-gray-900 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3">
        <div className="h-10 w-10 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold text-sm">
          YB
        </div>
        <div>
          <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">Your Brand Page</p>
          <p className="text-xs text-gray-500">Just now · Public</p>
        </div>
        <span className="ml-auto text-xs text-blue-600 font-semibold">+ Follow</span>
      </div>

      {/* Post text */}
      <p className="px-4 pb-3 text-sm text-gray-900 dark:text-gray-100 line-clamp-4">
        {body ?? title ?? 'No content yet.'}
      </p>

      {/* Image — wide 16:9 ratio */}
      <div className="aspect-video w-full bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-700 dark:to-gray-800 flex items-center justify-center overflow-hidden">
        {mediaUrl ? (
          <img src={mediaUrl} alt="Content" className="h-full w-full object-cover" />
        ) : (
          <span className="text-xs text-gray-400">No image</span>
        )}
      </div>

      {/* Reaction counts */}
      <div className="flex items-center justify-between border-b border-gray-100 dark:border-gray-800 px-4 py-1.5 text-xs text-gray-500">
        <span>👍 ❤️ 😮  234</span>
        <span>45 comments · 12 shares</span>
      </div>

      {/* Reaction bar */}
      <div className="flex divide-x divide-gray-100 dark:divide-gray-800">
        {[
          { icon: <ThumbsUp className="h-4 w-4" />, label: 'Like' },
          { icon: <MessageCircle className="h-4 w-4" />, label: 'Comment' },
          { icon: <Share2 className="h-4 w-4" />, label: 'Share' },
        ].map((action) => (
          <button
            key={action.label}
            type="button"
            className="flex flex-1 items-center justify-center gap-1.5 py-2 text-xs font-medium text-gray-500 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          >
            {action.icon}
            {action.label}
          </button>
        ))}
      </div>
    </div>
  );
}

interface YouTubePreviewProps {
  title?: string;
  body?: string;
  mediaUrl?: string;
}

function YouTubePreview({ title, body, mediaUrl }: YouTubePreviewProps) {
  return (
    <div className="mx-auto w-full max-w-md overflow-hidden">
      {/* Thumbnail — 16:9 */}
      <div className="aspect-video w-full rounded-xl bg-gradient-to-br from-gray-800 to-gray-900 flex items-center justify-center overflow-hidden relative">
        {mediaUrl ? (
          <img src={mediaUrl} alt="Thumbnail" className="h-full w-full object-cover" />
        ) : (
          <span className="text-xs text-gray-400">No thumbnail</span>
        )}
        {/* Play button overlay */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-600 text-white shadow-lg">
            <svg viewBox="0 0 24 24" fill="currentColor" className="h-6 w-6 pl-0.5">
              <path d="M8 5v14l11-7z" />
            </svg>
          </div>
        </div>
        {/* Duration badge */}
        <span className="absolute bottom-2 right-2 rounded bg-black/80 px-1.5 py-0.5 text-xs text-white">
          3:42
        </span>
      </div>

      {/* Video info */}
      <div className="mt-3 flex gap-3">
        <div className="h-9 w-9 flex-shrink-0 rounded-full bg-red-600" />
        <div className="flex-1 overflow-hidden">
          <p className="font-semibold text-sm text-foreground line-clamp-2">
            {title ?? 'Video Title'}
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">Your Brand Channel</p>
          <p className="text-xs text-muted-foreground">12K views · Just now</p>
          {body && (
            <p className="mt-1 text-xs text-muted-foreground line-clamp-2">{body}</p>
          )}
        </div>
        <div className="flex items-start">
          <button type="button" className="text-muted-foreground">
            <Eye className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Stats bar */}
      <div className="mt-3 flex items-center gap-4 border-t border-border pt-3 text-xs text-muted-foreground">
        <span className="flex items-center gap-1">
          <ThumbsUp className="h-3.5 w-3.5" /> 1.2K
        </span>
        <span className="flex items-center gap-1">
          <MessageCircle className="h-3.5 w-3.5" /> 84 comments
        </span>
        <span className="flex items-center gap-1">
          <Share2 className="h-3.5 w-3.5" /> Share
        </span>
      </div>
    </div>
  );
}

export function PlatformPreview({
  title,
  body,
  mediaUrls = [],
  defaultPlatform = 'instagram',
}: PlatformPreviewProps) {
  const mediaUrl = mediaUrls[0];

  return (
    <div className={cn('rounded-lg border border-border bg-card p-4 shadow-sm')}>
      <p className="mb-4 text-sm font-semibold text-foreground">Platform Preview</p>
      <Tabs defaultValue={defaultPlatform}>
        <TabsList className="mb-4 w-full">
          <TabsTrigger value="instagram" className="flex-1">Instagram</TabsTrigger>
          <TabsTrigger value="facebook" className="flex-1">Facebook</TabsTrigger>
          <TabsTrigger value="youtube" className="flex-1">YouTube</TabsTrigger>
        </TabsList>
        <TabsContent value="instagram">
          <InstagramPreview title={title} body={body} mediaUrl={mediaUrl} />
        </TabsContent>
        <TabsContent value="facebook">
          <FacebookPreview title={title} body={body} mediaUrl={mediaUrl} />
        </TabsContent>
        <TabsContent value="youtube">
          <YouTubePreview title={title} body={body} mediaUrl={mediaUrl} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
