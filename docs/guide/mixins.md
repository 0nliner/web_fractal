# CRUD mixins

`GenericRepo` implements the operations every repository repeats;
`GenericService` wraps it with hooks.

```python
from web_fractal.mixins import GenericRepo, GenericService

class UserRepo(GenericRepo):
    model = User
    dm_class = UserDM
    session_maker: async_sessionmaker

class UserService(GenericService):
    repo: UserRepo
```

## Repository API

Every method takes the unit of work by keyword:

```python
await repo.create([{"name": "Иван"}], uow=uow)          # -> list[UserDM]
await repo.get(uow=uow, id=1)                            # NotExist / MultipleFound
await repo.get_or_none(uow=uow, id=1)                    # -> UserDM | None
await repo.filter(user_filter, pag, uow=uow)             # -> list[UserDM]
await repo.update(user_filter, {"age": 31}, uow=uow)     # -> affected rows
await repo.delete(uow=uow, id=1)                         # -> affected rows
await repo.count(user_filter, uow=uow)                   # -> int
```

`get` raises `NotExist` when nothing matches and `MultipleFound` when more than
one row does — both from `web_fractal.mixins`. Catching them in a controller and
mapping to 404/409 is the intended flow.

Results are converted to `dm_class`; ORM objects do not leave the repository.

## Service hooks

```python
class UserService(GenericService):
    repo: UserRepo

    async def before_create(self, data: list[dict]) -> list[dict]:
        for row in data:
            row["name"] = row["name"].strip()
        return data

    async def after_create(self, objects: list) -> list:
        await self.notifier.send(objects)
        return objects
```

Everything else is delegated to the repository, so a service that has no extra
behaviour is three lines and still worth having: the controller depends on the
service interface, and the day logic appears there is nothing to rewire.

## When to stop using them

Override a method when the domain differs — a soft-delete `delete`, a `filter`
with a mandatory join. When most methods are overridden, the mixin is no longer
carrying weight: write the repository directly. It is a shortcut, not a
contract.
