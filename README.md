<p align="center"></p>
<h2 align="center">ApiQlient</h2>
<p align="center">
<a href="https://github.com/rgryta/ApiQlient/actions/workflows/main.yml"><img alt="Python package" src="https://github.com/rgryta/ApiQlient/actions/workflows/main.yml/badge.svg?branch=main"></a>
<a href="https://pypi.org/project/apiqlient/"><img alt="PyPI" src="https://img.shields.io/pypi/v/apiqlient"></a>
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
<a href="https://github.com/PyCQA/pylint"><img alt="pylint" src="https://img.shields.io/badge/linting-pylint-yellowgreen"></a>
<a href="https://github.com/rgryta/NoPrint"><img alt="NoPrint" src="https://img.shields.io/badge/NoPrint-enabled-blueviolet"></a>
</p>


## About

Want to develop an easy-to-use API client library for your HTTP server? Maybe you're already using FastAPI and want to share dataclass libraries
between your server and client projects with little to no maintenance involved?

API Quick Client (or ApiQlient) is for you then. Attach custom serializable classes to your endpoints and allow your users
to choose whether they want to use sync or async scheme. You don't need to set up anything else by yourself.

See the [documentation](https://github.com/rgryta/ApiQlient/#Usage) for more information.

## Requirements

ApiQlient utilizes `starlette` as it's base - similarly to FastAPI. Additionally, it requires `yarl` package for URL parsing
and `urllib3` for its' synchronous and `aiohttp` for asynchronous backends.

On top of that it provides several optional functionalities. You can use it with `dataclass_wizard`-defined classes or with `pydantic` model.
If you don't want to define custom classes, you can fall back to using `munch` instead.

## Installation

Pull straight from this repo to install manually or just use pip: `pip install apiqlient` will do the trick.

## Usage

ApiQlient supports both: synchronous and asynchronous execution. The manner of which to use is decided by detecting which
context manager we enter (`with` or `async with`). If we use `with` - `urllib3` will be used. If `async with` - `aiohttp`.

Below you can see and example using dataclass_wizard package.

```python
import asyncio
from dataclasses import dataclass

from apiqlient import ApiQlient
from dataclass_wizard import JSONSerializable, json_field

client = ApiQlient(base_url="https://jsonplaceholder.typicode.com/")


@client.router.get("/{id}")
@dataclass
class JSONPlaceholderDCW(JSONSerializable):
    id: int
    title: str
    completed: bool
    user_id: int = json_field("userId")


async def async_main():
    async with client:
        requests = [client.get(f"/todos/{i + 1}") for i in range(100)]
        responses = await asyncio.gather(*[request.response() for request in requests])
        objects = await asyncio.gather(*[response.object() for response in responses])
    print(f"My fist async object: {objects[0]}")


def sync_main():
    with client:
        requests = [client.get(f"/todos/{i + 1}") for i in range(100)]
        responses = [request.response() for request in requests]
        objects = [response.object() for response in responses]
    print(f"My first sync object: {objects[0]}")


asyncio.run(async_main())
```

As this project is meant to replicate behaviour of FastAPI and uses starlette as it's core functionality, it also supports 
router-based structure. Meaning that you can spread your dataclasses/models between different modules, and attach them to 
routers which will later be included into the app. See `example.py` for reference.

### Performance

Performance will differ depending on the environment. However, on my local machine, at the time of writing this, these were the
results from the `example.py` file:

```text
ASYNC
Finished parsing 100 requests in 8.913177967071533 seconds

SYNC
Finished parsing 100 requests in 19.49611806869507 seconds
```

No obvious difference was spotted between using `dataclass_wizard`, `pydantic` or `munch`.

## Development

### Installation

Install virtual environment and apiqlient package in editable mode with dev dependencies.

```bash
python -m venv venv
source venv/bin/activate
pip install -e .[dev]
```

### How to?

Automate as much as we can, see configuration in `pyproject.toml` file to see what are the flags used.

```bash
staging format  # Reformat the code
staging lint    # Check for linting issues
staging test    # Run unit tests and coverage report
```