"""
Phase 4 tests: GenericRepo and GenericService CRUD Mixins.
"""
import pytest
import pytest_asyncio
from pydantic import BaseModel
from sqlalchemy import Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from web_fractal.db import UnitOfWork
from web_fractal.dtos import Pagination
from web_fractal.filters import FilterBase, FilterField
from web_fractal.mixins import GenericRepo, GenericService, MultipleFound, NotExist


# ---------------------------------------------------------------------------
# Test infrastructure
# ---------------------------------------------------------------------------

class MixinBase(DeclarativeBase):
    pass


class Article(MixinBase):
    __tablename__ = "articles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    views: Mapped[int] = mapped_column(Integer, default=0)


class ArticleDM(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    title: str
    views: int


class ArticleFilter(FilterBase):
    title: FilterField[str]
    views: FilterField[int]


@pytest_asyncio.fixture
async def article_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(MixinBase.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def article_maker(article_engine):
    return async_sessionmaker(article_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def article_uow(article_maker):
    async with UnitOfWork(article_maker) as uow:
        yield uow


class ArticleRepo(GenericRepo):
    model = Article
    dm_class = ArticleDM


class ArticleService(GenericService):
    pass


# ---------------------------------------------------------------------------
# GenericRepo.create
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_single(article_uow):
    repo = ArticleRepo()
    result = await repo.create([{"title": "Hello", "views": 0}], uow=article_uow)
    assert len(result) == 1
    assert isinstance(result[0], ArticleDM)
    assert result[0].title == "Hello"
    assert result[0].id is not None


@pytest.mark.asyncio
async def test_create_multiple(article_uow):
    repo = ArticleRepo()
    data = [{"title": f"Article {i}", "views": i} for i in range(5)]
    result = await repo.create(data, uow=article_uow)
    assert len(result) == 5
    assert {r.title for r in result} == {f"Article {i}" for i in range(5)}


@pytest.mark.asyncio
async def test_create_respects_bulk_limit(article_uow):
    repo = ArticleRepo()
    repo.MAX_BULK_CREATE = 3
    data = [{"title": f"Article {i}", "views": 0} for i in range(10)]
    result = await repo.create(data, uow=article_uow)
    assert len(result) == 3


# ---------------------------------------------------------------------------
# GenericRepo.get
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_by_field(article_uow):
    repo = ArticleRepo()
    await repo.create([{"title": "FindMe", "views": 42}], uow=article_uow)
    found = await repo.get(uow=article_uow, title="FindMe")
    assert found.title == "FindMe"
    assert found.views == 42


@pytest.mark.asyncio
async def test_get_raises_not_exist(article_uow):
    repo = ArticleRepo()
    with pytest.raises(NotExist):
        await repo.get(uow=article_uow, title="Ghost")


@pytest.mark.asyncio
async def test_get_or_none_returns_none(article_uow):
    repo = ArticleRepo()
    result = await repo.get_or_none(uow=article_uow, title="Ghost")
    assert result is None


@pytest.mark.asyncio
async def test_get_or_none_returns_object(article_uow):
    repo = ArticleRepo()
    await repo.create([{"title": "Present", "views": 0}], uow=article_uow)
    result = await repo.get_or_none(uow=article_uow, title="Present")
    assert result is not None
    assert result.title == "Present"


# ---------------------------------------------------------------------------
# GenericRepo.filter
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def seeded_uow(article_maker):
    async with UnitOfWork(article_maker) as uow:
        session: AsyncSession = uow.session
        session.add_all([
            Article(title="Alpha", views=10),
            Article(title="Beta", views=20),
            Article(title="Gamma", views=30),
            Article(title="alpha_lower", views=5),
        ])
        await session.flush()
        yield uow


@pytest.mark.asyncio
async def test_filter_all(seeded_uow):
    repo = ArticleRepo()
    result = await repo.filter(ArticleFilter(), Pagination(), uow=seeded_uow)
    assert len(result) == 4


@pytest.mark.asyncio
async def test_filter_by_title_eq(seeded_uow):
    repo = ArticleRepo()
    result = await repo.filter(ArticleFilter(title__eq="Alpha"), Pagination(), uow=seeded_uow)
    assert len(result) == 1
    assert result[0].title == "Alpha"


@pytest.mark.asyncio
async def test_filter_by_views_gt(seeded_uow):
    repo = ArticleRepo()
    result = await repo.filter(ArticleFilter(views__gt=15), Pagination(), uow=seeded_uow)
    assert all(r.views > 15 for r in result)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_filter_with_pagination(seeded_uow):
    repo = ArticleRepo()
    result = await repo.filter(ArticleFilter(), Pagination(page=1, size=2), uow=seeded_uow)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_filter_pagination_page2(seeded_uow):
    repo = ArticleRepo()
    p1 = await repo.filter(ArticleFilter(), Pagination(page=1, size=2), uow=seeded_uow)
    p2 = await repo.filter(ArticleFilter(), Pagination(page=2, size=2), uow=seeded_uow)
    assert len(p1) == 2
    assert len(p2) == 2
    ids_p1 = {r.id for r in p1}
    ids_p2 = {r.id for r in p2}
    assert ids_p1.isdisjoint(ids_p2)


# ---------------------------------------------------------------------------
# GenericRepo.count
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_count_all(seeded_uow):
    repo = ArticleRepo()
    n = await repo.count(ArticleFilter(), uow=seeded_uow)
    assert n == 4


@pytest.mark.asyncio
async def test_count_filtered(seeded_uow):
    repo = ArticleRepo()
    n = await repo.count(ArticleFilter(views__gt=15), uow=seeded_uow)
    assert n == 2


# ---------------------------------------------------------------------------
# GenericRepo.update
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_by_filter(article_maker):
    async with UnitOfWork(article_maker) as uow:
        session = uow.session
        session.add(Article(title="OldTitle", views=0))
        await session.flush()

    async with UnitOfWork(article_maker) as uow:
        repo = ArticleRepo()
        rows = await repo.update(ArticleFilter(title__eq="OldTitle"), {"title": "NewTitle"}, uow=uow)
        assert rows == 1

    async with UnitOfWork(article_maker) as uow:
        repo = ArticleRepo()
        found = await repo.get(uow=uow, title="NewTitle")
        assert found.title == "NewTitle"


@pytest.mark.asyncio
async def test_update_no_match_returns_zero(article_maker):
    async with UnitOfWork(article_maker) as uow:
        repo = ArticleRepo()
        rows = await repo.update(ArticleFilter(title__eq="NoSuch"), {"views": 99}, uow=uow)
        assert rows == 0


# ---------------------------------------------------------------------------
# GenericRepo.delete
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_by_filter(article_maker):
    async with UnitOfWork(article_maker) as uow:
        session = uow.session
        session.add(Article(title="ToDelete", views=0))
        await session.flush()

    async with UnitOfWork(article_maker) as uow:
        repo = ArticleRepo()
        rows = await repo.delete(uow=uow, title="ToDelete")
        assert rows == 1

    async with UnitOfWork(article_maker) as uow:
        repo = ArticleRepo()
        found = await repo.get_or_none(uow=uow, title="ToDelete")
        assert found is None


@pytest.mark.asyncio
async def test_delete_no_match_returns_zero(article_maker):
    async with UnitOfWork(article_maker) as uow:
        repo = ArticleRepo()
        rows = await repo.delete(uow=uow, title="NoSuch")
        assert rows == 0


# ---------------------------------------------------------------------------
# GenericService (delegation + hooks)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_service_create_delegates(article_uow):
    repo = ArticleRepo()
    svc = ArticleService()
    svc.repo = repo
    result = await svc.create([{"title": "ServiceCreated", "views": 0}], uow=article_uow)
    assert len(result) == 1
    assert result[0].title == "ServiceCreated"


@pytest.mark.asyncio
async def test_service_before_create_hook(article_uow):
    repo = ArticleRepo()

    class HookedService(GenericService):
        async def before_create(self, data):
            return [{"title": d["title"].upper(), "views": d.get("views", 0)} for d in data]

    svc = HookedService()
    svc.repo = repo
    result = await svc.create([{"title": "lowercase", "views": 0}], uow=article_uow)
    assert result[0].title == "LOWERCASE"


@pytest.mark.asyncio
async def test_service_after_create_hook(article_uow):
    repo = ArticleRepo()
    called_with = []

    class HookedService(GenericService):
        async def after_create(self, objects):
            called_with.extend(objects)
            return objects

    svc = HookedService()
    svc.repo = repo
    await svc.create([{"title": "Hook", "views": 0}], uow=article_uow)
    assert len(called_with) == 1
    assert called_with[0].title == "Hook"


@pytest.mark.asyncio
async def test_service_get(article_uow):
    repo = ArticleRepo()
    svc = ArticleService()
    svc.repo = repo
    await repo.create([{"title": "SvcGet", "views": 0}], uow=article_uow)
    result = await svc.get(uow=article_uow, title="SvcGet")
    assert result.title == "SvcGet"


@pytest.mark.asyncio
async def test_service_count(seeded_uow):
    repo = ArticleRepo()
    svc = ArticleService()
    svc.repo = repo
    n = await svc.count(ArticleFilter(), uow=seeded_uow)
    assert n == 4
