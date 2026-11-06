import builtins

import pytest

from cardreport import DependencyError
from cardreport import _weasy_worker as worker


@pytest.mark.parametrize(
    "error",
    [
        OSError("cannot load library 'libgobject-2.0-0'"),
        ImportError("No module named 'weasyprint'"),
    ],
)
def test_dependency_error_preserves_cause_and_setup_link(monkeypatch, error):
    original_import = builtins.__import__

    def failing_import(name, *args, **kwargs):
        if name == "weasyprint":
            raise error
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", failing_import)
    with pytest.raises(DependencyError) as caught:
        worker.main()

    message = str(caught.value)
    assert str(error) in message
    assert caught.value.__cause__ is error
    assert (
        "https://github.com/arch7tect/cardreport/blob/main/"
        "docs/user/renderers.md#weasyprint" in message
    )
