from __future__ import annotations
from abc import abstractmethod
import bpy

from mathutils import Vector

from .errors import CustomPropertyUnanimatable

from .types import DomainRangeMap, ExtendedPropPath, PropPath

from .utils import (
    interp,
    keyframe_insert,
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

    def __init__(
        self,
        stage: Stage,
        location: Vector,
        base_coll: bpy.types.Collection,
        duplicate_linked=True,
    ):
        """Create Mobject

        Parameters
        ----------
        stage : Stage
            Parent stage
        location : Vector
            Initial Mobject location (relative to stage)
        base_coll : bpy.types.Collection
            Reference collection to use
        duplicate_linked : bool
            Should the newly created Blender objects
            be linked to the original base object, defaults to True
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
            bpy.ops.object.duplicate(linked=duplicate_linked)

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
        origin_empty.location = location + self.stage.origin

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


class CustomMobjectProperty:
    """User-defined mobject property

    Raises
    ------
    CustomPropertyUnanimatable
        An attempt to animate an unanimatable property was made.
    """

    mobject: Mobject
    is_animatable = True
    _in_animate_mode = False

    def __init__(self, mobject):
        self.mobject = mobject

    @abstractmethod
    def set_value(self, value: any) -> list[PlannedKeyframe] | None:
        """Set value of the custom mobject property.

        Parameters
        ----------
        value : any
            Value

        Returns
        -------
        list[PlannedKeyframe]
            If custom property is in animate mode (enabled via :meth:`set_animate_mode`),
            then it will return a list of planned keyframes instead of directly modifying the
            timeline.
        """
        pass

    def set_animate_mode(self, mode: bool):
        if not self.is_animatable:
            raise CustomPropertyUnanimatable()
        self._in_animate_mode = mode


class SimpleCustomMobjectProperty(CustomMobjectProperty):
    e_prop_paths: list[ExtendedPropPath]
    _mappings: list[DomainRangeMap] = []
    """List of domain range mappings.
    Index must match with the corresponding :attr:`e_prop_paths`.
    """

    def __init__(
        self, mobject: Mobject, e_prop_paths: list[ExtendedPropPath], animatable=True
    ):
        """Create a simple :class:`CustomMobjectProperty` from extended property paths.

        Parameters
        ----------
        mobject : Mobject
            Parent mobject
        e_prop_paths : list[ExtendedPropPath]
            A list of :type:`ExtendedPropPath`
        animatable : bool, optional
            If custom property can be animated, by default True
        """
        super().__init__(mobject)
        self.e_prop_paths = e_prop_paths
        self.is_animatable = animatable

    def set_mappings(
        self, mappings: list[DomainRangeMap]
    ) -> SimpleCustomMobjectProperty:
        """Sets mappings for this custom property.

        Parameters
        ----------
        mappings : list[DomainRangeMap]
            List of domain range mappings.
            Index must match with the corresponding :attr:`e_prop_paths`.
        """
        self._mappings = mappings
        return self

    def map(self, value: float, mapping: DomainRangeMap) -> float:
        return interp(value, *mapping)

    def set_value(self, value: any) -> list[PlannedKeyframe] | None:
        planned_keyframes = []

        for i, e_prop_path in enumerate(self.e_prop_paths):
            mapping = self._mappings[i] if i < len(self._mappings) else None
            if mapping:
                x = self.map(value, mapping)
            else:
                x = value

            obj = bpy.data.objects[self.mobject.prefix + "." + e_prop_path[0]]
            prop_path = e_prop_path[1:]
            data_path = prop_path_to_data_path(prop_path)

            if self._in_animate_mode:
                planned_keyframes.append(
                    {
                        "object": obj,
                        "type": "start",
                        "prop_path": prop_path,
                        "value": None,
                    }
                )
                planned_keyframes.append(
                    {
                        "object": obj,
                        "type": "end",
                        "prop_path": prop_path,
                        "value": x,
                    }
                )
                continue

            keyframe_insert(obj, data_path, self.mobject.stage.curr_time - 1)
            set_value_by_prop_path(obj, prop_path, x)
            keyframe_insert(obj, data_path, self.mobject.stage.curr_time)

        return planned_keyframes
