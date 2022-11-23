from abc import abstractmethod
import bpy
from mathutils import Vector

from .utils import reserve_original_prefix


class Stage:
    coll: bpy.types.Collection
    """Collection used for stage output
    """

    origin = Vector((0, 0, 0))
    """The stage origin (global)
    """

    prefix: str
    """Prefix to append to blender object names inside the stage collection.
    Used to prevent name collisions.
    """

    def __init__(self):
        self.prefix = reserve_original_prefix("_M.S")

    @abstractmethod
    def construct(self):
        """Construct and populate the stage."""
        pass

    def play(self, *args, duration=1):
        """Play animations

        Parameters
        ----------
        args
            Animations to be played
        duration : int, optional
            Duration, by default 1
        """
        pass
