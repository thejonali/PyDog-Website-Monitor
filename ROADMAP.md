# PyDog Website Monitor Roadmap

This file is tracked intentionally. It is product and engineering direction that should be visible to reviewers and contributors, not local scratch state.

## Highest-Value Additions

1. **Reliable service runtime**
   - Run the monitor as a long-lived service with graceful shutdown, structured logs, Docker support, health-oriented exit behavior, and clear config precedence.

2. **First-class test and CI coverage**
   - Keep migrations, configuration loading, monitoring decisions, and notification routing covered by automated tests in GitHub Actions.

3. **Durable data model and migrations**
   - Move schema changes through explicit migrations, add constraints/indexes, and preserve upgrade paths for existing SQLite installs.

4. **Alert quality and incident state**
   - Add retry policy, alert deduplication, recovery notifications, configurable thresholds, and an incident lifecycle so users are not spammed on every failed check.

5. **Operational UX**
   - Add a minimal web/API surface for status, recent checks, integration health, and configuration validation while keeping the CLI useful for local administration.
