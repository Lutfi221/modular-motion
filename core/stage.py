from abc import abstractmethod
import bpy
from mathutils import Vector


class Stage:
    coll: bpy.types.Collection
    """Collection used for stage output
    """

    origin: Vector
    """The stage origin (global)
    """

    def __init__(self):
        pass

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
        """
        pass
