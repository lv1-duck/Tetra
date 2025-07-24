from dataclasses import dataclass
from kivy.metrics import dp


# CLASSES FOR CONSTANTS
@dataclass
class Theme:
    BACKGROUND = (30/255, 31/255, 40/255, 1)
    HEADER_BG = (46/255, 47/255, 62/255, 1)
    BUTTON_BG = (45/255, 95/255, 145/255, 1)
    LIST_BG = (41/255, 43/255, 62/255, 1)
    ITEM_BG = (52/255, 54/255, 73/255, 1)
    TEXT_PRIMARY = (1, 1, 1, 1)
    TEXT_SECONDARY = (0.7, 0.7, 0.7, 1)
    SUCCESS = (0.2, 0.8, 0.2, 1)
    ERROR = (0.8, 0.2, 0.2, 1)

@dataclass
class Sizes:
    PADDING = dp(15)
    SPACING = dp(12)
    HEADER_HEIGHT = dp(50)
    BUTTON_HEIGHT = dp(60)
    LIST_ITEM_HEIGHT = dp(55)
    RADIUS_LARGE = dp(25)
    RADIUS_MEDIUM = dp(18)
    RADIUS_SMALL = dp(12)

