# Cloudflare

Hostname: `eoc.mbfdhub.com`.

- Proxied DNS CNAME points to the existing GMKtec Tunnel target.
- The existing remotely managed tunnel gets one ingress rule for
  `eoc.mbfdhub.com -> http://localhost:8220`, inserted before the catch-all.
- Existing tunnel routes are preserved byte-for-byte.
- A self-hosted Access application protects the hostname using the approved MBFD
  identity policy. The application is not deliberately exposed without Access.
- TLS terminates at Cloudflare; the tunnel reaches a localhost-only origin.

Validation:

```bash
curl -I https://eoc.mbfdhub.com
# Unauthenticated request must redirect to or return the Cloudflare Access flow.
curl --fail http://127.0.0.1:8220/health/live
ss -lntp | grep 8220
```

Cloudflare API tokens, tunnel credentials, Access identities, and policy email
values are intentionally omitted. Changes are made by immutable account/zone/
tunnel IDs discovered from the API, never guessed.
