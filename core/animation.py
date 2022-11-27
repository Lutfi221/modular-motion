from abc import abstractmethod
from typing import Literal, TypedDict, Union

import bpy

from .types import PropPath


class PlannedKeyframe(TypedDict):
    type: Literal["start"] | Literal["end"]
    """Type of keyframe.
    """
    object: bpy.types.ID
    """Blender data-block
    """
    prop_path: PropPath
    value: Union[any, None]
    """Keyframe value.
    If the value is None, the keyframe value will be the current property value.
    """


class Animation:
    @abstractmethod
    def dump_planned_keyframes(self) -> list[PlannedKeyframe]:
        """Dump and empty out planned keyframes.

        Returns
        -------
        list[PlannedKeyframe]
            List of planned keyframes
        """
        return []

    @abstractmethod
    def apply_animation(self, start: float, end: float):
        """Apply animation to the timeline.

        Parameters
        ----------
        start : float
            Start time
        end : float
            End time
        """
        pass
