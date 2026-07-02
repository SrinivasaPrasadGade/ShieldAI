import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AlertFeed } from '../components/layout/AlertFeed';
import React from 'react';

describe('AlertFeed Component', () => {
  it('renders a list of alerts and handles clicks', () => {
    const alerts = [
      { id: '1', title: 'Scam Detected', description: 'Phishing attempt', risk_score: 0.9, risk_label: 'HIGH', timestamp: new Date().toISOString() },
      { id: '2', title: 'Suspicious Activity', description: 'Login from new device', risk_score: 0.5, risk_label: 'MEDIUM', timestamp: new Date().toISOString() },
    ];

    const mockOnAlertClick = vi.fn();

    render(
      <AlertFeed 
        alerts={alerts} 
        onAlertClick={mockOnAlertClick} 
      />
    );

    // Verify elements are rendered
    expect(screen.getAllByText('Scam Detected')[1]).toBeInTheDocument();
    expect(screen.getByText('Suspicious Activity')).toBeInTheDocument();

    // Simulate click on an alert
    fireEvent.click(screen.getAllByText('Scam Detected')[1]);

    // Assert callback was called
    expect(mockOnAlertClick).toHaveBeenCalledWith(alerts[0]);
  });
});
