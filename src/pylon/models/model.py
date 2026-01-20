from abc import ABC, abstractmethod
import logging
from typing import Generic, TypeVar, Optional, Type


logger = logging.getLogger(__name__)


C = TypeVar("C")  # domain context / observation
R = TypeVar("R")  # return type


class InvalidModelReturnType(Exception):
    pass


class ModelExecutionError(Exception):
    pass


class TypedModel(ABC, Generic[C, R]):
    """Base class for models with typed context and return value.

    Subclasses must implement the `execute` method. The `execute` method
    is called by the `_execute` method, which also checks that the
    return type matches the expected type if provided.
    """

    def __init__(
        self,
        name: Optional[str] = None,
        return_type: Optional[Type[R]] = None,
    ) -> None:
        self.name = name or self.__class__.__name__
        self._return_type = return_type

    def _execute(self, context: C) -> R:
        """Executes the model with the given context and checks the return type.

        This method should not be overridden by subclasses. Subclasses should
        implement the `execute` method instead. This method will be called internally
        to run the model and validate its output.
        """
        result = self.execute(context)

        if self._return_type and not isinstance(result, self._return_type):
            logger.error(
                f"Model '{self.name}' returned invalid type: {type(result).__name__}"
            )
            raise InvalidModelReturnType(
                f"{self.name}.execute() must return {self._return_type.__name__}, "
                f"got {type(result).__name__}"
            )

        return result

    @abstractmethod
    def execute(self, context: C) -> R: ...


class IntegerModel(TypedModel[C, int]):
    def __init__(self, name: Optional[str] = None) -> None:
        super().__init__(name=name, return_type=int)


class FloatModel(TypedModel[C, float]):
    def __init__(self, name: Optional[str] = None) -> None:
        super().__init__(name=name, return_type=float)


class BooleanModel(TypedModel[C, bool]):
    def __init__(self, name: Optional[str] = None) -> None:
        super().__init__(name=name, return_type=bool)


class StringModel(TypedModel[C, str]):
    def __init__(self, name: Optional[str] = None) -> None:
        super().__init__(name=name, return_type=str)
