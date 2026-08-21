# CRUD-миксины

`GenericRepo` реализует операции, которые повторяет каждый репозиторий,
`GenericService` оборачивает его хуками.

```python
from web_fractal.mixins import GenericRepo, GenericService

class UserRepo(GenericRepo):
    model = User
    dm_class = UserDM
    session_maker: async_sessionmaker

class UserService(GenericService):
    repo: UserRepo
```

## API репозитория

Единица работы передаётся именованным аргументом:

```python
await repo.create([{"name": "Иван"}], uow=uow)          # -> list[UserDM]
await repo.get(uow=uow, id=1)                            # NotExist / MultipleFound
await repo.get_or_none(uow=uow, id=1)                    # -> UserDM | None
await repo.filter(user_filter, pag, uow=uow)             # -> list[UserDM]
await repo.update(user_filter, {"age": 31}, uow=uow)     # -> сколько строк задето
await repo.delete(uow=uow, id=1)                         # -> сколько строк задето
await repo.count(user_filter, uow=uow)                   # -> int
```

`get` бросает `NotExist`, если не нашлось ничего, и `MultipleFound`, если
нашлось больше одного, — оба из `web_fractal.mixins`. Ловить их в контроллере и
превращать в 404/409 — и есть предполагаемый поток.

Результат приводится к `dm_class`: ORM-объекты за пределы репозитория не
выходят.

## Хуки сервиса

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

Остальное делегируется репозиторию, поэтому сервис без своей логики — это три
строки, и заводить его всё равно стоит: контроллер зависит от интерфейса
сервиса, и в день, когда логика появится, переразводить нечего.

## Когда пора перестать ими пользоваться

Метод переопределяют, когда домен отличается: мягкое удаление в `delete`,
обязательный join в `filter`. Если переопределено большинство методов, миксин
уже ничего не несёт — пишите репозиторий напрямую. Это ускоритель, а не
контракт.
