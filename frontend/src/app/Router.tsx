import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { MainLayout } from '@/components/layout/MainLayout';
import { ErrorBoundary } from '@/components/feedback/ErrorBoundary';
import { LoginPage } from '@/features/auth/LoginPage';
import { DashboardPage } from '@/features/dashboard/DashboardPage';
import { ContentListPage } from '@/features/content/ContentListPage';
import { ContentCreatePage } from '@/features/content/ContentCreatePage';
import { ContentDetailPage } from '@/features/content/ContentDetailPage';
import { PublishingPage } from '@/features/publishing/PublishingPage';
import { CommunityPage } from '@/features/community/CommunityPage';
import { AnalyticsPage } from '@/features/analytics/AnalyticsPage';
import { ClientsPage } from '@/features/clients/ClientsPage';
import { ClientDetailPage } from '@/features/clients/ClientDetailPage';
import { AIToolsPage } from '@/features/ai-tools/AIToolsPage';
import { SettingsPage } from '@/features/settings/SettingsPage';
import { NotificationsPage } from '@/features/notifications/NotificationsPage';
import type { ReactNode } from 'react';

function ProtectedRoute({ children }: { children: ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function GuestRoute({ children }: { children: ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (isAuthenticated) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4" role="main">
      <h1 className="text-4xl font-bold">404</h1>
      <p className="text-muted-foreground">Page not found</p>
      <a href="/" className="text-primary underline hover:no-underline">
        Go to Dashboard
      </a>
    </div>
  );
}

/** Wrap each page with ErrorBoundary for fault isolation */
function PageBoundary({ children }: { children: ReactNode }) {
  return <ErrorBoundary>{children}</ErrorBoundary>;
}

export function Router() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<GuestRoute><LoginPage /></GuestRoute>} />

        {/* Protected with layout */}
        <Route element={<ProtectedRoute><MainLayout /></ProtectedRoute>}>
          <Route path="/" element={<PageBoundary><DashboardPage /></PageBoundary>} />
          <Route path="/content" element={<PageBoundary><ContentListPage /></PageBoundary>} />
          <Route path="/content/new" element={<PageBoundary><ContentCreatePage /></PageBoundary>} />
          <Route path="/content/:id" element={<PageBoundary><ContentDetailPage /></PageBoundary>} />
          <Route path="/publishing" element={<PageBoundary><PublishingPage /></PageBoundary>} />
          <Route path="/community" element={<PageBoundary><CommunityPage /></PageBoundary>} />
          <Route path="/analytics" element={<PageBoundary><AnalyticsPage /></PageBoundary>} />
          <Route path="/clients" element={<PageBoundary><ClientsPage /></PageBoundary>} />
          <Route path="/clients/:id" element={<PageBoundary><ClientDetailPage /></PageBoundary>} />
          <Route path="/ai-tools" element={<PageBoundary><AIToolsPage /></PageBoundary>} />
          <Route path="/settings" element={<PageBoundary><SettingsPage /></PageBoundary>} />
          <Route path="/notifications" element={<PageBoundary><NotificationsPage /></PageBoundary>} />
        </Route>

        {/* Fallback */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
}
