# Phase 2 — Interface Design

**Date:** 2026-04-14
**Project:** OneAI-Cortex v0.4.0
**Feature:** Google Connected Services — OAuth Token Management & Agent Integration

---

## 1. API Contracts

### POST /api/v1/connected-services/google/connect — Exchange Auth Code

Exchange a Google authorization code for tokens. Creates or updates the user's Google connection.

**Headers:** `Authorization: Bearer <jwt>`

**Request Body:**
```json
{
  "code": "4/0AfJohXl...",
  "redirect_uri": ""
}
```

**Response:** `201 Created` (new connection) or `200 OK` (updated)
```json
{
  "id": "uuid",
  "provider": "google",
  "provider_email": "jane@example.com",
  "status": "active",
  "granted_scopes": [
    "openid",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
  ],
  "created_at": "2026-04-14T12:00:00Z",
  "updated_at": "2026-04-14T12:00:00Z"
}
```

**Error Responses:**
- `400` — Invalid or expired authorization code
- `401` — JWT auth failed
- `502` — Google token exchange failed (Google API unreachable)

**Internal Flow:**
1. Call `GoogleOAuthClient.exchange_code(code, redirect_uri)` → get `access_token`, `refresh_token`, `scope`
2. Call `GoogleOAuthClient.get_user_info(access_token)` → get `email`
3. Encrypt `refresh_token` via `SecretEncryption.encrypt()`
4. Upsert `connected_services` row (user_id + provider = google)
5. Return `ConnectedServiceResponse`

---

### GET /api/v1/connected-services — List All Connections

**Headers:** `Authorization: Bearer <jwt>`

**Response:** `200 OK`
```json
{
  "items": [
    {
      "id": "uuid",
      "provider": "google",
      "provider_email": "jane@example.com",
      "status": "active",
      "granted_scopes": [
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/calendar"
      ],
      "created_at": "2026-04-14T12:00:00Z",
      "updated_at": "2026-04-14T12:00:00Z"
    }
  ],
  "total": 1
}
```

If no connections: `{ "items": [], "total": 0 }`

---

### GET /api/v1/connected-services/google/scopes — Google Connection Status

**Headers:** `Authorization: Bearer <jwt>`

**Response:** `200 OK` (connected)
```json
{
  "connected": true,
  "scopes": [
    "openid",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
  ],
  "email": "jane@example.com"
}
```

**Response:** `200 OK` (not connected)
```json
{
  "connected": false,
  "scopes": [],
  "email": null
}
```

---

### GET /api/v1/connected-services/google/token — Fresh Access Token

Returns a fresh Google access token by refreshing the stored refresh token. Used by agent runtime during tool execution.

**Headers:** `Authorization: Bearer <jwt>`

**Response:** `200 OK`
```json
{
  "access_token": "ya29.a0AfB_byB...",
  "expires_in": 3600,
  "scopes": [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar"
  ]
}
```

**Error Responses:**
- `404` — No Google connection for this user
- `410 Gone` — Refresh token revoked (user revoked access at Google). Connection status updated to `revoked`.
- `502` — Google token refresh failed (Google API unreachable)

**Internal Flow:**
1. Load `ConnectedService` by (user_id, provider="google")
2. Decrypt `refresh_token` via `SecretEncryption.decrypt()`
3. Call `GoogleOAuthClient.refresh_access_token(refresh_token)` → get fresh `access_token`, `expires_in`
4. If Google returns `400 invalid_grant`: update status to `revoked`, return 410
5. Return `GoogleTokenResponse`

---

### DELETE /api/v1/connected-services/google — Disconnect

**Headers:** `Authorization: Bearer <jwt>`

**Response:** `204 No Content`

**Error Responses:**
- `404` — No Google connection to disconnect

**Internal Flow:**
1. Load `ConnectedService` by (user_id, provider="google")
2. Hard-delete the row (tokens should not be retained after disconnect)

---

## 2. Service Interface

### ConnectedServiceService

```python
class ConnectedServiceService:
    def __init__(
        self,
        repo: ConnectedServiceRepository,
        google_client: GoogleOAuthClient,
        encryption: SecretEncryption,
    ) -> None: ...

    async def connect_google(
        self, user_id: UUID, code: str, redirect_uri: str
    ) -> ConnectedServiceResponse:
        """Exchange auth code for tokens, store encrypted connection."""

    async def get_google_scopes(
        self, user_id: UUID
    ) -> GoogleScopesResponse:
        """Get Google connection status and granted scopes."""

    async def get_google_token(
        self, user_id: UUID
    ) -> GoogleTokenResponse:
        """Get fresh Google access token from stored refresh token."""

    async def list_connections(
        self, user_id: UUID
    ) -> list[ConnectedServiceResponse]:
        """List all connected services for a user."""

    async def disconnect_google(
        self, user_id: UUID
    ) -> None:
        """Remove Google connection and stored tokens."""
```

---

## 3. Repository Interface

### ConnectedServiceRepository

```python
class ConnectedServiceRepository:
    def __init__(self, session: AsyncSession) -> None: ...

    async def create(self, data: dict[str, Any]) -> ConnectedService:
        """Create a new connected service record."""

    async def get_by_user_and_provider(
        self, user_id: UUID, provider: str
    ) -> ConnectedService | None:
        """Get a connection by user + provider. Returns None if not found."""

    async def update(
        self, service_id: UUID, data: dict[str, Any]
    ) -> ConnectedService | None:
        """Update a connected service. Returns None if not found."""

    async def list_by_user(self, user_id: UUID) -> list[ConnectedService]:
        """List all connected services for a user."""

    async def delete(self, service_id: UUID) -> bool:
        """Hard-delete a connected service. Returns True if found."""
```

---

## 4. Infrastructure Interface

### GoogleOAuthClient

```python
@dataclass(frozen=True, slots=True)
class GoogleTokenResult:
    access_token: str
    refresh_token: str | None
    expires_in: int
    scope: str  # space-separated scope string

@dataclass(frozen=True, slots=True)
class GoogleUserInfo:
    email: str
    name: str | None
    picture: str | None

class GoogleOAuthClient:
    def __init__(
        self, client_id: str, client_secret: str, timeout: float = 10.0
    ) -> None: ...

    async def exchange_code(
        self, code: str, redirect_uri: str
    ) -> GoogleTokenResult:
        """Exchange authorization code for tokens at Google's token endpoint."""

    async def refresh_access_token(
        self, refresh_token: str
    ) -> GoogleTokenResult:
        """Get a fresh access token using a stored refresh token."""

    async def get_user_info(
        self, access_token: str
    ) -> GoogleUserInfo:
        """Fetch user email/name/picture from Google's userinfo endpoint."""
```

---

## 5. Schema Definitions

### Request Schemas

```python
class GoogleConnectRequest(BaseModel):
    """Request body for exchanging a Google authorization code."""
    code: str = Field(..., min_length=1, description="Google authorization code")
    redirect_uri: str = Field(default="", description="Redirect URI used in OAuth flow")

```

### Response Schemas

```python
class ConnectedServiceResponse(BaseModel):
    """Connected service in API responses."""
    id: UUID
    provider: str
    provider_email: str | None
    status: str
    granted_scopes: list[str]
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}

class GoogleScopesResponse(BaseModel):
    """Google connection status and granted scopes."""
    connected: bool
    scopes: list[str]
    email: str | None

class GoogleTokenResponse(BaseModel):
    """Fresh Google access token for agent runtime."""
    access_token: str
    expires_in: int
    scopes: list[str]

class ConnectedServiceListResponse(BaseModel):
    """Paginated list of connected services."""
    items: list[ConnectedServiceResponse]
    total: int
```
