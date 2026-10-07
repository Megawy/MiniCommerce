// Production build (`npm run build`, Docker image). The browser calls Django directly, so this must be
// a URL the *browser* can reach (http://localhost:8000/api) — never a Docker service name like `web`.
// Set at build time, no source edits:  ng build --define "MC_API_BASE_URL='https://api.example.com/api'"
// (Docker: build arg API_BASE_URL). Without --define, the local Docker stack's URL is used.
declare const MC_API_BASE_URL: string | undefined;

export const environment = {
  production: true,
  apiBaseUrl: typeof MC_API_BASE_URL === 'string' ? MC_API_BASE_URL : 'http://localhost:8000/api',
};
