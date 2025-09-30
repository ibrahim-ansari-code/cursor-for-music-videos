# Intuit OAuth 2.0 Authentication Switch — Implementation Plan (Words Only)

## Objective

Replace the current Apideck-based connection flow with a direct Intuit QuickBooks Online OAuth 2.0 flow while preserving existing frontend endpoint contracts and without changing downstream sync logic yet. This phase establishes a first‑party token relationship and prepares us for subsequent API migration.

### Scope (Phase 1 Only)

- Authentication and token lifecycle for Intuit (authorization code + refresh).
- Minimal backend and frontend changes limited to connect, callback/initial‑sync, and status.
- Database additions for securely storing Intuit tokens and metadata.
- No changes to resource synchronization (customers, invoices, payments, expenses) in this phase.

### Constraints & Requirements

- Use Supabase CLI migrations (database branching) for schema changes; do not use Alembic for this work.
- Keep existing routes stable for the frontend; connect should continue returning a redirect URL.
- Store tokens encrypted at rest and handle refresh seamlessly.
- Production keys and redirect URIs must match Intuit app configuration exactly.

### High‑Level Architecture Changes

- Introduce a provider‑selection mechanism so the backend can serve either Apideck or Intuit flows during rollout.
- Add an Intuit OAuth helper module to encapsulate authorization URL creation, token exchange, refresh, and expiry calculations.
- Extend the `integrations` table to include Intuit‑specific fields (realm/company id, encrypted tokens, expirations, granted scope, and optional cached company name).
- Preserve existing circuit‑breaker, retry, and structured logging patterns; tag logs distinctly for Intuit.

### Backend Plan

1. Configuration
   - Add configuration keys for Intuit client id, client secret, environment (sandbox/production), redirect URI, and a minor version setting for future API calls.
   - Add a single provider flag to enable a safe toggle between Apideck and Intuit during rollout.

2. Database
   - Extend `integrations` to store: realm id, encrypted access token, encrypted refresh token, access/refresh expiration timestamps, granted scope string, and optional cached company name.
   - Use Supabase CLI to generate a migration in `supabase/migrations` via a database branch and commit the resulting SQL file(s).

3. OAuth Flow
   - Connect endpoint: when provider is Intuit, generate the Intuit authorization URL with required scopes and a cryptographically secure state value; persist state (and a short TTL) in integration metadata; return the URL to the frontend.
   - Callback/initial‑sync endpoint: accept authorization code and realm id; verify state; exchange the code for tokens; store encrypted tokens and expirations; mark the integration connected and record `connected_at`.
   - Status endpoint: when provider is Intuit, report `connected` based on the presence and validity of tokens; include connection timestamps and cached company name if available.

4. Security
   - Enforce state verification to mitigate CSRF.
   - Encrypt tokens before persistence and never log sensitive values.
   - Validate redirect URIs strictly against configuration; reject mismatches.

5. Observability
   - Use structured logging with a distinct `service` tag for Intuit.
   - Add performance spans around authorization URL creation and token exchange.

### Frontend Plan (Minimal)

- Preserve existing initiation via the connect route and redirect handling.
- Upon return from Intuit, read the `code`, `realmId`, and `state` parameters from the URL and post them to the backend’s initial‑sync/callback endpoint.
- Keep user experience unchanged (status refresh and success/error toasts remain as today).

### Supabase Migration Plan

- Use Supabase’s database branching workflow to create a development branch for the migration.
- Generate a migration that adds the new Intuit columns to the `integrations` table and any necessary indexes or constraints.
- Test against the local Supabase instance; validate creation, update, and query paths for the new fields.
- Commit the migration files under `supabase/migrations` alongside a brief description of the change.

### Rollout Strategy

- Ship behind a provider flag with the Intuit path disabled by default.
- Enable in a development environment first; validate token issuance, storage, refresh, and status reporting.
- Progressively enable in staging and then production, monitoring error rates and logs; maintain the ability to revert to Apideck instantly.

### Testing Strategy

- Unit tests for: authorization URL generation, state persistence/validation, token exchange parsing, token refresh, encryption/decryption, and expiration handling.
- Integration tests: end‑to‑end flow across connect → redirect → initial‑sync/callback → status.
- Negative tests: invalid state, expired code, invalid redirect URI, credential mismatch, and refresh token rotation scenarios.

### Acceptance Criteria

- Users can initiate connection and complete Intuit OAuth successfully.
- Tokens are stored encrypted with correct expirations and can be refreshed without user action.
- Status endpoint accurately reflects connection state for Intuit.
- No changes to existing data synchronization behavior in this phase.
- Migration is reproducible via Supabase CLI and checked in under `supabase/migrations`.

### Risks & Mitigations

- Redirect URI mismatch: double‑check app configuration and environment‑specific URIs.
- Token refresh nuances: handle rotation semantics and expiry windows conservatively; add retry with backoff and proper error surfaces.
- Partial rollout complexity: keep the provider flag simple and well‑documented; log provider choice per request.

### Timeline & Sequencing (Suggested)

1. Planning and configuration scaffolding.
2. Supabase migration creation and validation in local branch.
3. OAuth helper module and connect/initial‑sync/status path for Intuit (behind flag).
4. Tests and documentation.
5. Staged enablement and monitoring; retain rollback path.

### Deliverables for this Phase

- New Supabase migration adding Intuit fields to `integrations`.
- Backend configuration keys and provider toggle.
- Auth endpoints supporting Intuit (connect and initial‑sync/callback) with secure token storage.
- Minimal frontend adjustment to pass returned parameters to the backend.
- Tests, logs, and concise operator notes.
