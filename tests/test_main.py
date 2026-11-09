import asyncio
from types import SimpleNamespace

import pytest

import main


class FakeDocuments:
    """Record search parameters and return a fixed response without network access."""

    def __init__(self):
        """Initialize the recorded search parameters."""
        self.last_params = None

    def search(self, params):
        """Record the supplied parameters and return fake search hits."""
        self.last_params = params
        return {"hits": [{"id": 1}]}


@pytest.fixture
def fake_documents(monkeypatch):
    """Replace the Typesense client for one test and restore it automatically."""
    documents = FakeDocuments()
    client = SimpleNamespace(collections={"demo": SimpleNamespace(documents=documents)})
    monkeypatch.setattr(main, "typesense_client", client)
    return documents


@pytest.mark.parametrize(
    "search_arguments, expected_query",
    [
        pytest.param({"query": "sunshine"}, "sunshine", id="query-alias"),
        pytest.param({"q": "sunshine"}, "sunshine", id="q-parameter"),
        pytest.param(
            {"q": "sunshine", "query": "sunshine"},
            "sunshine",
            id="matching-aliases",
        ),
        pytest.param({"q": ""}, "", id="empty-query"),
    ],
)
def test_search_forwards_query_and_returns_hits(
    fake_documents, search_arguments, expected_query
):
    """Accept either query parameter and return the Typesense response."""
    result = asyncio.run(main.search("demo", **search_arguments))

    assert result["hits"] == [{"id": 1}]
    assert fake_documents.last_params["q"] == expected_query


@pytest.mark.parametrize(
    "search_arguments, expected_message",
    [
        pytest.param(
            {},
            "A search term is required. Provide 'q' or 'query'.",
            id="missing-query",
        ),
        pytest.param(
            {"q": "sunshine", "query": "rain"},
            "Use either 'q' or 'query', not both with different values.",
            id="conflicting-aliases",
        ),
    ],
)
def test_search_rejects_invalid_queries_before_calling_typesense(
    fake_documents, search_arguments, expected_message
):
    """Reject missing or conflicting queries without contacting Typesense."""
    with pytest.raises(ValueError) as error:
        asyncio.run(main.search("demo", **search_arguments))

    assert str(error.value) == expected_message
    assert fake_documents.last_params is None
