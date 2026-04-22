import axios, { AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from "axios"

import { clearAuthCookies, getAccessToken, getRefreshToken, setAuthCookies } from "@/lib/auth"
import type {
  ConciliarResponse,
  LoginResponse,
  MeResponse,
  ResultadoResponse,
  RodadaListItem,
  UploadRodadaResponse,
} from "@/lib/types"

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export const api: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 600_000, // upload/conciliar podem ser lentos (~2-3min)
})

// Alias reutilizavel para os submodulos em lib/api/* — mesmo cliente com interceptors de auth.
export const apiClient = api

// Request: injeta Bearer
api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getAccessToken()
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response: se 401, tenta refresh uma vez; se falhar, limpa e redireciona para /login.
let refreshPromise: Promise<string | null> | null = null

async function tryRefresh(): Promise<string | null> {
  const refreshToken = getRefreshToken()
  if (!refreshToken) return null
  try {
    const r = await axios.post<{ access_token: string; refresh_token: string }>(
      `${BASE_URL}/auth/refresh`,
      { refresh_token: refreshToken },
      { timeout: 15_000 }
    )
    setAuthCookies(r.data.access_token, r.data.refresh_token)
    return r.data.access_token
  } catch {
    return null
  }
}

api.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined
    if (!original || original._retried) throw error
    if (error.response?.status !== 401) throw error
    if (original.url?.includes("/auth/login") || original.url?.includes("/auth/refresh")) throw error

    original._retried = true
    if (!refreshPromise) refreshPromise = tryRefresh().finally(() => { refreshPromise = null })
    const newToken = await refreshPromise
    if (!newToken) {
      clearAuthCookies()
      if (typeof window !== "undefined") window.location.href = "/login"
      throw error
    }
    original.headers = original.headers || {}
    original.headers.Authorization = `Bearer ${newToken}`
    return api.request(original)
  }
)

// === Funcoes tipadas ===

export async function login(email: string, password: string): Promise<LoginResponse> {
  const r = await api.post<LoginResponse>("/auth/login", { email, password })
  setAuthCookies(r.data.access_token, r.data.refresh_token)
  return r.data
}

export async function getMe(): Promise<MeResponse> {
  const r = await api.get<MeResponse>("/auth/me")
  return r.data
}

export async function listarRodadas(): Promise<RodadaListItem[]> {
  const r = await api.get<RodadaListItem[]>("/rodadas")
  return r.data
}

export async function criarRodada(formData: FormData): Promise<UploadRodadaResponse> {
  const r = await api.post<UploadRodadaResponse>("/rodadas/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  })
  return r.data
}

export async function conciliarRodada(rodadaId: string): Promise<ConciliarResponse> {
  const r = await api.post<ConciliarResponse>(`/rodadas/${rodadaId}/conciliar`)
  return r.data
}

export async function getResultado(
  rodadaId: string,
  page = 1,
  perPage = 50
): Promise<ResultadoResponse> {
  const r = await api.get<ResultadoResponse>(
    `/rodadas/${rodadaId}/resultado?page=${page}&per_page=${perPage}`
  )
  return r.data
}
