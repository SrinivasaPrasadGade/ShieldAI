import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CitizenChat } from '../components/features/CitizenChat';
import React from 'react';

// Mock scrollTo
window.HTMLElement.prototype.scrollTo = function() {};

describe('CitizenChat Component', () => {
  it('renders chat interface and allows typing', () => {
    render(<CitizenChat />);

    // Verify initial rendering
    expect(screen.getAllByText(/Citizen Fraud Shield/i)[0]).toBeInTheDocument();
    
    // Find input and type something
    const input = screen.getByPlaceholderText(/Describe your situation here/i);
    expect(input).toBeInTheDocument();
    
    fireEvent.change(input, { target: { value: 'Suspicious email received' } });
    expect(input.value).toBe('Suspicious email received');
  });
});
