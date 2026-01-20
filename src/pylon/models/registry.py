from typing import Any, Dict, Type, TypeVar, cast
import logging

from .model import TypedModel


logger = logging.getLogger(__name__)


T = TypeVar("T", bound=TypedModel[Any, Any])


class ModelRegistryError(Exception):
    pass


class DuplicateModelError(ModelRegistryError):
    pass


class ModelNotFoundError(ModelRegistryError):
    pass


class ModelRegistry:
    """
    Registry for TypedModel instances.

    Allows registering and retrieving models by name to be
    used in the Pylon simulation.
    """

    def __init__(self) -> None:
        self._models: Dict[str, TypedModel[Any, Any]] = {}

    def register_model(
        self, model: TypedModel[Any, Any], override: bool = False
    ) -> None:
        if model.name in self._models:
            if not override:
                raise DuplicateModelError(f"Model '{model.name}' is already registered")
            logger.warning(f"Overwriting model '{model.name}' in registry")
        self._models[model.name] = model

    def unregister_model(self, name: str) -> None:
        if name not in self._models:
            logger.error(f"Model '{name}' is not registered")
            raise ModelNotFoundError(f"Model '{name}' is not registered")
        del self._models[name]

    def get(self, name: str) -> TypedModel[Any, Any]:
        if name not in self._models:
            logger.error(f"Model '{name}' is not registered")
            raise ModelNotFoundError(f"Model '{name}' is not registered")
        return self._models[name]

    def get_typed(self, name: str, t: Type[T]) -> T:
        return cast(T, self.get(name))

    def clear(self) -> None:
        self._models.clear()

    @property
    def models(self) -> Dict[str, TypedModel[Any, Any]]:
        return self._models.copy()
