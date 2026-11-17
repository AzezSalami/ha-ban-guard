# Security policy

## Supported versions

Only the latest release receives fixes. Updates are published through HACS as soon as they are released.

## Reporting a vulnerability

Please **do not open a public issue**. Report it privately through GitHub's
[private vulnerability reporting](https://github.com/AzezSalami/ha-ban-guard/security/advisories/new).

Include the Ban Guard and Home Assistant versions, the steps to reproduce, and the impact. You can expect an acknowledgement within 7 days. Once a fix is released, we will publish a coordinated advisory and credit you if you wish.

## Scope and design notes

Ban Guard is a defence-in-depth tool, not a firewall. It blocks requests inside Home Assistant's HTTP server. Use a reverse proxy or firewall for network-level protection.

- Every websocket command and action requires an administrator. The only unauthenticated HTTP resource is the static panel bundle.
- The lockout guard refuses bans covering loopback, the host's own addresses, the Supervisor network, trusted proxies, recently used administrator addresses and the requester's address.
- Bans use the client address that Home Assistant resolves, so `use_x_forwarded_for` and `trusted_proxies` must be configured correctly behind a reverse proxy. With a misconfigured proxy, all clients share the proxy's address. Ban Guard protects trusted proxies from being banned for this reason.
- The Nginx Proxy Manager password is encrypted (Fernet) with a key kept in `.storage/ban_guard.secret`, separate from the config entry. Anyone with full access to `.storage` can decrypt it.
- The activity log never stores query strings or credentials. Secret URL segments (webhook ids, ingress tokens, long token-like segments) are redacted. Diagnostics replace every address with a one-way token.
- The integration has no third-party Python requirements. The GeoIP database reader is a small in-tree implementation (`mmdb.py`). The only minified file is the built panel bundle, which CI rebuilds and compares byte for byte.
- Releases include a SHA-256 checksum and a GitHub build provenance attestation.
