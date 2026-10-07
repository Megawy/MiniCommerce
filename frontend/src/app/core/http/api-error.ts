import { HttpErrorResponse } from '@angular/common/http';

/** DRF error bodies: {"detail": "..."} or {"field": ["msg", ...], "non_field_errors": [...]}. */
export type FieldErrors = Record<string, string[]>;

/** Per-call wording for specific statuses, e.g. login: {401: 'Incorrect email or password.'}. */
export type MessageOverrides = Partial<Record<number, string>>;

const STATUS_MESSAGES: Record<number, string> = {
  401: 'Your session has expired. Please sign in again.',
  403: "You don't have permission to do that.",
  404: "We couldn't find what you were looking for.",
  409: 'The item changed while you were updating it. Please try again.',
  429: 'Too many requests. Please wait a moment and try again.',
};

const BARE_FIELDS = new Set(['non_field_errors', 'quantity', 'product_id']);

/** Field-level validation errors from a DRF 400 response (empty if there are none). */
export function fieldErrors(error: unknown): FieldErrors {
  if (
    !(error instanceof HttpErrorResponse) ||
    error.status !== 400 ||
    typeof error.error !== 'object' ||
    !error.error
  ) {
    return {};
  }
  const result: FieldErrors = {};
  for (const [field, value] of Object.entries(error.error as Record<string, unknown>)) {
    if (field === 'detail') continue;
    result[field] = Array.isArray(value) ? value.map(String) : [String(value)];
  }
  return result;
}

/**
 * The one place that turns any API failure into a user-facing sentence.
 *  - 400: the backend's own message (business rules / validation are written for users);
 *  - 401/403/404/409/429/5xx/network: fixed friendly text (never raw server output).
 */
export function apiErrorMessage(error: unknown, overrides: MessageOverrides = {}): string {
  if (!(error instanceof HttpErrorResponse)) return 'Something went wrong.';
  const status = error.status;
  if (overrides[status]) return overrides[status]!;
  if (status === 0) return 'Cannot reach the server. Check your connection and try again.';
  if (status >= 500) return 'Something went wrong on the server. Please try again later.';
  if (STATUS_MESSAGES[status]) return STATUS_MESSAGES[status];

  const detail = (error.error as { detail?: unknown } | null)?.detail;
  if (typeof detail === 'string') return detail;
  const first = Object.entries(fieldErrors(error))[0];
  if (first) {
    const [field, messages] = first;
    // Business-rule errors already read as sentences ("Only 3 left in stock."); others get the field name.
    return BARE_FIELDS.has(field) ? messages[0] : `${field}: ${messages[0]}`;
  }
  return `Request failed (${status}).`;
}
