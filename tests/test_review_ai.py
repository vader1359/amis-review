import json

import httpx
import pytest
from web import review_ai


@pytest.fixture
def configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PSI_AI_BASE_URL", "http://127.0.0.1:20128/v1")
    monkeypatch.setenv("PSI_AI_MODEL", "test-model")
    monkeypatch.setenv("PSI_AI_API_KEY", "private-test-key")


def _mock(monkeypatch: pytest.MonkeyPatch, handler: object) -> None:
    original = httpx.Client
    monkeypatch.setattr(
        review_ai.httpx,
        "Client",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )


def test_disabled_without_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PSI_AI_BASE_URL", raising=False)
    assert review_ai.ai_status() == {"enabled": False, "model": None}
    assert review_ai.explain_review({})["status"] == "unavailable"


def test_minimized_request_and_cited_response(
    configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "http://127.0.0.1:20128/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer private-test-key"
        payload = json.loads(request.content)
        assert payload["stream"] is False
        assert payload["max_tokens"] == 1800
        text = payload["messages"][1]["content"]
        for secret in ("Alice", "address", "PHONE", "ORDER-PRIVATE", "SKU-PRIVATE"):
            assert secret not in text
        assert json.loads(text)[0]["evidence"] == {"expected": 4, "actual": 3}
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "explanations": [
                                        {
                                            "evidence_id": "e001",
                                            "explanation": "Giả thuyết: chênh 1.",
                                            "exclude": True,
                                        },
                                        {
                                            "evidence_id": "invented",
                                            "explanation": "Sai",
                                        },
                                        {"evidence_id": "e001", "explanation": "Trùng"},
                                    ],
                                }
                            )
                        }
                    }
                ]
            },
        )

    _mock(monkeypatch, handler)
    result = review_ai.explain_review(
        {
            "mismatches": [
                {
                    "id": "ORDER-PRIVATE",
                    "order_id": "ORDER-PRIVATE",
                    "sku": "SKU-PRIVATE",
                    "issue": "quantity_mismatch",
                    "customer_name": "Alice",
                    "explanation": "Alice address PHONE",
                    "evidence": {
                        "expected": 4,
                        "actual": 3,
                        "customer": "Alice",
                        "address": "secret",
                    },
                }
            ]
        }
    )
    assert result["status"] == "ok"
    assert result["explanations"] == [
        {
            "evidence_id": "ORDER-PRIVATE",
            "explanation": "Giả thuyết: chênh 1.",
            "hypothesis": True,
        }
    ]
    assert review_ai.ai_status() == {"enabled": True, "model": "test-model"}


@pytest.mark.parametrize(
    ("status", "body"),
    [
        (401, b"private-test-key"),
        (503, b"upstream error"),
        (200, b"not json"),
        (200, b"data: SSE unexpected"),
        (200, b"x" * 64001),
        (200, b'{"choices": []}'),
    ],
)
def test_failures_sanitized(
    configured: None, monkeypatch: pytest.MonkeyPatch, status: int, body: bytes
) -> None:
    _mock(monkeypatch, lambda request: httpx.Response(status, content=body))
    result = review_ai.explain_review({"items": [{"id": "x", "count": 1}]})
    assert result == {
        "status": "unavailable",
        "explanations": [],
        "disclaimer": review_ai.DISCLAIMER,
    }


def test_timeout_sanitized(configured: None, monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        msg = "credential private-test-key"
        raise httpx.ReadTimeout(msg, request=request)

    _mock(monkeypatch, handler)
    assert (
        review_ai.explain_review({"items": [{"id": "x", "count": 1}]})["status"]
        == "unavailable"
    )


def test_input_limits() -> None:
    items, refs = review_ai._prepare(
        {
            "changes": [
                {
                    "id": str(index),
                    "kind": "changed",
                    "before": {"quantity": 10**1000},
                    "after": {"quantity": 1, "customer": "PRIVATE"},
                }
                for index in range(100)
            ]
        }
    )
    assert len(items) == len(refs) == 30
    assert "before" not in items[0]
    assert items[0]["after"] == {"quantity": 1}


def test_engine_templates_and_numeric_fields() -> None:
    items, _ = review_ai._prepare(
        {
            "mismatches": [
                {
                    "id": "a",
                    "issue": "Revenue exceeds approved CRM line",
                    "evidence": "CRM qty=2, net=1,000; Revenue qty=3, net=1,500",
                },
                {
                    "id": "b",
                    "issue": "COGS > NET REV SOLD",
                    "evidence": "NET REV SOLD=200; COGS=300; quantity=2; ledger row 42",
                },
                {
                    "id": "c",
                    "issue": "SKU not found in Product Master",
                    "evidence": (
                        "Inventory row 4; quantity=2; value=100; warehouse=PRIVATE"
                    ),
                },
                {
                    "id": "unknown",
                    "issue": "Alice needs a refund",
                    "evidence": "PRIVATE",
                },
            ],
            "changes": [
                {
                    "id": "d",
                    "kind": "changed",
                    "before": {
                        "crm_quantity": 2,
                        "revenue_net": 1000,
                        "state": "Hoàn thành",
                        "customer": "Alice",
                        "approval_status": "Private custom value",
                    },
                }
            ],
        }
    )
    assert len(items) == 4
    assert items[0]["evidence"] == {
        "crm_quantity": 2,
        "crm_net": 1000,
        "revenue_quantity": 3,
        "revenue_net": 1500,
    }
    assert items[1]["evidence"] == {"revenue_net": 200, "cogs": 300, "quantity": 2}
    assert items[2]["evidence"] == {"quantity": 2, "amount": 100}
    assert items[3]["before"] == {
        "crm_quantity": 2,
        "revenue_net": 1000,
        "state": "Hoàn thành",
    }
    assert "PRIVATE" not in json.dumps(items)


def test_insufficient_evidence_does_not_call_provider(
    configured: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(request: httpx.Request) -> httpx.Response:
        pytest.fail("Insufficient evidence must not call a provider")

    _mock(monkeypatch, forbidden)
    assert review_ai.explain_review({"items": [{"id": "x"}]})["status"] == "unavailable"


@pytest.mark.parametrize(
    "base",
    [
        "file:///secret",
        "https://user:pass@test/v1",
        "http://[invalid",
        "https://test/v1?secret=1",
    ],
)
def test_invalid_configuration(
    configured: None, monkeypatch: pytest.MonkeyPatch, base: str
) -> None:
    monkeypatch.setenv("PSI_AI_BASE_URL", base)
    assert review_ai.ai_status()["enabled"] is False
