/** GET /api/auth/me/ */
export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
}

/** POST /api/auth/login/ */
export interface LoginRequest {
  email: string;
  password: string;
}

/** POST /api/auth/register/ (response is a User; the password is never returned) */
export interface RegisterRequest {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
}

/** Response of POST /api/auth/login/ */
export interface TokenPair {
  access: string;
  refresh: string;
}

/** Response of POST /api/auth/refresh/ (SimpleJWT without rotation: access only) */
export interface RefreshResponse {
  access: string;
  refresh?: string;
}
