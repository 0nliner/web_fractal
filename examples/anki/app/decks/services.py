from web_fractal.mixins import GenericService

from .interfaces import DeckRepoABC, DeckServiceABC


class DeckService(GenericService, DeckServiceABC):
    repo: DeckRepoABC  # archtool injects DeckRepo instance
