# Phase 2 — Data Flows

**Date:** 2026-04-14
**Project:** OneAI-Cortex v0.4.0
**Feature:** Google Connected Services — OAuth Token Management & Agent Integration

---

## Flow 1: Google Connect — OAuth Code Exchange

```
Frontend → POST /api/v1/connected-services/google/connect
  Headers: Authorization: Bearer <jwt>
  Body: { code: "4/0AfJohXl...", redirect_uri: "" }

  → Router: validate body (GoogleConnectRequest), authenticate user (JWT)
    → ConnectedServiceService.connect_google(user_id, code, redirect_uri)

      → Step 1: Exchange code for tokens
        → GoogleOAuthClient.exchange_code(code, "")
          → POST https://oauth2.googleapis.com/token
            Body: {
              code: "4/0AfJohXl...",
              client_id: GOOGLE_CLIENT_ID,
              client_secret: GOOGLE_CLIENT_SECRET,
              redirect_uri: "postmessage",
              grant_type: "authorization_code"
            }
          ← 200: {
              access_token: "ya29.a0AfB...",
              refresh_token: "1//0e...",
              expires_in: 3600,
              scope: "openid https://www.googleapis.com/auth/gmail.modify ..."
            }
        ← GoogleTokenResult(access_token, refresh_token, expires_in, scope)

      → Step 2: Fetch user info
        → GoogleOAuthClient.get_user_info("ya29.a0AfB...")
          → GET https://www.googleapis.com/oauth2/v2/userinfo
            Headers: Authorization: Bearer ya29.a0AfB...
          ← 200: { email: "jane@example.com", name: "Jane", picture: "..." }
        ← GoogleUserInfo(email, name, picture)

      → Step 3: Encrypt refresh token
        → self._encryption.encrypt("1//0e...")
        ← "gAAAAABm...Fernet-encrypted-token..."

      → Step 4: Upsert connection
        → self._repo.get_by_user_and_provider(user_id, "google")
        ← None (first connection)
        → self._repo.create({
            user_id: user_id,
            provider: "google",
            provider_email: "jane@example.com",
            refresh_token: "gAAAAABm...",  ← ENCRYPTED
            granted_scopes: "openid https://...gmail.modify https://...calendar",
            status: "active",
          })
        ← ConnectedService model

    ← ConnectedServiceResponse
  ← Return 201: ConnectedServiceResponse
```

---

## Flow 2: Check Google Connection Status

```
Frontend → GET /api/v1/connected-services/google/scopes
  Headers: Authorization: Bearer <jwt>

  → Router: authenticate user (JWT)
    → ConnectedServiceService.get_google_scopes(user_id)
      → self._repo.get_by_user_and_provider(user_id, "google")

      → Case A: Connection found
        ← ConnectedService(provider_email="jane@example.com", granted_scopes="openid gmail.modify calendar", status="active")
        → Parse scopes string → list
        ← GoogleScopesResponse(connected=True, scopes=[...], email="jane@example.com")

      → Case B: No connection found
        ← None
        ← GoogleScopesResponse(connected=False, scopes=[], email=None)

  ← Return 200: GoogleScopesResponse

  Frontend receives response:
    → If connected=True: show "Connected" badge, populate scope toggles
    → If connected=False: show "Connect Google Account" button
```

---

## Flow 3: Fresh Access Token for Agent Runtime

```
Agent Tool → GET /api/v1/connected-services/google/token
  Headers: Authorization: Bearer <jwt>

  → Router: authenticate user (JWT)
    → ConnectedServiceService.get_google_token(user_id)

      → Step 1: Load connection
        → self._repo.get_by_user_and_provider(user_id, "google")
        ← ConnectedService(refresh_token="gAAAAABm...", granted_scopes="...", status="active")
        → If None: raise EntityNotFoundError → 404

      → Step 2: Decrypt refresh token
        → self._encryption.decrypt("gAAAAABm...")
        ← "1//0e..."  ← PLAINTEXT refresh token

      → Step 3: Refresh access token at Google
        → GoogleOAuthClient.refresh_access_token("1//0e...")
          → POST https://oauth2.googleapis.com/token
            Body: {
              refresh_token: "1//0e...",
              client_id: GOOGLE_CLIENT_ID,
              client_secret: GOOGLE_CLIENT_SECRET,
              grant_type: "refresh_token"
            }

          → Case A: Success
            ← 200: { access_token: "ya29.new...", expires_in: 3600, scope: "..." }
            ← GoogleTokenResult(access_token="ya29.new...", expires_in=3600, scope="...")

          → Case B: Token revoked
            ← 400: { error: "invalid_grant", error_description: "Token has been revoked" }
            → Update connection status to "revoked"
            → raise ServiceError("Google connection revoked") → 410 Gone

      ← GoogleTokenResponse(access_token="ya29.new...", expires_in=3600, scopes=[...])
  ← Return 200: GoogleTokenResponse

  Agent tool receives token:
    → Use access_token to call Google API
    → Example: POST gmail.googleapis.com/v1/users/me/messages/send
      Headers: Authorization: Bearer ya29.new...
```

---

## Flow 4: Reconnect — Update Scopes

```
Frontend → POST /api/v1/connected-services/google/connect
  Headers: Authorization: Bearer <jwt>
  Body: { code: "4/0ANewCode...", redirect_uri: "" }

  → Same as Flow 1, but at Step 4:
    → self._repo.get_by_user_and_provider(user_id, "google")
    ← ConnectedService(id=existing_uuid, ...)  ← EXISTS

    → self._repo.update(existing_uuid, {
        refresh_token: "gAAAAABn...",  ← NEW encrypted token
        granted_scopes: "openid gmail.modify calendar drive.readonly",  ← UPDATED scopes
        provider_email: "jane@example.com",
        status: "active",
      })
    ← Updated ConnectedService

  ← Return 200: ConnectedServiceResponse (status 200, not 201)
```

---

## Flow 5: Disconnect Google

```
Frontend → DELETE /api/v1/connected-services/google
  Headers: Authorization: Bearer <jwt>

  → Router: authenticate user (JWT)
    → ConnectedServiceService.disconnect_google(user_id)
      → self._repo.get_by_user_and_provider(user_id, "google")
      ← ConnectedService(id=uuid, ...)
      → If None: raise EntityNotFoundError → 404
      → self._repo.delete(uuid)  ← HARD DELETE (tokens should not be retained)
      ← True
    ← None
  ← Return 204: No Content

  Frontend receives 204:
    → Update UI to show "Disconnected"
    → Show "Connect Google Account" button
```

---

## Flow Summary

| # | Flow | Direction | Key Operation | Token State |
|---|------|-----------|---------------|-------------|
| 1 | Connect | Frontend → Cortex → Google | Code exchange + store | Plaintext → Encrypted in DB |
| 2 | Check status | Frontend → Cortex | DB lookup | No token access needed |
| 3 | Get token | Agent → Cortex → Google | Decrypt + refresh | Encrypted → Decrypted → Google → Fresh access token |
| 4 | Reconnect | Frontend → Cortex → Google | Code exchange + update | Old encrypted → New encrypted |
| 5 | Disconnect | Frontend → Cortex | Hard delete | Encrypted → Deleted |
