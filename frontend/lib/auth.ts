/**
 * Manipula cookies de auth (access_token e refresh_token).
 *
 * Nomes dos cookies sao compartilhados entre client e middleware (edge),
 * entao precisam ser strings literais (nao import de const).
 */
import Cookies from "js-cookie"

export const ACCESS_TOKEN_COOKIE = "spm_access_token"
export const REFRESH_TOKEN_COOKIE = "spm_refresh_token"

// 7 dias — refresh token rotaciona; access expira em ~1h mas o interceptor renova.
const COOKIE_OPTIONS = {
  expires: 7,
  path: "/",
  sameSite: "lax" as const,
  // secure: em producao deveria ser true. Dev local (http://localhost) precisa false.
}

export function setAuthCookies(accessToken: string, refreshToken: string) {
  Cookies.set(ACCESS_TOKEN_COOKIE, accessToken, COOKIE_OPTIONS)
  Cookies.set(REFRESH_TOKEN_COOKIE, refreshToken, COOKIE_OPTIONS)
}

export function getAccessToken(): string | undefined {
  return Cookies.get(ACCESS_TOKEN_COOKIE)
}

export function getRefreshToken(): string | undefined {
  return Cookies.get(REFRESH_TOKEN_COOKIE)
}

export function clearAuthCookies() {
  Cookies.remove(ACCESS_TOKEN_COOKIE, { path: "/" })
  Cookies.remove(REFRESH_TOKEN_COOKIE, { path: "/" })
}

export function logout() {
  clearAuthCookies()
  if (typeof window !== "undefined") {
    window.location.href = "/login"
  }
}
