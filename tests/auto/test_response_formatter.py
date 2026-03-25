# tests/auto/test_response_formatter.py
"""Tests for app.response_formatter — format_text, format_binary, format_json, sanitization.

Covers:
  - format_text_response: wraps text in EmbeddedResource, strips invisible chars
  - format_binary_response: base64-encodes binary into BlobResourceContents
  - format_json_response: serializes + sanitizes JSON, wraps in EmbeddedResource
  - _strip_invisible_chars: removes zero-width spaces, bidi overrides, BOM
  - _sanitize_data: recursive dict/list/str sanitization
  - _resource_uri: builds eodhd:// URIs
"""

import base64
import json

import pytest
from app.response_formatter import (
    _resource_uri,
    _sanitize_data,
    _strip_invisible_chars,
    format_binary_response,
    format_json_response,
    format_text_response,
    raise_on_api_error,
)
from fastmcp.exceptions import ToolError
from mcp.types import BlobResourceContents, EmbeddedResource, TextResourceContents

# ---------------------------------------------------------------------------
# _strip_invisible_chars
# ---------------------------------------------------------------------------


class TestStripInvisibleChars:
    def test_no_invisible(self):
        assert _strip_invisible_chars("hello world") == "hello world"

    def test_zero_width_space(self):
        assert _strip_invisible_chars("hel\u200blo") == "hello"

    def test_zero_width_non_joiner(self):
        assert _strip_invisible_chars("ab\u200ccd") == "abcd"

    def test_zero_width_joiner(self):
        assert _strip_invisible_chars("ab\u200dcd") == "abcd"

    def test_left_to_right_mark(self):
        assert _strip_invisible_chars("ab\u200ecd") == "abcd"

    def test_right_to_left_mark(self):
        assert _strip_invisible_chars("ab\u200fcd") == "abcd"

    def test_bidi_overrides(self):
        # U+202A..U+202F are bidi control chars
        assert _strip_invisible_chars("a\u202ab\u202ec") == "abc"

    def test_word_joiner(self):
        assert _strip_invisible_chars("a\u2060b") == "ab"

    def test_bom(self):
        assert _strip_invisible_chars("\ufeffhello") == "hello"

    def test_multiple_invisible(self):
        assert _strip_invisible_chars("\u200b\u200c\u200d\ufeff") == ""

    def test_empty_string(self):
        assert _strip_invisible_chars("") == ""

    def test_preserves_normal_unicode(self):
        assert _strip_invisible_chars("héllo wörld 日本語") == "héllo wörld 日本語"

    def test_preserves_newlines_and_tabs(self):
        assert _strip_invisible_chars("line1\nline2\ttab") == "line1\nline2\ttab"


# ---------------------------------------------------------------------------
# _sanitize_data
# ---------------------------------------------------------------------------


class TestSanitizeData:
    def test_string(self):
        assert _sanitize_data("hel\u200blo") == "hello"

    def test_clean_string(self):
        assert _sanitize_data("hello") == "hello"

    def test_dict(self):
        result = _sanitize_data({"key": "val\u200bue", "num": 42})
        assert result == {"key": "value", "num": 42}

    def test_list(self):
        result = _sanitize_data(["a\u200bb", "clean"])
        assert result == ["ab", "clean"]

    def test_nested(self):
        result = _sanitize_data({"a": [{"b": "c\u200dd"}]})
        assert result == {"a": [{"b": "cd"}]}

    def test_int_passthrough(self):
        assert _sanitize_data(42) == 42

    def test_float_passthrough(self):
        assert _sanitize_data(3.14) == 3.14

    def test_bool_passthrough(self):
        assert _sanitize_data(True) is True

    def test_none_passthrough(self):
        assert _sanitize_data(None) is None

    def test_empty_dict(self):
        assert _sanitize_data({}) == {}

    def test_empty_list(self):
        assert _sanitize_data([]) == []


# ---------------------------------------------------------------------------
# _resource_uri
# ---------------------------------------------------------------------------


class TestResourceUri:
    def test_simple_path(self):
        uri = _resource_uri("eod/AAPL")
        assert str(uri) == "eodhd://api/eod/AAPL"

    def test_strips_leading_slash(self):
        uri = _resource_uri("/eod/AAPL")
        assert str(uri) == "eodhd://api/eod/AAPL"

    def test_response_default(self):
        uri = _resource_uri("response")
        assert str(uri) == "eodhd://api/response"


# ---------------------------------------------------------------------------
# format_text_response
# ---------------------------------------------------------------------------


class TestFormatTextResponse:
    def test_returns_list_of_one(self):
        result = format_text_response("hello", "text/plain")
        assert isinstance(result, list)
        assert len(result) == 1

    def test_embedded_resource_type(self):
        result = format_text_response("hello", "text/plain")
        assert isinstance(result[0], EmbeddedResource)
        assert result[0].type == "resource"

    def test_text_resource_contents(self):
        result = format_text_response("hello", "text/plain")
        resource = result[0].resource
        assert isinstance(resource, TextResourceContents)
        assert resource.text == "hello"
        assert resource.mimeType == "text/plain"

    def test_csv_mime(self):
        result = format_text_response("a,b\n1,2", "text/csv")
        assert result[0].resource.mimeType == "text/csv"

    def test_strips_invisible_chars(self):
        result = format_text_response("hel\u200blo", "text/plain")
        assert result[0].resource.text == "hello"

    def test_custom_resource_path(self):
        result = format_text_response("x", "text/plain", resource_path="eod/AAPL")
        assert "eod/AAPL" in str(result[0].resource.uri)

    def test_default_resource_path(self):
        result = format_text_response("x", "text/plain")
        assert "response" in str(result[0].resource.uri)

    def test_empty_text(self):
        result = format_text_response("", "text/plain")
        assert result[0].resource.text == ""


# ---------------------------------------------------------------------------
# format_binary_response
# ---------------------------------------------------------------------------


class TestFormatBinaryResponse:
    def test_returns_list_of_one(self):
        result = format_binary_response(b"\x89PNG", "image/png")
        assert isinstance(result, list)
        assert len(result) == 1

    def test_embedded_resource_type(self):
        result = format_binary_response(b"\x00", "application/octet-stream")
        assert isinstance(result[0], EmbeddedResource)
        assert result[0].type == "resource"

    def test_blob_resource_contents(self):
        data = b"hello bytes"
        result = format_binary_response(data, "application/octet-stream")
        resource = result[0].resource
        assert isinstance(resource, BlobResourceContents)
        assert resource.mimeType == "application/octet-stream"

    def test_base64_encoding(self):
        data = b"hello bytes"
        result = format_binary_response(data, "application/octet-stream")
        blob = result[0].resource.blob
        assert base64.b64decode(blob) == data

    def test_empty_bytes(self):
        result = format_binary_response(b"", "application/octet-stream")
        assert base64.b64decode(result[0].resource.blob) == b""

    def test_custom_resource_path(self):
        result = format_binary_response(b"\x00", "image/png", resource_path="logos/AAPL")
        assert "logos/AAPL" in str(result[0].resource.uri)


# ---------------------------------------------------------------------------
# format_json_response
# ---------------------------------------------------------------------------


class TestFormatJsonResponse:
    def test_returns_list_of_one(self):
        result = format_json_response({"a": 1})
        assert isinstance(result, list)
        assert len(result) == 1

    def test_embedded_resource_type(self):
        result = format_json_response({"a": 1})
        assert isinstance(result[0], EmbeddedResource)

    def test_mime_type_json(self):
        result = format_json_response({"a": 1})
        assert result[0].resource.mimeType == "application/json"

    def test_text_is_valid_json(self):
        result = format_json_response({"key": "value", "num": 42})
        parsed = json.loads(result[0].resource.text)
        assert parsed == {"key": "value", "num": 42}

    def test_sanitizes_invisible_chars(self):
        result = format_json_response({"k": "v\u200bal"})
        parsed = json.loads(result[0].resource.text)
        assert parsed == {"k": "val"}

    def test_sanitizes_nested(self):
        result = format_json_response({"a": [{"b": "c\u200dd"}]})
        parsed = json.loads(result[0].resource.text)
        assert parsed == {"a": [{"b": "cd"}]}

    def test_list_input(self):
        result = format_json_response([1, 2, 3])
        parsed = json.loads(result[0].resource.text)
        assert parsed == [1, 2, 3]

    def test_null_values(self):
        result = format_json_response({"a": None})
        parsed = json.loads(result[0].resource.text)
        assert parsed == {"a": None}

    def test_custom_resource_path(self):
        result = format_json_response({"a": 1}, resource_path="fundamentals/AAPL")
        assert "fundamentals/AAPL" in str(result[0].resource.uri)

    def test_indented_output(self):
        result = format_json_response({"a": 1})
        text = result[0].resource.text
        assert "\n" in text  # indent=2 produces newlines

    def test_empty_dict(self):
        result = format_json_response({})
        parsed = json.loads(result[0].resource.text)
        assert parsed == {}

    def test_error_dict_raises_tool_error(self):
        with pytest.raises(ToolError, match="Forbidden"):
            format_json_response({"error": "Forbidden", "status_code": 403})


class TestRaiseOnApiError:
    def test_non_error_dict_noop(self):
        raise_on_api_error({"ok": True})

    def test_error_dict_raises(self):
        with pytest.raises(ToolError, match="Forbidden"):
            raise_on_api_error({"error": "Forbidden"})

    def test_error_dict_includes_status_and_detail(self):
        with pytest.raises(ToolError, match="403"):
            raise_on_api_error({"error": "Forbidden", "status_code": 403, "text": "invalid API key"})

    def test_error_dict_includes_structured_upstream_context(self):
        with pytest.raises(ToolError, match="code=OPERATION_NOT_PERMITTED"):
            raise_on_api_error(
                {
                    "error": "EODHD API request failed with 401 Unauthorized.",
                    "status_code": 401,
                    "error_code": "OPERATION_NOT_PERMITTED",
                    "upstream_message": "User 12 do not have access to this watch list DJI",
                }
            )

    def test_error_dict_parses_json_detail_from_text(self):
        with pytest.raises(ToolError, match="watch list DJI"):
            raise_on_api_error(
                {
                    "error": "EODHD API request failed with 401 Unauthorized.",
                    "status_code": 401,
                    "text": '{"code":"OPERATION_NOT_PERMITTED","errorMessage":"User 12 do not have access to this watch list DJI"}',
                }
            )
