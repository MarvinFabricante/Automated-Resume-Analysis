from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional

from fastapi import APIRouter


@dataclass(frozen=True)
class RouteDefinition:
    path: str
    methods: tuple[str, ...] = field(default_factory=tuple)
    kwargs: dict[str, Any] = field(default_factory=dict)
    is_websocket: bool = False


def route(path: str, *, methods: Iterable[str], **kwargs: Any) -> Callable:
    def decorator(endpoint: Callable) -> Callable:
        routes = list(getattr(endpoint, "__controller_routes__", []))
        routes.append(
            RouteDefinition(
                path=path,
                methods=tuple(method.upper() for method in methods),
                kwargs=kwargs,
            )
        )
        setattr(endpoint, "__controller_routes__", routes)
        return endpoint

    return decorator


def Get(path: str, **kwargs: Any) -> Callable:
    return route(path, methods=("GET",), **kwargs)


def Post(path: str, **kwargs: Any) -> Callable:
    return route(path, methods=("POST",), **kwargs)


def Put(path: str, **kwargs: Any) -> Callable:
    return route(path, methods=("PUT",), **kwargs)


def Patch(path: str, **kwargs: Any) -> Callable:
    return route(path, methods=("PATCH",), **kwargs)


def Delete(path: str, **kwargs: Any) -> Callable:
    return route(path, methods=("DELETE",), **kwargs)


def ApiRoute(path: str, *, methods: Iterable[str], **kwargs: Any) -> Callable:
    return route(path, methods=methods, **kwargs)


def WebSocketRoute(path: str, **kwargs: Any) -> Callable:
    def decorator(endpoint: Callable) -> Callable:
        routes = list(getattr(endpoint, "__controller_routes__", []))
        routes.append(
            RouteDefinition(
                path=path,
                kwargs=kwargs,
                is_websocket=True,
            )
        )
        setattr(endpoint, "__controller_routes__", routes)
        return endpoint

    return decorator


class BaseController:
    prefix: str = ""
    tags: Optional[list[str]] = None
    router_kwargs: dict[str, Any] = {}

    def __init__(self):
        self.router = APIRouter(
            prefix=self.prefix,
            tags=self.tags,
            **self.router_kwargs,
        )
        self._register_annotated_routes()

    def _register_annotated_routes(self) -> None:
        for method_name, method in self._iter_controller_methods():
            endpoint = getattr(self, method_name)
            for route_definition in getattr(method, "__controller_routes__", []):
                if route_definition.is_websocket:
                    self.router.websocket(
                        route_definition.path,
                        **route_definition.kwargs,
                    )(endpoint)
                    continue

                self.router.add_api_route(
                    route_definition.path,
                    endpoint,
                    methods=list(route_definition.methods),
                    **route_definition.kwargs,
                )

    @classmethod
    def _iter_controller_methods(cls):
        for controller_cls in reversed(cls.__mro__):
            if controller_cls is BaseController:
                continue
            for method_name, method in controller_cls.__dict__.items():
                if callable(method) and hasattr(method, "__controller_routes__"):
                    yield method_name, method
