from copy import deepcopy
from datetime import date
from decimal import Decimal

import pytest

from cardreport import (
    BindingError,
    Card,
    Dataset,
    ReportTemplate,
    TemplateError,
)


def definition():
    return {
        "format": "cardreport.template/1",
        "datasets": {
            "summary": {
                "cardinality": "one",
                "fields": {"count": {"type": "integer"}, "label": {"type": "text"}},
            },
            "items": {
                "cardinality": "many",
                "fields": {
                    "name": {"type": "text"},
                    "n": {"type": "number"},
                    "gap": {"type": "number", "nullable": True},
                    "day": {"type": "date"},
                },
            },
        },
        "report": {
            "blocks": [
                {
                    "type": "row",
                    "height_mm": 50,
                    "children": [
                        {
                            "type": "card",
                            "content": {
                                "type": "kpi",
                                "label": {
                                    "bind": {"dataset": "summary", "field": "label"}
                                },
                                "value": {
                                    "bind": {"dataset": "summary", "field": "count"}
                                },
                            },
                        }
                    ],
                }
            ]
        },
    }


def data(count=12):
    return {
        "summary": Dataset.single({"count": count, "label": "Clients"}),
        "items": Dataset.from_dicts(
            [{"name": "A", "n": Decimal("2.3"), "gap": None, "day": date(2026, 1, 1)}]
        ),
    }


def test_reuse_detachment_and_empty_metadata():
    spec = definition()
    tpl = ReportTemplate.from_dict(spec)
    spec["report"]["blocks"].clear()
    first = tpl.bind(data())
    second = tpl.bind(data(99))
    assert first.blocks[0].children[0].content.value == 12
    assert second.blocks[0].children[0].content.value == 99
    detached = tpl.to_dict()
    detached["report"]["blocks"].clear()
    assert len(tpl.bind(data()).blocks) == 1
    assert ReportTemplate.from_json(tpl.to_json()).to_dict() == tpl.to_dict()
    empty = data()
    empty["items"] = Dataset(["name", "n", "gap", "day"], [])
    tpl.bind(empty)
    with pytest.raises(BindingError):
        tpl.bind({"summary": data()["summary"]})


@pytest.mark.parametrize(
    "mutate",
    [
        lambda s: s.update(format="cardreport.template/2"),
        lambda s: s["report"].update(unknown=True),
        lambda s: s["report"].update(title=None),
        lambda s: s["datasets"]["summary"].update(cardinality="many"),
        lambda s: s["datasets"]["summary"]["fields"]["label"].update(nullable=True),
        lambda s: s["report"]["blocks"][0]["children"][0]["content"].update(value=12),
        lambda s: s["report"]["blocks"][0]["children"][0]["content"].update(
            format="date"
        ),
    ],
)
def test_invalid_definition(mutate):
    spec = definition()
    mutate(spec)
    with pytest.raises(TemplateError):
        ReportTemplate(spec)


def test_binding_error_locations():
    tpl = ReportTemplate(definition())
    bad = data()
    bad["summary"] = Dataset.single({"count": "12", "label": "Clients"})
    with pytest.raises(BindingError) as caught:
        tpl.bind(bad)
    assert (caught.value.dataset, caught.value.row, caught.value.field) == (
        "summary",
        0,
        "count",
    )
    spec = definition()
    spec["report"]["blocks"] = [
        {"type": "table", "dataset": "items", "columns": [{"key": "n", "label": "N"}]}
    ]
    bad = data()
    bad["items"] = Dataset.from_dicts(
        [{"name": "A", "n": 1, "gap": None, "day": date(2026, 1, 1)}]
    )
    ReportTemplate(spec).bind(bad)
    spec["report"]["blocks"] = [
        {"type": "funnel", "dataset": "items", "category": "name", "value": "n"}
    ]
    bad["items"] = Dataset.from_dicts(
        [{"name": "A", "n": -1, "gap": None, "day": date(2026, 1, 1)}]
    )
    with pytest.raises(BindingError) as caught:
        ReportTemplate(spec).bind(bad)
    assert caught.value.template_path == "report.blocks[0]"
    assert caught.value.__cause__ is not None


def test_all_components_and_static_chart_contracts():
    spec = definition()
    spec["report"]["mode"] = "flow"
    spec["report"]["blocks"] += [
        {"type": "text", "text": "Literal <b> & Пример", "style": "caption"},
        {"type": "page_break"},
        {"type": "column", "children": [{"type": "text", "text": "Inside"}]},
        {
            "type": "table",
            "dataset": "items",
            "columns": [{"key": "n", "label": "N", "format": {"currency": "EUR"}}],
        },
        {
            "type": "bar",
            "dataset": "items",
            "category": "name",
            "series": [{"field": "n", "label": "N"}],
        },
        {
            "type": "line",
            "dataset": "items",
            "x": "day",
            "x_kind": "date",
            "value": "gap",
        },
        {"type": "funnel", "dataset": "items", "category": "name", "value": "n"},
    ]
    report = ReportTemplate(spec).bind(data())
    assert len(report.blocks) == 8
    assert "Literal &lt;b&gt;" in report.to_html()
    for change in [
        {"value": "gap"},
        {"category": "day"},
        {"series": [{"field": "n", "label": "N"}], "value": "n"},
    ]:
        bad = deepcopy(spec)
        bad["report"]["blocks"] = [
            {
                "type": "bar",
                "dataset": "items",
                "category": "name",
                "value": "n",
                **change,
            }
        ]
        with pytest.raises(TemplateError):
            ReportTemplate(bad)
    bad = deepcopy(spec)
    bad["report"]["blocks"] = [{"type": "card", "content": {"type": "page_break"}}]
    with pytest.raises(TemplateError):
        ReportTemplate(bad)


def test_native_cycles_and_unknown_versions():
    spec = definition()
    spec["report"]["blocks"].append(spec)
    with pytest.raises(TemplateError):
        ReportTemplate(spec)
    with pytest.raises(TemplateError):
        ReportTemplate.from_json('{"format":1,"format":2}')


def test_nullable_card_title_and_kpi_note():
    spec = definition()
    spec["datasets"]["summary"]["fields"]["note"] = {"type": "text", "nullable": True}
    card = spec["report"]["blocks"][0]["children"][0]
    card["title"] = {"bind": {"dataset": "summary", "field": "note"}}
    card["content"]["note"] = card["title"]
    inp = data()
    inp["summary"] = Dataset.single({"count": 1, "label": "A", "note": None})
    report = ReportTemplate(spec).bind(inp)
    result = report.blocks[0].children[0]
    assert (
        isinstance(result, Card)
        and result.title is None
        and result.content.note is None
    )


def test_definition_locations_and_mapping_inputs():
    from types import MappingProxyType

    spec = definition()
    spec["report"]["theme"] = {"accent": "invalid"}
    with pytest.raises(TemplateError) as caught:
        ReportTemplate(spec)
    assert caught.value.template_path == "report.theme.accent"
    spec = definition()
    spec["report"]["blocks"].insert(0, {"type": "row", "children": []})
    with pytest.raises(TemplateError) as caught:
        ReportTemplate(spec)
    assert caught.value.template_path == "report.blocks[0]"
    spec = definition()
    spec["report"] = MappingProxyType(spec["report"])
    ReportTemplate(MappingProxyType(spec)).bind(data())


def test_binding_lowered_limits_and_table_location():
    from cardreport import DataLimits

    tpl = ReportTemplate(definition())
    with pytest.raises(BindingError) as caught:
        tpl.bind(data(), limits=DataLimits(max_string_chars=3))
    assert (caught.value.dataset, caught.value.row, caught.value.field) == (
        "summary",
        0,
        "label",
    )
    with pytest.raises(BindingError):
        tpl.bind([])
    spec = definition()
    spec["datasets"]["items"]["fields"]["str:field"] = {"type": "text"}
    spec["report"]["blocks"] = [
        {
            "type": "table",
            "dataset": "items",
            "columns": [{"key": "str:field", "label": "Text"}],
        }
    ]
    inp = data()
    inp["items"] = Dataset.single(
        {
            "name": "A",
            "n": 1,
            "gap": None,
            "day": date(2026, 1, 1),
            "str:field": "\U0001f984",
        }
    )
    with pytest.raises(BindingError) as caught:
        ReportTemplate(spec).bind(inp)
    assert (caught.value.dataset, caught.value.row, caught.value.field) == (
        "items",
        0,
        "str:field",
    )
    assert caught.value.template_path == "report.blocks[0]"


def test_bound_hostile_text_is_literal():
    inp = data()
    inp["summary"] = Dataset.single(
        {"count": 1, "label": '<script>alert("x")</script>'}
    )
    html = ReportTemplate(definition()).bind(inp).to_html()
    assert "&lt;script&gt;alert" in html
    assert '<script>alert("x")</script>' not in html
