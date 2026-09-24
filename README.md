# BuildGuard

**Control autonomous AI.** A deterministic guardrail layer that sits between your agent and the
outside world. Every tool call, payment, burst of activity or outgoing message is approved or
blocked *before* it happens.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Dependencies](https://img.shields.io/badge/runtime%20dependencies-0-brightgreen)
![Typing](https://img.shields.io/badge/typing-PEP%20561-blueviolet)

- **Zero dependencies.** Standard library only, so the attack surface stays as small as the package.
- **Zero latency.** Pure in-memory decisions, no network calls, no disk, no locks.
- **Deterministic.** Same action and same state always produce the same verdict.
- **Composable.** Built-in guardrails for the common cases, a two-method protocol for everything else.

## Install

```bash
pip install buildguard
```

## Quickstart

```python
from buildguard import BudgetGuard, Guard

guard = Guard(budget=BudgetGuard(max_transaction=50.0))
guard.validate({"type": "payment", "amount": 250.0})
# {'status': 'BLOCKED', 'reason': 'amount $250.00 exceeds the per-transaction limit $50.00', ...}
```

## The four guardrails

| Guardrail | Question it answers | State |
| --- | --- | --- |
| `BudgetGuard` | Is this payment inside the per-transaction and cumulative caps? | tracks spend |
| `RateLimitGuard` | Is the agent inside its call budget for the current window? | sliding window |
| `ToolGuard` | Is this tool on the allowlist, off the denylist, and permitted for the role? | stateless |
| `PiiGuard` | Does this text or payload contain cards, credentials, emails or phone numbers? | stateless |

Stack them into a firewall:

```python
from buildguard import BudgetGuard, Guard, PiiGuard, RateLimitGuard, ToolGuard

guard = Guard(
    budget=BudgetGuard(max_transaction=50.0, max_total=500.0),
    rate_limit=RateLimitGuard(max_calls=60, period_seconds=60.0),
    tools=ToolGuard(allowed={"search_web", "read_file"}, roles={"analyst": {"search_web"}}),
    pii=PiiGuard(),
)
```

Guardrails run in the order **tools → budget → rate limit → custom**, and the first one to block
decides the outcome. `ToolGuard` blocks dangerous tools such as `execute_command` and `drop_table`
out of the box.

## Two ways to evaluate an action

```python
guard.validate(action)                    # decision only, no state is committed
guard.validate_and_run(action, handler)   # decision, then commit and run the handler
```

`validate` is safe to call for previews and dry runs: it never charges a budget, never consumes a
rate-limit slot and never reaches your handler. `validate_and_run` commits the approved action to
every stateful guardrail before invoking the handler, and blocked actions are returned untouched —
the handler is not called.

Both return the same shape:

```python
{
    "status": "APPROVED",   # or "BLOCKED"
    "reason": "approved",
    "action": {...},        # the sanitized action
    "result": ...,          # only present when a handler ran
}
```

The `action` in the response is always a sanitized copy, so PII never travels back into your logs
or your agent's next prompt.

## Custom guardrails

A guardrail is any object with a `check(action) -> (allowed, reason)` method. Implement `commit(action)`
as well if the rule needs to account for approved actions.

```python
from datetime import datetime, timezone

from buildguard import BudgetGuard, Guard


class BusinessHoursRule:
    """Only lets payments through on weekdays during business hours in UTC."""

    def check(self, action):
        if action.get("type") != "payment":
            return True, ""
        moment = datetime.now(timezone.utc)
        if moment.weekday() < 5 and 9 <= moment.hour < 17:
            return True, ""
        return False, "payments run only on weekdays between 9:00 and 17:00 UTC"


guard = Guard(budget=BudgetGuard(max_transaction=500.0), guardrails=[BusinessHoursRule()])
```

See `examples/custom_guardrails.py` for a stateful rule that uses `commit`.

## Performance

Every decision is a handful of compiled-regex substitutions and in-memory comparisons, so a full
four-guardrail pass runs in well under a millisecond — far below the cost of the tool call it
protects. Measure it on your own hardware:

```bash
python -m timeit -s "
from buildguard import BudgetGuard, Guard, PiiGuard, RateLimitGuard, ToolGuard
guard = Guard(
    budget=BudgetGuard(max_transaction=50.0, max_total=500.0),
    rate_limit=RateLimitGuard(max_calls=10**6),
    tools=ToolGuard(allowed={'search_web'}),
    pii=PiiGuard(),
)
action = {'type': 'payment', 'amount': 25.0, 'tool': 'search_web', 'note': 'ping ops@example.com'}
" "guard.validate(action)"
```

## Architecture

```
buildguard/
├── pyproject.toml
├── src/buildguard/
│   ├── __init__.py            public API
│   ├── core.py                Guard gateway, Guardrail protocol
│   └── guardrails/
│       ├── budget.py          transaction and cumulative caps
│       ├── rate_limit.py      in-memory sliding window
│       ├── pii.py             pre-compiled redaction patterns
│       └── tools.py           allowlists, denylists, roles
├── tests/                     pytest suite, one module per guardrail
└── examples/
    ├── quickstart.py          all four guardrails end to end
    └── custom_guardrails.py   stateless and stateful custom rules
```

## Development

```bash
python -m venv venv
source venv/Scripts/activate        # Windows; use venv/bin/activate elsewhere
pip install -e ".[dev]"
pytest
```

## License

MIT
