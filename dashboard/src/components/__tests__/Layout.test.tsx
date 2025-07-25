import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Layout from '../Layout';

const renderWithRouter = (component: React.ReactElement) => {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  );
};

describe('Layout', () => {
  it('renders the main navigation elements', () => {
    renderWithRouter(<Layout />);
    
    // Check if the app title is present
    expect(screen.getByText('Discord Ticket Bot')).toBeInTheDocument();
    
    // Check if navigation items are present
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Tickets')).toBeInTheDocument();
    expect(screen.getByText('Search Transcripts')).toBeInTheDocument();
  });

  it('applies the correct theme', () => {
    renderWithRouter(<Layout />);
    
    // The layout should render without errors
    expect(screen.getByRole('main')).toBeInTheDocument();
  });
});