"""Bound standard ruamel.yaml loading; leave YAML semantics to the library."""

import io

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError
from ruamel.yaml.events import CollectionEndEvent, CollectionStartEvent
from ruamel.yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode


def _reader() -> YAML:
    return YAML(typ="safe", pure=True)


def load_yaml(source: str | bytes, max_bytes: int) -> object:
    if not isinstance(source, (str, bytes)):
        raise ValueError("expected YAML text or bytes")
    if len(source) > max_bytes:
        raise ValueError("YAML byte limit exceeded")
    text = source.decode("utf-8") if isinstance(source, bytes) else source
    if len(text.encode("utf-8")) > max_bytes:
        raise ValueError("YAML byte limit exceeded")
    try:
        # Stream events before composition allocates a node graph. This is only
        # a resource guard; ruamel owns all syntax and scalar interpretation.
        depth = 0
        for count, event in enumerate(_reader().parse(text), 1):
            if isinstance(event, CollectionStartEvent):
                depth += 1
            elif isinstance(event, CollectionEndEvent):
                depth -= 1
            if depth > 65 or count > 2_000_000:
                raise ValueError("YAML event/depth limit exceeded")
        # Compose keeps aliases as references. Bound their expanded graph before
        # the standard constructor can flatten merges or materialize values.
        node = _reader().compose(text)
        stack: list[tuple[Node, int]] = [] if node is None else [(node, 0)]
        # Count keys too: up to twice the existing value-tree node allowance.
        count = scalar_chars = 0
        while stack:
            item, depth = stack.pop()
            count += 1
            if depth > 64 or count > 1_000_000:
                raise ValueError("YAML depth/expanded-node limit exceeded")
            if isinstance(item, ScalarNode):
                # Also bound YAML 1.1 base-60 integer arithmetic before conversion.
                if item.tag == "tag:yaml.org,2002:int" and len(item.value) > 4300:
                    raise ValueError("YAML numeric scalar limit exceeded")
                scalar_chars += len(item.value)
                if scalar_chars > max_bytes:
                    raise ValueError("YAML expanded-scalar limit exceeded")
            elif isinstance(item, MappingNode):
                stack.extend(
                    (child, depth + 1) for pair in item.value for child in pair
                )
            elif isinstance(item, SequenceNode):
                stack.extend((child, depth + 1) for child in item.value)
        try:
            result: object = _reader().load(text)
        except (ValueError, OverflowError):
            raise ValueError("invalid YAML scalar") from None
        except AssertionError:
            raise ValueError("invalid YAML mapping") from None
        return result
    except YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        location = f" at line {mark.line + 1}, column {mark.column + 1}" if mark else ""
        # Library exception text can include entire input lines or duplicate values.
        raise ValueError(f"invalid YAML ({type(exc).__name__}){location}") from None
    except RecursionError:
        raise ValueError("YAML nesting limit exceeded") from None


def dump_yaml(tree: object, max_bytes: int) -> str:
    stream = io.StringIO()
    writer = _reader()
    writer.default_flow_style = False
    writer.sort_base_mapping_type_on_output = False  # type: ignore[assignment]  # Upstream annotates the initial None only.
    writer.allow_unicode = True
    writer.dump(tree, stream)
    result = stream.getvalue()
    if len(result.encode("utf-8")) > max_bytes:
        raise ValueError("YAML byte limit exceeded")
    return result
