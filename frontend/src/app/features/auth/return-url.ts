/**
 * Only allow in-app paths after login ("/cart"), never "//evil.com" or "https://..."
 * — otherwise ?returnUrl= becomes an open redirect.
 */
export function safeReturnUrl(url: string | null | undefined): string {
  return url && url.startsWith('/') && !url.startsWith('//') ? url : '/';
}
