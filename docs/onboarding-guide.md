# Meridian Analytics - Onboarding Guide

Last updated: January 2026

## Step 1: Create a workspace

After signing up, create a workspace from the dashboard. Workspace names must be
unique across your organization and cannot be changed after creation. Each
account may hold up to 25 workspaces.

## Step 2: Connect a data source

Meridian supports PostgreSQL, MySQL, Snowflake, BigQuery, and CSV upload.
Connections are read-only by design - Meridian never issues write statements
against a customer database.

For databases behind a firewall, allowlist the static egress addresses listed in
the security settings page. Meridian does not support SSH tunnelling.

## Step 3: Define your first metric

Metrics are defined in the metric editor using SQL. Every metric requires a name,
a time column, and an aggregation. Saved metrics are versioned; the previous ten
versions are retained and can be restored from the history panel.

## Step 4: Invite your team

Three roles are available:

- **Viewer** - read dashboards, cannot edit metrics
- **Editor** - create and modify metrics and dashboards
- **Admin** - manage billing, members, and data source connections

Invitations expire after 7 days. An account on the Free plan is limited to three
members.

## Typical timeline

Most teams complete onboarding within two hours. Connecting a warehouse behind a
firewall is the step that most often adds delay, usually because the allowlist
change needs approval from a network team.
