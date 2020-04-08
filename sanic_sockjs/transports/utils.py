import http.cookies
from datetime import datetime, timedelta


CACHE_CONTROL = "no-store, no-cache, no-transform, must-revalidate, max-age=0"


def cors_headers(headers, nocreds=False):
    origin = headers.get('Origin', "*")
    cors = (('Access-Control-Allow-Origin', origin),)

    ac_headers = headers.get('Access-Control-Request-Headers')
    if ac_headers:
        cors += (('Access-Control-Allow-Headers', ac_headers),)

    if origin != "*":
        return cors + (('Access-Control-Allow-Credentials', "true"),)
    else:
        return cors


def session_cookie(request):
    cookie = request.cookies.get("JSESSIONID", "dummy")
    cookies = http.cookies.SimpleCookie()
    cookies["JSESSIONID"] = cookie
    cookies["JSESSIONID"]["path"] = "/"
    return (('Set-Cookie', cookies["JSESSIONID"].output(header="")[1:]),)


td365 = timedelta(days=365)
td365seconds = str(
    (td365.microseconds + (td365.seconds + td365.days * 24 * 3600) * 10 ** 6) // 10 ** 6
)


def cache_headers():
    d = datetime.now() + td365
    return (
        ('Access-Control-Max-Age', td365seconds),
        ('Cache-Control', "max-age=%s, public" % td365seconds),
        ('Expires', d.strftime("%a, %d %b %Y %H:%M:%S")),
    )
