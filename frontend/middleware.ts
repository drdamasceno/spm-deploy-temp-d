import { NextResponse, type NextRequest } from "next/server"

// Cookie names duplicados aqui (em vez de import) porque edge runtime
// nao compartilha o mesmo bundle do client. Manter em sync com lib/auth.ts.
const ACCESS_TOKEN_COOKIE = "spm_access_token"

const PUBLIC_PATHS = ["/login"]

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl
  const isPublic = PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`))
  const hasToken = Boolean(req.cookies.get(ACCESS_TOKEN_COOKIE)?.value)

  if (!hasToken && !isPublic) {
    const url = req.nextUrl.clone()
    url.pathname = "/login"
    return NextResponse.redirect(url)
  }

  if (hasToken && pathname === "/login") {
    const url = req.nextUrl.clone()
    url.pathname = "/"
    return NextResponse.redirect(url)
  }

  return NextResponse.next()
}

export const config = {
  // Nao interceptar assets estaticos e API routes.
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api).*)"],
}
