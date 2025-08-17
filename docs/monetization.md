# Monetization Plan

This document outlines a tiered pricing model that preserves the local-first ethos while offering paid value for power users and enterprises.

## Tiers

### Personal (Free)
- GUI included
- Local-only (Ollama) models
- No hosted services; completely offline-capable

Why: Community edition to grow user base and word-of-mouth without API costs.

### Pro (~$29/month)
- Everything in Personal
- Cloud providers via API keys (OpenAI, Anthropic, Google)
- Save and manage multiple schemas (cloud sync)
- Project history of past runs
- Access to hosted API

Why: Professionals who prefer the UI but want top-tier models and convenience.

### Business (Annual License)
- Self-hosted Docker (GUI + server)
- Annual flat fee (e.g., $1,500/year)
- SSO/SAML optional add-on

Why: Targets companies with strict data policies that need a managed internal tool.

## Technical Gates
- Feature flags by tier (provider gating, save/history/API)
- Auth and billing integration (e.g., Stripe)
- Minimal SaaS backend for sync/history; Docker packaging for Business
- License checks for self-hosted deployments

## Next Steps
- Define feature flags and config
- Spike a minimal backend (FastAPI + Postgres) for schemas/history
- Add auth/billing flow
- Create Docker packaging and licensing for Business
