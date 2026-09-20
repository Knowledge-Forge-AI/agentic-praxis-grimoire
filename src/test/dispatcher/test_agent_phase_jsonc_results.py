from __future__ import annotations

import json

import pytest

from agent_phase import request as request_module
from agent_phase import result as result_module
from agent_phase import review_result
from agent_phase.jsonc import normalize


NONCE = "0123456789abcdef0123456789abcdef"


def terminal_fence(payload: str) -> bytes:
    begin, end = result_module.markers(NONCE)
    return f"{begin}\n{payload}\n{end}".encode("utf-8")


def review_fence(payload: str) -> bytes:
    begin, end = review_result.markers(NONCE)
    return f"{begin}\n{payload}\n{end}".encode("utf-8")


def test_real_trailing_comma_review_result_shape_is_accepted() -> None:
    payload = """{
      "version": 1,
      "stage": "final_review",
      "outcome": "reviewed_with_no_findings",
      "body": "No correctness findings.",
    }"""

    parsed = review_result.parse(review_fence(payload), "final_review", NONCE)

    assert parsed.outcome == "reviewed_with_no_findings"
    assert parsed.body == "No correctness findings."


@pytest.mark.parametrize("version", [True, 1.0, "1"])
def test_terminal_result_version_requires_exact_integer(version: object) -> None:
    payload = json.dumps({
        "version": version,
        "stage": "closeout",
        "outcome": "completed",
        "body": "verified",
        "commit_message": None,
    })

    with pytest.raises(result_module.ResultError) as caught:
        result_module.parse(terminal_fence(payload), "closeout", NONCE)

    assert caught.value.code == "RESULT_VERSION"


@pytest.mark.parametrize(
    ("leading", "trailing"),
    [(" \t\r\n", "\n\r\t "), ("\n", "\r")],
)
def test_outer_ascii_jsonc_whitespace_is_symmetric(
    leading: str, trailing: str
) -> None:
    terminal = json.dumps({
        "version": 1,
        "stage": "closeout",
        "outcome": "completed",
        "body": "verified",
        "commit_message": None,
    })
    review = json.dumps({
        "version": 1,
        "stage": "plan_review",
        "outcome": "reviewed_with_no_findings",
        "body": "",
    })

    assert result_module.parse(
        terminal_fence(leading + terminal + trailing), "closeout", NONCE
    ).completed
    assert review_result.parse(
        review_fence(leading + review + trailing), "plan_review", NONCE
    ).reviewable


@pytest.mark.parametrize("padding", ["\u00a0", "\u2003", "\u2028"])
@pytest.mark.parametrize("leading", [True, False])
def test_outer_non_ascii_jsonc_whitespace_is_rejected(
    padding: str, leading: bool
) -> None:
    terminal = json.dumps({
        "version": 1,
        "stage": "closeout",
        "outcome": "completed",
        "body": "verified",
        "commit_message": None,
    })
    review = json.dumps({
        "version": 1,
        "stage": "plan_review",
        "outcome": "reviewed_with_no_findings",
        "body": "",
    })
    terminal_text = padding + terminal if leading else terminal + padding
    review_text = padding + review if leading else review + padding

    with pytest.raises(result_module.ResultError):
        result_module.parse(terminal_fence(terminal_text), "closeout", NONCE)
    with pytest.raises(review_result.ReviewResultError):
        review_result.parse(review_fence(review_text), "plan_review", NONCE)


def test_line_and_block_comments_are_accepted_by_both_result_parsers() -> None:
    terminal = """{
      // transport note
      "version": 1,
      "stage": "closeout",
      /* semantic result */
      "outcome": "completed",
      "body": "verified",
      "commit_message": null
    }"""
    review = """/* leading */ {
      "version": 1,
      "stage": "plan_review", // bound identity
      "outcome": "reviewed_with_findings",
      "body": "one finding"
    } // trailing comment"""

    assert result_module.parse(terminal_fence(terminal), "closeout", NONCE).completed
    assert review_result.parse(
        review_fence(review), "plan_review", NONCE
    ).outcome == "reviewed_with_findings"


def test_crlf_line_comments_and_line_comment_at_eof_are_accepted() -> None:
    normalized = normalize('{\r\n// note\r\n"value": 1,\r\n}// eof note')

    assert json.loads(normalized) == {"value": 1}


@pytest.mark.parametrize(
    "value",
    [
        'odd escaped quote: \\" followed by // text',
        'even backslashes: \\\\ followed by "quoted // text"',
    ],
)
def test_odd_and_even_backslashes_before_quotes_preserve_string_boundaries(
    value: str,
) -> None:
    strict = json.dumps({"value": value})

    assert json.loads(normalize(strict)) == {"value": value}


def test_comment_between_trailing_comma_and_delimiter_is_accepted() -> None:
    normalized = normalize('{"array": [1, /* note */], "object": {"x": 1, // note\n},}')

    assert json.loads(normalized) == {"array": [1], "object": {"x": 1}}


def test_nested_trailing_commas_include_commit_message() -> None:
    payload = """{
      "version": 1,
      "stage": "closeout",
      "outcome": "completed",
      "body": "verified",
      "commit_message": {
        "subject": "Record the result",
        "body": "Verification:\\nPassed.",
      },
    }"""

    parsed = result_module.parse(terminal_fence(payload), "closeout", NONCE)

    assert parsed.commit_message.subject == "Record the result"
    assert parsed.commit_message.body == "Verification:\nPassed."


def test_nested_array_and_object_trailing_commas_normalize_to_strict_json() -> None:
    value = json.loads(normalize('{"outer":[1,2,],"inner":{"x":1,},}'))

    assert value == {"outer": [1, 2], "inner": {"x": 1}}


def test_comment_tokens_and_punctuation_inside_strings_are_preserved() -> None:
    body = 'https://example.test/a//b, literal /* and //, braces {}, quote " and slash \\'
    payload = json.dumps(
        {
            "version": 1,
            "stage": "closeout",
            "outcome": "completed",
            "body": body,
            "commit_message": None,
        }
    )
    payload = payload[:-1] + ",}"

    parsed = result_module.parse(terminal_fence(payload), "closeout", NONCE)

    assert parsed.body == body
    assert normalize(json.dumps(body)) == json.dumps(body)


def test_duplicate_keys_remain_rejected_after_jsonc_normalization() -> None:
    terminal = """{
      "version": 1,
      "version": 1,
      "stage": "closeout",
      "outcome": "completed",
      "body": "",
      "commit_message": null,
    }"""
    review = """{
      "version": 1,
      "stage": "plan_review",
      "outcome": "reviewed_with_no_findings",
      "outcome": "reviewed_with_findings",
      "body": "",
    }"""

    with pytest.raises(result_module.ResultError) as terminal_error:
        result_module.parse(terminal_fence(terminal), "closeout", NONCE)
    with pytest.raises(review_result.ReviewResultError) as review_error:
        review_result.parse(review_fence(review), "plan_review", NONCE)

    assert terminal_error.value.code == "RESULT_DUPLICATE_KEY"
    assert review_error.value.code == "REVIEW_RESULT_INVALID"


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_non_json_numeric_constants_are_rejected_by_both_result_parsers(
    constant: str,
) -> None:
    terminal = (
        '{"version":1,"stage":"closeout","outcome":"completed",'
        f'"body":{constant},"commit_message":null}}'
    )
    review = (
        '{"version":1,"stage":"plan_review",'
        '"outcome":"reviewed_with_no_findings",'
        f'"body":{constant}}}'
    )

    with pytest.raises(result_module.ResultError) as terminal_error:
        result_module.parse(terminal_fence(terminal), "closeout", NONCE)
    with pytest.raises(review_result.ReviewResultError) as review_error:
        review_result.parse(review_fence(review), "plan_review", NONCE)

    assert terminal_error.value.code == "RESULT_NOT_JSON"
    assert review_error.value.code == "REVIEW_RESULT_INVALID"


def test_lone_surrogates_are_typed_result_failures() -> None:
    terminal = (
        '{"version":1,"stage":"closeout","outcome":"completed",'
        '"body":"\\ud800","commit_message":null}'
    )
    review = (
        '{"version":1,"stage":"plan_review",'
        '"outcome":"reviewed_with_no_findings","body":"\\ud800"}'
    )

    with pytest.raises(result_module.ResultError) as terminal_error:
        result_module.parse(terminal_fence(terminal), "closeout", NONCE)
    with pytest.raises(review_result.ReviewResultError) as review_error:
        review_result.parse(review_fence(review), "plan_review", NONCE)

    assert terminal_error.value.code == "RESULT_BODY"
    assert review_error.value.code == "REVIEW_RESULT_INVALID"


@pytest.mark.parametrize(
    "payload",
    [
        '{"version": 1, /* unterminated',
        '{"version": 1, "stage": "closeout}',
        '{"version": 1, "body": "unterminated}',
    ],
    ids=["unterminated-comment", "incomplete-object", "unterminated-string"],
)
def test_malformed_jsonc_is_rejected(payload: str) -> None:
    with pytest.raises(result_module.ResultError) as caught:
        result_module.parse(terminal_fence(payload), "closeout", NONCE)
    assert caught.value.code == "RESULT_NOT_JSON"


def test_second_object_after_jsonc_result_retains_trailing_content_failure() -> None:
    first = """{
      "version": 1,
      "stage": "closeout",
      "outcome": "completed",
      "body": "",
      "commit_message": null,
    }"""

    with pytest.raises(result_module.ResultError) as terminal_error:
        result_module.parse(terminal_fence(first + " {}"), "closeout", NONCE)
    with pytest.raises(review_result.ReviewResultError):
        review_result.parse(
            review_fence(
                '{"version":1,"stage":"plan_review",'
                '"outcome":"reviewed_with_no_findings","body":"",} {}'
            ),
            "plan_review",
            NONCE,
        )

    assert terminal_error.value.code == "RESULT_TRAILING_CONTENT"


@pytest.mark.parametrize("payload", ["plain prose", "outcome: completed"])
def test_arbitrary_prose_and_yaml_are_not_coerced(payload: str) -> None:
    with pytest.raises(result_module.ResultError) as terminal_error:
        result_module.parse(terminal_fence(payload), "closeout", NONCE)
    with pytest.raises(review_result.ReviewResultError):
        review_result.parse(review_fence(payload), "plan_review", NONCE)

    assert terminal_error.value.code == "RESULT_NOT_JSON"


def test_producer_request_parsing_remains_strict_json() -> None:
    trailing_comma = (
        b'{"schema":"agent-phase-request-v1",'
        b'"phase_type":"implementation_testing",'
        b'"execution_mode":"normal","prompt":"task",}'
    )
    commented = trailing_comma.replace(b'"prompt"', b'/* no */ "prompt"')

    with pytest.raises(request_module.RequestError):
        request_module.parse_request(trailing_comma)
    with pytest.raises(request_module.RequestError):
        request_module.parse_request(commented)


@pytest.mark.parametrize(
    ("payload", "expected_val"),
    [
        ('{"version": 1, "extra": "allowed", /* comment */ "trailing": true, }', {"version": 1, "extra": "allowed", "trailing": True}),
        ('[1, 2, 3, /* item */ 4,]', [1, 2, 3, 4]),
        ('"valid json string with // comment inside"', "valid json string with // comment inside"),
        ('42.5', 42.5),
        ('true // comment', True),
        ('false /* comment */', False),
        ('null // empty', None),
    ],
)
def test_syntax_layer_accepts_all_json_roots_and_jsonc(payload: str, expected_val: object) -> None:
    from agent_phase.jsonc import raw_decode
    val, trailing = raw_decode(payload, object_pairs_hook=dict)
    assert val == expected_val
    assert trailing.strip() == ""


def test_stage_and_review_results_tolerate_extra_fields() -> None:
    terminal_payload = json.dumps({
        "version": 1,
        "stage": "closeout",
        "outcome": "completed",
        "body": "done",
        "commit_message": None,
        "extra_field_1": "tolerated",
        "extra_nested": {"foo": "bar"},
    })
    parsed_term = result_module.parse(terminal_fence(terminal_payload), "closeout", NONCE)
    assert parsed_term.completed
    assert parsed_term.body == "done"

    review_payload = json.dumps({
        "version": 1,
        "stage": "plan_review",
        "outcome": "reviewed_with_no_findings",
        "body": "Approved",
        "extra_field_1": "tolerated",
    })
    parsed_rev = review_result.parse(review_fence(review_payload), "plan_review", NONCE)
    assert parsed_rev.outcome == "reviewed_with_no_findings"
    assert parsed_rev.body == "Approved"


@pytest.mark.parametrize(
    "payload",
    [
        "{}",
        "[]",
        '["a", 1, true]',
        '"text"',
        "42",
        "3.14",
        "true",
        "false",
        "null",
        "{\n  // comment\n  \"outcome\": \"completed\",\n  /* block */\n}",
        "[\n  // comment\n  1, 2,\n  /* block */\n]",
    ],
)
def test_all_valid_json_roots_and_jsonc_parse_successfully(payload: str) -> None:
    parsed_term = result_module.parse(terminal_fence(payload), "closeout", NONCE)
    assert isinstance(parsed_term, result_module.StageResult)
    assert parsed_term.version == 1
    assert parsed_term.stage == "closeout"

    parsed_rev = review_result.parse(review_fence(payload), "plan_review", NONCE)
    assert isinstance(parsed_rev, review_result.ReviewResult)
    assert parsed_rev.version == 1
    assert parsed_rev.stage == "plan_review"
    assert parsed_rev.nonce == NONCE


def test_partial_objects_parse_successfully_with_semantic_values() -> None:
    # {"outcome":"completed"}
    p1 = result_module.parse(terminal_fence('{"outcome":"completed"}'), "closeout", NONCE)
    assert p1.outcome == "completed"
    assert p1.completed is True
    assert p1.stage == "closeout"
    assert p1.commit_message is None

    r1 = review_result.parse(review_fence('{"outcome":"completed"}'), "plan_review", NONCE)
    assert r1.outcome == "unreviewable"
    assert not r1.reviewable

    # {"body":"reviewed"}
    p2 = result_module.parse(terminal_fence('{"body":"reviewed"}'), "closeout", NONCE)
    assert p2.outcome == "blocked"
    assert p2.completed is False
    assert p2.body == "reviewed"

    r2 = review_result.parse(review_fence('{"body":"reviewed"}'), "plan_review", NONCE)
    assert r2.outcome == "unreviewable"
    assert not r2.reviewable

    # {"stage":"closeout"}
    p3 = result_module.parse(terminal_fence('{"stage":"closeout"}'), "closeout", NONCE)
    assert p3.outcome == "blocked"
    assert p3.completed is False
    assert p3.stage == "closeout"

    r3 = review_result.parse(review_fence('{"stage":"plan_review"}'), "plan_review", NONCE)
    assert r3.outcome == "unreviewable"
    assert not r3.reviewable

    # {"extra":"value"}
    p4 = result_module.parse(terminal_fence('{"extra":"value"}'), "closeout", NONCE)
    assert p4.outcome == "blocked"
    assert p4.completed is False

    r4 = review_result.parse(review_fence('{"extra":"value"}'), "plan_review", NONCE)
    assert r4.outcome == "unreviewable"
    assert not r4.reviewable


@pytest.mark.parametrize(
    "payload",
    [
        "{}",
        "[]",
        '["a", 1, true]',
        '"text"',
        "42",
        "3.14",
        "true",
        "false",
        "null",
        '{"body":"reviewed"}',
        '{"stage":"closeout"}',
        '{"extra":"value"}',
    ],
)
def test_valid_json_without_completion_semantics_never_silently_completes(
    payload: str,
) -> None:
    parsed = result_module.parse(terminal_fence(payload), "closeout", NONCE)
    assert parsed.completed is False
    assert parsed.outcome == "blocked"


@pytest.mark.parametrize(
    "payload",
    [
        "{}",
        "[]",
        '["a", 1, true]',
        '"text"',
        "42",
        "3.14",
        "true",
        "false",
        "null",
        '{"outcome":"completed"}',
        '{"body":"reviewed"}',
        '{"stage":"plan_review"}',
        '{"extra":"value"}',
    ],
)
def test_valid_json_without_review_semantics_becomes_unreviewable_without_throwing(
    payload: str,
) -> None:
    parsed = review_result.parse(review_fence(payload), "plan_review", NONCE)
    assert parsed.outcome == "unreviewable"
    assert parsed.reviewable is False
    assert "recognizable review semantics" in parsed.body

