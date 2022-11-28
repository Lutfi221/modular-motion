from __future__ import annotations
import bpy
from mathutils import Vector

from ..utils import (
    keyframe_insert,
    prop_path_to_data_path,
    reserve_original_prefix,
    set_value_by_prop_path,
)

from ..stage import Stage
from .custom_mobject_prop import CustomMobjectProperty
from ..types import PropPath
from ..animation import Animation, PlannedKeyframe


class Mobject(Animation):
    """Standard Mobject (Modular Motion Object)"""

    marks: dict[str, bpy.types.Object] = {}
    """Dictionary of empties.
    Used for attaching other mobjects via :meth:`attach_to`."""

    actions: list[Animation]
    """List of playable actions.
    """

    custom_properties: dict[str, CustomMobjectProperty]
    """Custom user-defined Mobject properties.
    """

    prefix: str
    """Mobject prefix.
    """

    object: bpy.types.Object
    """Origin blender object
    """

    stage: Stage

    _in_animate_mode = False
    """If Mobject in animate mode.
    Enabled by accessing :meth:`animate` and disabled by
    calling :meth:`apply_animation`"""

    _planned_keyframes: list[PlannedKeyframe]
    """Keyframes to be applied to the timeline.
    Used while :attr:`_in_animate_mode` is True.
    Will be emptied every time :meth:`dump_planned_keyframes` is called.
    """

    def __init__(self, stage: Stage):
        self.stage = stage
        self.prefix = reserve_original_prefix(stage.prefix + ".MOB")

    def move_to(self, location: Vector) -> Mobject:
        """Move Mobject to location

        Parameters
        ----------
        location : Vector
            New location

        Returns
        -------
        Mobject
            Self
        """
        self.set_prop_value("", ["location"], location + self.stage.origin)
        return self

    def shift(self, offset: Vector) -> Mobject:
        """Shift mobject by offset.

        Parameters
        ----------
        offset : Vector
            Translation vector

        Returns
        -------
        Mobject
            Self
        """
        self.move_to(self.object.location + offset)
        return self

    def set_rotation(self, rotation_euler: Vector) -> Mobject:
        """Set mobject rotation. Replaces previous rotation.

        Parameters
        ----------
        rotation_euler : Vector
            Euler rotation vector

        Returns
        -------
        Mobject
            Self
        """
        self.set_prop_value("", ["rotation_euler"], rotation_euler)
        return self

    def rotate(self, rotation_euler: Vector) -> Mobject:
        """Rotate mobject. Rotation vector is added to previous rotation.

        Parameters
        ----------
        rotation_euler : Vector
            Euler rotation vector

        Returns
        -------
        Mobject
            Self
        """
        self.set_rotation(rotation_euler + self.object.rotation_euler)
        return self

    def set_scale(self, scale: Vector) -> Mobject:
        """Set mobject scale. Replaces previous scale.

        Parameters
        ----------
        scale : Vector
            Scale vector

        Returns
        -------
        Mobject
            Self
        """
        self.set_prop_value("", ["scale"], scale)
        return self

    def scale(self, scale: Vector) -> Mobject:
        """Scales mobject by multiplying new scale with
        the previous scale.

        Parameters
        ----------
        scale : Vector
            Scale vector

        Returns
        -------
        Mobject
            Self
        """
        self.set_scale(self.object.scale * scale)
        return self

    @property
    def animate(self) -> Mobject:
        """Enables mobject animation

        Returns
        -------
        Mobject
            Self
        """
        self._in_animate_mode = True
        return self

    def dump_planned_keyframes(self) -> list[PlannedKeyframe]:
        """Get planned keyframes for animation.
        Any regular modular_motion user should not call this.
        Calling this will also clear :attr:`_planned_keyframes`
        and disables animation mode.

        Returns
        -------
        list[PlannedKeyframe]
            List of planned keyframes
        """
        p = self._planned_keyframes
        self._planned_keyframes = []
        self._in_animate_mode = False
        return p

    def set_prop_value(self, obj_name, prop_path: PropPath, value: any) -> Mobject:
        """Set property value of an object.
        Use this method to change property values insted of modifying them
        directly so it will be compatible with :meth:`animate`

        Parameters
        ----------
        obj_name : str, optional
            Object name
        prop_path : PropPath
            Property path
        value : any
            New value for the property

        Returns
        -------
        Mobject
            Self
        """
        target = self.prefix + "." + obj_name
        obj = bpy.data.objects[target]
        if self._in_animate_mode:
            self._planned_keyframes.append(
                {"object": obj, "type": "start", "prop_path": prop_path, "value": None}
            )
            self._planned_keyframes.append(
                {"object": obj, "type": "end", "prop_path": prop_path, "value": value}
            )
            return self

        data_path = prop_path_to_data_path(prop_path)

        keyframe_insert(obj, data_path, self.stage.curr_time - 1)
        set_value_by_prop_path(obj, prop_path, value)
        keyframe_insert(obj, data_path, self.stage.curr_time)
        return self

    def customize(self, property: str, value: str | any) -> Mobject:
        """Customize a user-defined mobject property.

        Parameters
        ----------
        property : str
            Custom property name
        value : str | any
            Value

        Returns
        -------
        Mobject
            Self
        """
        prop = self.custom_properties[property]
        if self._in_animate_mode:
            prop.set_animate_mode(True)
            self._planned_keyframes.extend(prop.set_value(value))
            prop.set_animate_mode(False)
        else:
            prop.set_value(value)
        return self
