from __future__ import annotations

from mathutils import Vector


class Playable:
    def __init__(self):
        pass

    def play(self, start_time: float, duration: float) -> None:
        pass


class Mobject:
    """Standard Mobject (Modular Motion Object)"""

    marks: dict[str, Vector]
    """Dictionary of named points (relative to mobject)"""

    actions: dict[str, Playable] = {}
    """List of playable actions for the Mobject
    """

    def __init__(self):
        pass

    def customize(self, property: str, value: str | any) -> Mobject:
        """Customize a mobject property.

        Parameters
        ----------
        property : str
            Property name
        value : str | any
            Value

        Returns
        -------
        Mobject
            Self
        """
        pass
