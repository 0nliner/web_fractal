from web_fractal.mixins import GenericService

from .interfaces import UserRepoABC, UserServiceABC


class UserService(GenericService, UserServiceABC):
    repo: UserRepoABC  # archtool injects UserRepo instance
