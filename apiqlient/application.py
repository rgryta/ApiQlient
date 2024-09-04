"""
ApiQlient is a simple HTTP/HTTPS client
"""

from __future__ import annotations

import functools
import dataclasses
from typing import Coroutine

# pylint:disable=ungrouped-imports
from yarl import URL
from aiohttp import ClientSession, ClientResponse
from urllib3 import HTTPResponse, HTTPConnectionPool, HTTPSConnectionPool
from aiohttp.client import _RequestContextManager
from starlette.routing import Match
from starlette.applications import Starlette

try:
    import munch
except ImportError:
    munch = None

try:
    import dataclass_wizard
except ImportError:
    dataclass_wizard = None

try:
    import pydantic
except ImportError:
    pydantic = None


from .router import ClientRouter


class BaseRequest:  # pylint:disable=too-few-public-methods
    """
    Base request class
    """

    _response: ClientResponse | HTTPResponse = None

    def __init__(self, dataclass, client: ApiQlient, method: str, url, **kwargs):
        self.cls = dataclass
        self._client = client
        self._method = method

        self._url = url
        self._kwargs = kwargs


class BaseResponse:  # pylint:disable=too-few-public-methods
    """
    Base response class for object parsing
    """

    url: str = "N/A"  # Present in both: HTTPResponse and ClientResponse

    def _from_dict(
        self, /, data: dict, cls: dataclasses.dataclass | pydantic.BaseModel | None, none_error: bool = False
    ):
        """Parse response object from dict"""
        try:
            if cls and any([dataclass_wizard, pydantic]):
                if dataclass_wizard and issubclass(cls, dataclass_wizard.JSONSerializable):
                    return cls.from_dict(data)
                if pydantic and issubclass(cls, pydantic.BaseModel):
                    return cls.parse_obj(data)
                return cls(**data)
            if munch:
                return munch.munchify(data)
        except Exception as exc:
            if none_error:
                return None
            raise type(exc)(f"Error trying to retrieve {self.url}: [{exc}]") from exc
        raise ValueError("munch is not installed")


class Request(BaseRequest):
    """
    Request class for synchronous HTTP(S) requests
    """

    class Response(HTTPResponse, BaseResponse):
        """
        Response class for synchronous HTTP(S) requests
        """

        def _object(self, cls: type = None, *, none_error: bool = False):
            """
            Helper function to pass internal class argument through functools.partial
            """
            return self._from_dict(cls=cls, data=self.json(), none_error=none_error)

        def object(self, *, none_error: bool = False) -> dataclasses.dataclass | munch.Munch | pydantic.BaseModel:
            """
            Return parsed response object

            :keyword none_error: If True, return None if an error occurs during json() -> object parsing
            :raises json.JSONDecodeError: If the response body is not valid JSON
            """
            return self._object(none_error=none_error)

    _response: HTTPResponse = None

    def __init__(self, dataclass, client: ApiQlient, method: str, url, **kwargs):
        super().__init__(dataclass, client, method, url, **kwargs)

        self.method = getattr(type(client.client), "request")  # Get HTTP(S)ConnectionPool class' request method

    def response(
        self,
    ) -> Request.Response:  # In actuality this is HTTPResponse always, just for type hints
        """
        Return response object
        """
        with self:
            assert isinstance(self._response, Request.Response)
            return self._response

    def __enter__(self):
        if self._response is None:
            assert isinstance(self._client.client, (HTTPConnectionPool, HTTPSConnectionPool))
            self._response = self.method(self._client.client, self._method.upper(), self._url, **self._kwargs)
            self._response.__class__ = Request.Response

            # Bind dataclass to object parsing
            self._response._object = functools.partial(self._response._object, cls=self.cls)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class AsyncRequest(BaseRequest):
    """
    Request class for asynchronous HTTP(S) requests
    """

    class Response(ClientResponse, BaseResponse):
        """
        Response class for asynchronous HTTP(S) requests
        """

        async def _object(self, cls: type = None, none_error: bool = False):
            """
            Helper function to pass internal class argument through functools.partial
            """
            return self._from_dict(cls=cls, data=await self.json(content_type=None), none_error=none_error)

        async def object(self, *, none_error: bool = False) -> dataclasses.dataclass | munch.Munch | pydantic.BaseModel:
            """
            Return parsed response object

            :keyword none_error: If True, return None if an error occurs during json() -> object parsing
            :raises json.JSONDecodeError: If the response body is not valid JSON
            """
            return await self._object(none_error=none_error)

    _request: _RequestContextManager = None
    _response: ClientResponse = None

    def __init__(self, dataclass, client: ApiQlient, method: str, url, **kwargs):
        super().__init__(dataclass, client, method, url, **kwargs)

        self.method = getattr(ClientSession, self._method.lower())

        assert isinstance(self._client.client, ClientSession)
        self._request = self.method(self._client.client, self._url, **self._kwargs)

    async def response(self) -> AsyncRequest.Response:
        """
        Return response object
        """
        async with self:
            assert isinstance(self._response, AsyncRequest.Response)
            return self._response

    async def __aenter__(self):
        if self._response is None:
            self._response = await self._request
            self._response.__class__ = AsyncRequest.Response

            # Bind dataclass to object parsing
            self._response._object = functools.partial(self._response._object, cls=self.cls)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class ApiQlient(Starlette):  # pylint:disable=too-many-instance-attributes
    """
    ApiQlient client
    """

    client: ClientSession | HTTPConnectionPool
    methods = ("get", "head", "post", "put", "delete", "connect", "options", "trace", "patch")

    async_scope: bool | None = None

    def __init__(self, base_url: URL | str, *args, **kwargs):
        super().__init__()

        if not isinstance(base_url, (URL, str)):
            raise ValueError("base_url must be a string or URL object")

        url = URL(base_url) if isinstance(base_url, str) else base_url

        if url.host:
            self.scheme = url.scheme
            self.host = url.host
            self.port = url.port
        else:
            self.scheme = "http"
            self.host = url.path
            self.port = 80

        self._args = args
        self._kwargs = kwargs
        self._paths = {}

        self.router: ClientRouter = ClientRouter()

    def include_router(self, router: ClientRouter, *, prefix=""):
        """Include router in client"""
        self.router.include_router(router, prefix=prefix)

    # Use aiohttp for async requests
    async def __aenter__(self):
        self._make_context(async_scope=True)
        args = (f"{self.scheme}://{self.host}:{self.port}", *self._args)
        self.client = await ClientSession(*args, **self._kwargs).__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        assert isinstance(self.client, ClientSession)
        await self.client.__aexit__(exc_type, exc_val, exc_tb)
        self._remove_context()

    def __enter__(self):
        self._make_context(async_scope=False)
        if self.scheme == "http":
            self.client = HTTPConnectionPool(self.host, self.port, *self._args, **self._kwargs)
        elif self.scheme == "https":
            self.client = HTTPSConnectionPool(self.host, self.port, *self._args, **self._kwargs)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        assert isinstance(self.client, HTTPConnectionPool)
        self.client.close()
        self._remove_context()

    def _make_context(self, async_scope: bool):
        """
        Make context for client
        """

        def generate_method(method):
            """
            Generate method for client
            """

            def func(method: str, path: str, **kwargs):
                return self._route(path, method, **kwargs)

            return functools.partial(func, method)

        self.async_scope = async_scope

        for method in self.methods:
            setattr(self, method, generate_method(method))

    def _remove_context(self):
        """
        Remove context for client
        """
        self.async_scope = None

        for method in self.methods:
            setattr(self, method, lambda *_, **__: (_ for _ in ()).throw(NotImplementedError("Client not in context")))

    def _route(self, path, method, **kwargs):
        """
        Route request to appropriate endpoint
        """

        def _path():
            scope = {"type": "http", "path": path, "method": method.upper()}
            routes = {Match.FULL: [], Match.PARTIAL: []}
            for route in self.routes:
                match, _ = route.matches(scope=scope)
                if match != Match.NONE:
                    routes[match].append(route)
            if routes[Match.FULL]:
                return routes[Match.FULL][0]
            if routes[Match.PARTIAL]:
                return routes[Match.PARTIAL][0]
            return None

        _route = _path()
        cls = Request if not self.async_scope else AsyncRequest
        return cls(dataclass=_route.endpoint if _route else None, client=self, method=method, url=path, **kwargs)

    # Define "get", "head", "post", "put", "delete", "connect", "options", "trace", "patch" methods for hints
    def get(self, path, **kwargs) -> Request | Coroutine[AsyncRequest]:  # pylint:disable=missing-function-docstring
        raise NotImplementedError("When defining paths use `@client.router.get(...)` instead")

    def head(self, path, **kwargs) -> Request | Coroutine[AsyncRequest]:  # pylint:disable=missing-function-docstring
        raise NotImplementedError("When defining paths use `@client.router.head(...)` instead")

    def post(self, path, **kwargs) -> Request | Coroutine[AsyncRequest]:  # pylint:disable=missing-function-docstring
        raise NotImplementedError("When defining paths use `@client.router.post(...)` instead")

    def put(self, path, **kwargs) -> Request | Coroutine[AsyncRequest]:  # pylint:disable=missing-function-docstring
        raise NotImplementedError("When defining paths use `@client.router.put(...)` instead")

    def delete(self, path, **kwargs) -> Request | Coroutine[AsyncRequest]:  # pylint:disable=missing-function-docstring
        raise NotImplementedError("When defining paths use `@client.router.delete(...)` instead")

    def connect(self, path, **kwargs) -> Request | Coroutine[AsyncRequest]:  # pylint:disable=missing-function-docstring
        raise NotImplementedError("When defining paths use `@client.router.connect(...)` instead")

    def options(self, path, **kwargs) -> Request | Coroutine[AsyncRequest]:  # pylint:disable=missing-function-docstring
        raise NotImplementedError("When defining paths use `@client.router.options(...)` instead")

    def trace(self, path, **kwargs) -> Request | Coroutine[AsyncRequest]:  # pylint:disable=missing-function-docstring
        raise NotImplementedError("When defining paths use `@client.router.trace(...)` instead")

    def patch(self, path, **kwargs) -> Request | Coroutine[AsyncRequest]:  # pylint:disable=missing-function-docstring
        raise NotImplementedError("When defining paths use `@client.router.patch(...)` instead")
