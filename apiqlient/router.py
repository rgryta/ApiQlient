"""
ApiQlient client router
"""

from __future__ import annotations

import warnings
from typing import Callable

from starlette.routing import Route, Router


class ClientRoute(Route):
    """
    Custom route for client application
    """

    def __init__(self, path, endpoint, *, methods, list_of: bool = False, **kwargs):
        super().__init__(path, endpoint, methods=methods, **kwargs)
        self.list_of = list_of


class ClientRouter(Router):
    """
    A router for client application
    """

    def __init__(self, *, prefix="", **kwargs):
        super().__init__(**kwargs)
        self.prefix = prefix

    def include_router(self, router: ClientRouter, *, prefix=""):
        """
        Include all the routes from a router
        """
        if prefix:
            assert prefix.startswith("/"), "A path prefix must start with '/'"
            assert not prefix.endswith("/"), "A path prefix must not end with '/', as the routes will start with '/'"
        else:
            for r in router.routes:
                path = getattr(r, "path")  # noqa: B009
                name = getattr(r, "name", "unknown")
                if path is not None and not path:
                    raise ValueError(f"Prefix and path cannot be both empty (path operation: {name})")
        for route in router.routes:
            if isinstance(route, ClientRoute):
                self.add_client_route(
                    path=prefix + route.path,
                    endpoint=route.endpoint,
                    methods=route.methods,
                    list_of=route.list_of,
                )
            elif isinstance(route, Route):
                methods = list(route.methods or [])
                self.add_route(
                    path=prefix + route.path,
                    endpoint=route.endpoint,
                    methods=methods,
                    include_in_schema=route.include_in_schema,
                    name=route.name,
                )

    def add_client_route(self, path, endpoint, methods, list_of: bool = False):
        """
        Add a new client route to the router
        """
        route = ClientRoute(
            path=self.prefix + path,
            endpoint=endpoint,
            methods=methods,
            list_of=list_of,
        )
        self.routes.append(route)

    def client_route(self, path, methods, list_of: bool = False):
        """
        Define a new client route
        """

        def decorator(func) -> Callable:
            self.add_client_route(path=path, endpoint=func, methods=methods, list_of=list_of)
            return func

        return decorator

    def get(self, path: str, list_of: bool = False):
        """
        The GET method requests a representation of the specified resource.
        Requests using GET should only retrieve data.
        """
        return self.client_route(path=path, methods=["GET"], list_of=list_of)

    def head(self, path: str, list_of: bool = False):  # pylint:disable=unused-argument
        """
        The HEAD method asks for a response identical to a GET request,
        but without the response body.

        Warning: A response to a HEAD method should not have a body. If it has one anyway,
        that body must be ignored: any representation headers that might describe
        the erroneous body are instead assumed to describe the response which a similar GET
        request would have received.
        """
        warnings.warn(
            "The `head` decorator is not supported as HEAD request should not have a body.",
            DeprecationWarning,
        )
        raise NotImplementedError

    def post(self, path: str, list_of: bool = False):
        """
        The POST method submits an entity to the specified resource,
        often causing a change in state or side effects on the server.
        """
        return self.client_route(path=path, methods=["POST"], list_of=list_of)

    def put(self, path: str, list_of: bool = False):
        """
        The PUT method replaces all current representations of the target
        resource with the request payload.
        """
        return self.client_route(path=path, methods=["PUT"], list_of=list_of)

    def delete(self, path: str, list_of: bool = False):
        """
        The DELETE method deletes the specified resource.
        """
        return self.client_route(path=path, methods=["DELETE"], list_of=list_of)

    def connect(self, path: str, list_of: bool = False):  # pylint:disable=unused-argument
        """
        The CONNECT method establishes a tunnel to the server identified by the target resource.
        """
        warnings.warn(
            "The `connect` decorator is not supported as CONNECT request should doesn't have a body.",
            DeprecationWarning,
        )
        raise NotImplementedError

    def options(self, path: str, list_of: bool = False):
        """
        The OPTIONS method describes the communication options for the target resource.
        """
        return self.client_route(path=path, methods=["OPTIONS"], list_of=list_of)

    def trace(self, path: str, list_of: bool = False):
        """
        The TRACE method performs a message loop-back test along the path to the target resource.
        """
        return self.client_route(path=path, methods=["TRACE"], list_of=list_of)

    def patch(self, path: str, list_of: bool = False):
        """
        The PATCH method applies partial modifications to a resource.
        """
        return self.client_route(path=path, methods=["PATCH"], list_of=list_of)
