import pytest
from dataclasses import dataclass

from pylon.models.model import TypedModel, InvalidModelReturnType


@dataclass(frozen=True)
class DummyContext:
    value: int


class IntReturningModel(TypedModel[DummyContext, int]):
    def __init__(self):
        super().__init__(return_type=int)

    def execute(self, context: DummyContext) -> int:
        return context.value


def test_typed_model_accepts_correct_type():
    model = IntReturningModel()
    ctx = DummyContext(value=5)

    result = model._execute(ctx)  # type: ignore

    assert result == 5


class BadModel(TypedModel[DummyContext, int]):
    def __init__(self):
        super().__init__(name="BadModel", return_type=int)

    def execute(self, context: DummyContext) -> int:
        return "not an int"  # type: ignore


def test_typed_model_rejects_incorrect_type():
    model = BadModel()
    ctx = DummyContext(value=5)

    with pytest.raises(InvalidModelReturnType) as exc:
        model._execute(ctx)  # type: ignore

    msg = str(exc.value)
    assert "BadModel.execute()" in msg
    assert "must return int" in msg
    assert "got str" in msg


class UntypedModel(TypedModel[DummyContext, object]):
    def execute(self, context: DummyContext):
        return "anything"


def test_typed_model_allows_any_return_when_no_return_type():
    model = UntypedModel()
    ctx = DummyContext(value=5)

    result = model._execute(ctx)  # type: ignore

    assert result == "anything"


def test_typed_model_is_abstract():
    with pytest.raises(TypeError):
        TypedModel()  # type: ignore


def test_execute_not_implemented_raises():
    with pytest.raises(TypeError):

        class IncompleteModel(TypedModel[DummyContext, int]):
            pass

        IncompleteModel()  # type: ignore
