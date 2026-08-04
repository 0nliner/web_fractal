from web_fractal.mixins import GenericRepo

from .dtos import UserDM
from .interfaces import UserRepoABC
from .models import User


class UserRepo(GenericRepo, UserRepoABC):
    model = User
    dm_class = UserDM
    # session_maker is set by bundle.py post-inject (async_sessionmaker is outside project root)
