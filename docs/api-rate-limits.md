# Meridian Analytics - API Rate Limits

Last updated: June 2026

## Per-plan limits

| Plan | Requests per minute | Requests per day | Burst |
| --- | --- | --- | --- |
| Free | 20 | 5,000 | 40 |
| Starter | 120 | 100,000 | 240 |
| Growth | 600 | 1,000,000 | 1,200 |
| Enterprise | Negotiated | Negotiated | Negotiated |

Limits are enforced per API key, not per account. An account with three keys on
the Starter plan therefore has an effective ceiling of 360 requests per minute.

## What happens when you exceed a limit

The API returns HTTP 429 with a `Retry-After` header expressed in seconds.
Clients should back off exponentially. Repeated violations within a single hour
cause the key to be throttled to 10% of its normal limit for 15 minutes.

## Reading your current usage

Every response includes three headers:

- `X-RateLimit-Limit` - the ceiling for the current window
- `X-RateLimit-Remaining` - requests left in the current window
- `X-RateLimit-Reset` - Unix timestamp when the window resets

## Requesting an increase

Growth and Enterprise customers can request a temporary increase for scheduled
batch jobs. Submit the request at least three business days in advance through
the support portal. Increases are granted for a maximum of 72 hours.
