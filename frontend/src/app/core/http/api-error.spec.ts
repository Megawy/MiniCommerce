import { HttpErrorResponse } from '@angular/common/http';

import { safeReturnUrl } from '../../features/auth/return-url';
import { apiErrorMessage, fieldErrors } from './api-error';

const response = (status: number, error: unknown) => new HttpErrorResponse({ status, error });

describe('apiErrorMessage / fieldErrors', () => {
  it('uses DRF "detail" messages', () => {
    expect(apiErrorMessage(response(400, { detail: 'Your cart is empty.' }))).toBe('Your cart is empty.');
  });

  it('extracts field validation errors', () => {
    const err = response(400, { email: ['A user with this email already exists.'] });
    expect(fieldErrors(err)).toEqual({ email: ['A user with this email already exists.'] });
    expect(apiErrorMessage(err)).toBe('email: A user with this email already exists.');
  });

  it('explains network failures', () => {
    expect(apiErrorMessage(response(0, null))).toContain('Cannot reach the server');
  });
});

describe('safeReturnUrl', () => {
  it('allows in-app paths only', () => {
    expect(safeReturnUrl('/cart')).toBe('/cart');
    expect(safeReturnUrl('//evil.example')).toBe('/');
    expect(safeReturnUrl('https://evil.example')).toBe('/');
    expect(safeReturnUrl(undefined)).toBe('/');
  });
});

describe('apiErrorMessage status mapping', () => {
  it.each([
    [401, 'Your session has expired. Please sign in again.'],
    [409, 'The item changed while you were updating it. Please try again.'],
    [429, 'Too many requests. Please wait a moment and try again.'],
    [500, 'Something went wrong on the server. Please try again later.'],
    [503, 'Something went wrong on the server. Please try again later.'],
  ])('%i -> friendly text, never the raw body', (status, expected) => {
    expect(apiErrorMessage(response(status, { detail: 'raw server text' }))).toBe(expected);
  });

  it('shows business-rule messages without the field name', () => {
    expect(apiErrorMessage(response(400, { quantity: ['Only 3 left in stock.'] }))).toBe('Only 3 left in stock.');
  });

  it('accepts per-call overrides (login: 401 = bad credentials)', () => {
    expect(apiErrorMessage(response(401, {}), { 401: 'Incorrect email or password.' })).toBe(
      'Incorrect email or password.',
    );
  });
});
