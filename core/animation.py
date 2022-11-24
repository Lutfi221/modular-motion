from abc import abstractmethod
from typing import Literal, TypedDict, Union

import bpy

from .types import PropPath


class PlannedKeyframe(TypedDict):
    type: Literal["start"] | Literal["end"]
    """Type of keyframe.
    """
    object: bpy.types.Object
    """Blender object
    """
    prop_path: PropPath
    value: Union[any, None]
    """Keyframe value.
    If the value is None, the keyframe value will be the current property value.
    """


class Animation:
    @abstractmethod
    def get_planned_keyframes(self) -> list[PlannedKeyframe]:
        pass
