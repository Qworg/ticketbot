import React from 'react';
import { Routes, Route } from 'react-router-dom';
import ErrorBoundary from './components/ErrorBoundary';
import NotificationContainer from './components/NotificationContainer';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import TicketList from './pages/TicketList';
import TicketDetail from './pages/TicketDetail';
import TranscriptSearch from './pages/TranscriptSearch';
import SharedTranscript from './pages/SharedTranscript';
import NotFound from './pages/NotFound';

function App() {
  return (
    <ErrorBoundary
      maxRetries={3}
      showErrorDetails={process.env.NODE_ENV === 'development'}
      onError={(error, errorInfo) => {
        // Log error to monitoring service in production
        if (process.env.NODE_ENV === 'production') {
          console.error('Application error:', error, errorInfo);
        }
      }}
    >
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="tickets" element={<TicketList />} />
          <Route path="tickets/:id" element={<TicketDetail />} />
          <Route path="search" element={<TranscriptSearch />} />
          <Route path="shared/:shareToken" element={<SharedTranscript />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
      
      {/* Global notification container */}
      <NotificationContainer />
    </ErrorBoundary>
  );
}

export default App;