import json
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel

from structsure.core import generate


class ExampleModel(BaseModel):
    foo: str
    bar: int


class FakeOpenAIClient:
    def __init__(self, responses: list[str]):
        self._responses = responses
        self._calls = 0

    class _Chat:
        class _Completions:
            def __init__(self, outer):
                self._outer = outer

            def create(self, model: str, messages: list[dict[str, str]], response_format: dict[str, str]):
                # Simulate OpenAI API response structure
                idx = self._outer._outer._calls
                self._outer._outer._calls += 1
                content = self._outer._outer._responses[idx]
                return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

        def __init__(self, outer):
            self._outer = outer
            self.completions = self._Completions(outer)

    @property
    def chat(self):
        return self._Chat(self)


def test_generate_success_first_try():
    valid = json.dumps({"foo": "hello", "bar": 42})
    client = FakeOpenAIClient([valid])

    result = generate(
        client=client,  # type: ignore[arg-type]
        model="gpt-test",
        response_model=ExampleModel,
        prompt="produce a valid json",
    )

    assert isinstance(result, ExampleModel)
    assert result.foo == "hello"
    assert result.bar == 42


def test_generate_recovers_after_failure():
    invalid = "{not valid json}"
    valid = json.dumps({"foo": "world", "bar": 7})
    client = FakeOpenAIClient([invalid, valid])

    result = generate(
        client=client,  # type: ignore[arg-type]
        model="gpt-test",
        response_model=ExampleModel,
        prompt="produce a valid json",
        max_retries=3,
    )

    assert result.foo == "world"
    assert result.bar == 7


def test_generate_exceeds_retries():
    invalids = ["{not valid json}"] * 3
    client = FakeOpenAIClient(invalids)

    with pytest.raises(Exception):
        generate(
            client=client,  # type: ignore[arg-type]
            model="gpt-test",
            response_model=ExampleModel,
            prompt="bad json",
            max_retries=3,
        )
