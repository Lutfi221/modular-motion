from __future__ import annotations
import bpy

from mathutils import Vector

from .types import PropPath

from .utils import (
    prop_path_to_data_path,
    reserve_original_prefix,
    set_value_by_prop_path,
)

from .stage import Stage
from .animation import Animation, PlannedKeyframe


class Mobject(Animation):
    """Standard Mobject (Modular Motion Object)"""

    marks: dict[str, bpy.types.Object]
    """Dictionary of empties.
    Used for attaching other mobjects via :meth:`attach_to`."""

    actions: dict[str, Animation] = {}
    """List of playable actions for the Mobject.
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
    Will be emptied every time :meth:`get_planned_keyframes` is called.
    """

    def __init__(self, stage: Stage, location: Vector, base_coll: bpy.types.Collection):
        """Create Mobject

        Parameters
        ----------
        stage : Stage
            Parent stage
        location : Vector
            Initial Mobject location (relative to stage)
        base_coll : bpy.types.Collection
            Reference collection to use
        """
        # For some reason, when initializing, this attribute can
        # contain the previous value from the previous instance.
        # That's why we empty it here.
        self._planned_keyframes = []

        self.stage = stage
        self.prefix = reserve_original_prefix(stage.prefix + ".MOB")

        # Deselect all objects.
        for obj in bpy.context.selected_objects:
            obj.select_set(False)

        base_coll_objs = base_coll.all_objects

        # Create origin empty
        origin_empty = bpy.data.objects.new(self.prefix + ".", None)
        origin_empty.empty_display_type = "ARROWS"
        origin_empty.scale = (0.1, 0.1, 0.1)
        origin_empty.location = base_coll_objs[0].location
        stage.coll.objects.link(origin_empty)
        self.object = origin_empty

        # Recursively duplicate the contents of the base collection
        with bpy.context.temp_override(selected_objects=base_coll_objs):
            bpy.ops.object.duplicate()

        # We only need to parent the objects at the top of the hierarchy.
        # Therefore we won't break the already existing parent-child relations.
        to_be_parented: list[bpy.types.Object] = [
            obj for obj in bpy.context.selected_objects if obj.parent is None
        ]

        # Parent the objects to the empty origin.
        for obj in to_be_parented:
            obj.parent = origin_empty
            obj.matrix_parent_inverse = origin_empty.matrix_local.inverted()

        # Move the empty origin to its intended location
        origin_empty.location = location

        # Move all objects to the stage collection
        for obj in bpy.context.selected_objects:
            base_coll.objects.unlink(obj)
            self.stage.coll.objects.link(obj)

        originals = base_coll.objects

        # Add prefix and rename objects to their original names.
        # This will remove the blender-generated suffixes after
        # duplication such as `.001`, `.002`, etc.
        for i, clone in enumerate(origin_empty.children_recursive):
            clone: bpy.types.Object
            clone.name = self.prefix + "." + originals[i].name

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
        self.set_prop_value("", ["location"], location)
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

    def get_planned_keyframes(self) -> list[PlannedKeyframe]:
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
            return

        data_path = prop_path_to_data_path(prop_path)

        obj.keyframe_insert(data_path=data_path, frame=self.stage.curr_time - 1)
        set_value_by_prop_path(obj, prop_path, value)
        obj.keyframe_insert(data_path=data_path, frame=self.stage.curr_time)

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
