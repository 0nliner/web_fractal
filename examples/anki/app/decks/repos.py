from web_fractal.mixins import GenericRepo

from .dtos import DeckDM
from .interfaces import DeckRepoABC
from .models import Deck


class DeckRepo(GenericRepo, DeckRepoABC):
    model = Deck
    dm_class = DeckDM
    # session_maker is set by bundle.py post-inject
