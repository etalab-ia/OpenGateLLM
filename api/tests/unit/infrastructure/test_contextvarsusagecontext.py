from contextvars import ContextVar

import pytest

from api.domain.usage.entities import Usage
from api.infrastructure.contextvars import ContextVarsUsageContext
from api.infrastructure.fastapi import RequestContext


@pytest.fixture
def request_context_var():
    return ContextVar("test_request_context", default=RequestContext(id="a" * 32))


@pytest.fixture
def usage_context(request_context_var):
    return ContextVarsUsageContext(request_context=request_context_var)


def test_should_expose_request_id_from_request_context(usage_context):
    assert usage_context.request_id == "a" * 32


def test_should_raise_when_request_id_is_missing(request_context_var):
    request_context_var.set(RequestContext())
    usage_context = ContextVarsUsageContext(request_context=request_context_var)

    with pytest.raises(RuntimeError, match="request_id missing"):
        _ = usage_context.request_id


def test_should_record_usage_without_overwriting_request_id(usage_context, request_context_var):
    usage = Usage(prompt_tokens=1, completion_tokens=2, total_tokens=3)

    usage_context.record_usage(usage=usage)

    context = request_context_var.get()
    assert context.id == "a" * 32
    assert context.usage is usage
