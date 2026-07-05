import json

import httpx
import pytest

from research_lens.ollama import OllamaResponseError, generate_ollama_sql


def test_generate_ollama_sql_calls_local_chat_api() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert request.url == "http://localhost:11434/api/chat"
        assert payload["model"] == "qwen2.5-coder:3b"
        assert payload["messages"] == [{"role": "user", "content": "Generate SQL"}]
        assert payload["stream"] is False
        assert payload["think"] is False
        assert payload["options"]["temperature"] == 0
        assert payload["options"]["num_predict"] == 384
        assert payload["keep_alive"] == "10m"
        return httpx.Response(
            200,
            json={"message": {"role": "assistant", "content": "SELECT * FROM works"}},
        )

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        response = generate_ollama_sql(
            "Generate SQL",
            base_url="http://localhost:11434/",
            model="qwen2.5-coder:3b",
            client=client,
        )

    assert response == "SELECT * FROM works"


@pytest.mark.parametrize(
    "response_body",
    [
        {},
        {"message": {}},
        {"message": {"content": ""}},
    ],
)
def test_generate_ollama_sql_rejects_missing_content(
    response_body: dict[str, object],
) -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(200, json=response_body)
    )

    with (
        httpx.Client(transport=transport) as client,
        pytest.raises(OllamaResponseError),
    ):
        generate_ollama_sql(
            "Generate SQL",
            base_url="http://localhost:11434",
            model="qwen2.5-coder:3b",
            client=client,
        )
