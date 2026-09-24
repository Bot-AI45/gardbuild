from gardbuild import PiiGuard


def test_masks_credit_cards():
    guard = PiiGuard()
    assert guard.scrub("card 4242 4242 4242 4242") == "card [REDACTED]"
    assert guard.scrub("card 4242424242424242") == "card [REDACTED]"


def test_masks_email_addresses():
    guard = PiiGuard()
    assert guard.scrub("ping ops@example.com now") == "ping [REDACTED] now"


def test_masks_phone_numbers():
    guard = PiiGuard()
    assert guard.scrub("call +1 (555) 123-4567") == "call [REDACTED]"
    assert guard.scrub("call 5551234567") == "call [REDACTED]"


def test_masks_api_keys():
    guard = PiiGuard()
    assert guard.scrub("key sk-9f2b71c4d8e5a6b7c") == "key [REDACTED]"


def test_masks_secrets():
    guard = PiiGuard()
    assert guard.scrub("api_key=4f9a2b7c8d1e6f3a") == "[REDACTED]"


def test_scrubs_nested_structures():
    guard = PiiGuard()
    payload = {"user": {"email": "a@b.co"}, "notes": ["call 5551234567", 7]}
    assert guard.scrub(payload) == {
        "user": {"email": "[REDACTED]"},
        "notes": ["call [REDACTED]", 7],
    }


def test_scrubs_tuples():
    guard = PiiGuard()
    assert guard.scrub(("ops@example.com",)) == ("[REDACTED]",)


def test_supports_a_custom_mask():
    guard = PiiGuard(mask="<hidden>")
    assert guard.scrub("ops@example.com") == "<hidden>"


def test_supports_per_rule_masks():
    guard = PiiGuard(masks={"email": "<email>"})
    assert guard.scrub("ops@example.com") == "<email>"
    assert guard.scrub("5551234567") == "[REDACTED]"


def test_supports_extra_patterns():
    guard = PiiGuard(patterns={"employee_id": r"\bEMP-\d{5}\b"})
    assert guard.scrub("EMP-12345 filed a request") == "[REDACTED] filed a request"


def test_leaves_clean_input_alone():
    guard = PiiGuard()
    assert guard.scrub("summarise the quarterly report") == "summarise the quarterly report"


def test_leaves_non_string_values_alone():
    guard = PiiGuard()
    assert guard.scrub(42) == 42
    assert guard.scrub(None) is None
