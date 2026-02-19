import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { LoadingSpinner } from './LoadingSpinner';

describe('LoadingSpinner', () => {
  it('renders spinner', () => {
    const { container } = render(<LoadingSpinner />);
    expect(container.querySelector('.animate-spin')).toBeTruthy();
  });

  it('accepts className prop', () => {
    const { container } = render(<LoadingSpinner className="mt-10" />);
    expect(container.firstElementChild?.classList.contains('mt-10')).toBe(true);
  });
});
