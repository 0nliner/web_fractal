from web_fractal.mixins import GenericRepo

from .dtos import CardDM
from .interfaces import CardRepoABC
from .models import Card


class CardRepo(GenericRepo, CardRepoABC):
    model = Card
    dm_class = CardDM
    # session_maker is set by bundle.py post-inject
