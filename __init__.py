bl_info = {
    "name": "modular-motion",
    "author": "Lutfi Azis",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "description": "Modular and programmatic animation",
}


from .core.mobject import Mobject
from .core.animation import Animation
from .core.stage import Stage
from .core.utils import *


def register():
    pass


def unregister():
    pass
