from buildguard import BudgetGuard, Guard, PiiGuard, RateLimitGuard, ToolGuard

guard = Guard(
    budget=BudgetGuard(max_transaction=50.0, max_total=200.0),
    rate_limit=RateLimitGuard(max_calls=5, period_seconds=60.0),
    tools=ToolGuard(allowed={"search_web", "read_file"}),
    pii=PiiGuard(),
)

ACTIONS = [
    {"type": "tool_call", "tool": "search_web", "query": "python protocols"},
    {"type": "payment", "amount": 25.0, "receipt_email": "ops@example.com"},
    {"type": "payment", "amount": 250.0, "note": "annual plan"},
    {"type": "tool_call", "tool": "execute_command", "command": "rm -rf /"},
    {"type": "payment", "amount": 30.0, "note": "renewal for sk-7c1f9a2b4d6e8f01"},
]


def main() -> None:
    for action in ACTIONS:
        decision = guard.validate_and_run(action)
        print(f"{decision['status']:>7}  {decision['reason']}")
        if decision["action"] != action:
            print(f"         action sanitized to {decision['action']}")


if __name__ == "__main__":
    main()
