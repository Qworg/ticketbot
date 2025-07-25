import { render, screen } from '@testing-library/react';
import Dashboard from '../Dashboard';

describe('Dashboard', () => {
  it('renders dashboard title and metrics', () => {
    render(<Dashboard />);
    
    // Check if the dashboard title is present
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    
    // Check if metric cards are present
    expect(screen.getByText('Active Tickets')).toBeInTheDocument();
    expect(screen.getByText('Assigned to Me')).toBeInTheDocument();
    expect(screen.getByText('Closed Today')).toBeInTheDocument();
    
    // Check if recent activity section is present
    expect(screen.getByText('Recent Activity')).toBeInTheDocument();
    expect(screen.getByText('No recent activity to display.')).toBeInTheDocument();
  });

  it('displays initial metric values as 0', () => {
    render(<Dashboard />);
    
    // All metric values should be 0 initially
    const metricValues = screen.getAllByText('0');
    expect(metricValues).toHaveLength(3);
  });
});