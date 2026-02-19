import { Providers } from './providers';
import { Router } from './Router';
import { ErrorBoundary } from '@/components/feedback/ErrorBoundary';
import { ToastContainer } from '@/components/feedback/Toast';
import { OfflineBanner } from '@/components/feedback/OfflineBanner';

export default function App() {
  return (
    <ErrorBoundary>
      <Providers>
        <OfflineBanner />
        <Router />
        <ToastContainer />
      </Providers>
    </ErrorBoundary>
  );
}
