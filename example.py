import time
import asyncio
from dataclasses import dataclass

from pydantic import Field, BaseModel
from dataclass_wizard import JSONSerializable, json_field

from apiqlient import ApiQlient, ClientRouter

client = ApiQlient(base_url="https://jsonplaceholder.typicode.com/")
router = ClientRouter(prefix="/todos")


@router.get("/{id}")  # Or use @client.router.get() if you have a simple project
@dataclass
class JSONPlaceholderDCW(JSONSerializable):
    id: int
    title: str
    completed: bool
    user_id: int = json_field("userId")


# Alternatively use pydantic BaseModel
# @router.get("/{id}")
class JSONPlaceholderPDT(BaseModel):
    user_id: int = Field(alias="userId")
    id: int = Field()
    title: str = Field()
    completed: bool = Field()


client.include_router(router=router)


async def main():
    todos = [f"/todos/{i+1}" for i in range(100)]

    start = time.time()
    print("ASYNC")
    async with client:
        rqs = [client.get(todo) for todo in todos]
        responses = await asyncio.gather(*[request.response() for request in rqs])
        objects = []
        for response in responses:
            objects.append(await response.object())
    print(f"Finished parsing {len(objects)} requests in {time.time()-start} seconds")
    print(f"Example response: {objects[0]}.")

    start = time.time()
    print("SYNC")
    with client:
        rqs = [client.get(todo) for todo in todos]
        responses = [request.response() for request in rqs]
        objects = []
        for response in responses:
            objects.append(response.object())
    print(f"Finished parsing {len(objects)} requests in {time.time()-start} seconds")
    print(f"Example response: {objects[0]}.")


asyncio.run(main())
