from __future__ import annotations
from abc import abstractmethod
from math import floor
from typing import TypedDict
import bpy

from mathutils import Vector

from .errors import CustomPropertyUnanimatable

from .types import DomainRangeMap, ExtendedPropPath, PropPath

from .utils import (
    data_path_to_prop_path,
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

    actions: list[ActionAnimation]
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

    base_coll: bpy.types.Collection
    """Base collection containing the mobject reference."""

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
        self.base_coll = base_coll

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

        clones: list[bpy.types.Object] = origin_empty.children_recursive

        clones_with_shape_keys = [
            obj for obj in clones if obj.data and obj.data.shape_keys
        ]

        # Unlink objects with shape keys, so when we animate the shape keys,
        # it wouldn't affect the base object.
        with bpy.context.temp_override(selected_objects=clones_with_shape_keys):
            bpy.ops.object.make_single_user(
                animation=True, object=True, obdata=True, obdata_animation=True
            )

        # Make animation and object data animation single-user.
        # And clear the keyframes.
        with bpy.context.temp_override(selected_objects=clones):
            bpy.ops.object.make_single_user(animation=True, obdata_animation=True)
            bpy.ops.anim.keyframe_clear_v3d()

        for obj in clones_with_shape_keys:
            obj.data.shape_keys.animation_data_clear()

        originals = base_coll.objects

        # Add prefix and rename objects to their original names.
        # This will remove the blender-generated suffixes after
        # duplication such as `.001`, `.002`, etc.
        for i, clone in enumerate(clones):
            clone: bpy.types.Object
            clone.name = self.prefix + "." + originals[i].name

            # Renames shape keys
            if hasattr(clone.data, "shape_keys") and clone.data.shape_keys:
                clone.data.shape_keys.name = (
                    self.prefix + "." + originals[i].data.shape_keys.name
                )

        self.actions = generate_actions(self)

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


class _ID(TypedDict):
    """Data-block identifier.
    Helper type for :func:`generate_actions`"""

    scope: str
    """Data-block type in plural form.

    Examples
    --------
    `'objects'`, `'shape_keys'`
    """
    name: str
    """Data-block name"""


class _AnimData(TypedDict):
    """Wrapper for `fcurve` to add data-block owner information.
    Helper type for :func:`generate_actions`"""

    root: _ID
    """Owner of the fcurve"""
    fcurve: bpy.types.FCurve


class Actor(TypedDict):
    """An actor is an fcurve that is involved in an action.
    An fcurve is involved in the action if it contains atleast
    two keyframes in the action window (the action's start and end time).
    An actor can be in multiple actions."""

    root: _ID
    """Owner of `base_fcurve`"""
    base_fcurve: bpy.types.FCurve
    data_path: str
    """Data path that is being animated.
    Might includes an unneccessary index at the end."""


def generate_actions(mobject: Mobject, width=30) -> list[ActionAnimation]:
    first_keyframe_time = 9999999
    last_keyframe_time = -9999999
    actions: list[ActionAnimation] = []

    # Will contain all animation data
    # from the objects in `mobject.base_coll`
    anims_data: list[_AnimData] = []

    for obj in mobject.base_coll.all_objects:
        obj: bpy.types.Object

        if obj.animation_data:
            for fcurve in obj.animation_data.action.fcurves:
                anims_data.append(
                    {"root": {"scope": "objects", "name": obj.name}, "fcurve": fcurve}
                )

        try:
            shape_key_anim_data = obj.data.shape_keys.animation_data
        except AttributeError:
            shape_key_anim_data = None

        if shape_key_anim_data:
            for fcurve in shape_key_anim_data.action.fcurves:
                anims_data.append(
                    {
                        "root": {
                            "scope": "shape_keys",
                            "name": obj.data.shape_keys.name,
                        },
                        "type": "shape_key",
                        "fcurve": fcurve,
                    }
                )

    # Find the first and last keyframe time
    for anim_data in anims_data:
        first_fcurve_keyframe = anim_data["fcurve"].keyframe_points[0]
        if first_fcurve_keyframe.co[0] < first_keyframe_time:
            first_keyframe_time = first_fcurve_keyframe.co[0]

        last_fcurve_keyframe = anim_data["fcurve"].keyframe_points[-1]
        if last_fcurve_keyframe.co[0] > last_keyframe_time:
            last_keyframe_time = last_fcurve_keyframe.co[0]

    # Number of actions we can generate
    actions_amount = floor((last_keyframe_time - first_keyframe_time) / width)

    # This is a 2D array, where the first index is the action index.
    actors_by_index: list[list[Actor]] = [None] * actions_amount

    for i in range(actions_amount):
        actors_by_index[i] = []
        start = first_keyframe_time + width * i
        end = start + width

        for anim_data in anims_data:
            is_an_actor = False
            # Number of keyframes between the action's
            # start and end time.
            k_amount_in_window = 0

            # To know if `anim_data` is an actor for action[i],
            # we need to check if it has atleast two keyframes
            # between the action's start and end time.

            for k_point in anim_data["fcurve"].keyframe_points:
                if k_point.co[0] < start:
                    continue
                if k_point.co[0] > end:
                    break

                k_amount_in_window += 1
                if k_amount_in_window >= 2:
                    is_an_actor = True
                    break

            if is_an_actor:
                fcurve = anim_data["fcurve"]
                actors_by_index[i].append(
                    {
                        "root": anim_data["root"],
                        "base_fcurve": fcurve,
                        "data_path": fcurve.data_path
                        + "["
                        + str(fcurve.array_index)
                        + "]",
                    }
                )
        actions.append(ActionAnimation(mobject, actors_by_index[i], start, end))
    return actions


class ActionAnimation(Animation):
    mobject: Mobject
    base_start_time: float
    """Start time of the action in the base object fcurve."""
    base_end_time: float
    """End time of the action in the base object fcurve."""
    actors: list[Actor]
    """List of fcurves that is involved in this action."""

    def __init__(
        self,
        mobject: Mobject,
        actors: list[Actor],
        base_start_time: float,
        base_end_time: float,
    ):
        """Create a mobject action

        Parameters
        ----------
        mobject : Mobject
            Mobject
        actors : list[Actor]
            List of actors that is involved in the action
        base_start_time : float
            Start time of the action in the base object fcurve.
        base_end_time : float
            End time of the action in the base object fcurve.
        """
        self.mobject = mobject
        self.base_start_time = base_start_time
        self.base_end_time = base_end_time
        self.actors = actors

    def apply_animation(self, start: float, end: float):
        for actor in self.actors:
            base_name = actor["root"]["name"]
            base_fcurve = actor["base_fcurve"]
            data_path = actor["data_path"]
            prop_path = data_path_to_prop_path(data_path)
            target: bpy.types.ID = getattr(bpy.data, actor["root"]["scope"])[
                self.mobject.prefix + "." + base_name
            ]

            kp = base_fcurve.keyframe_points
            i = 0

            # Increment `i` until keyframe `kp[i]` is inside the action window
            # (between `self.base_start_time` and `self.base_end_time`).
            while i < len(kp):
                base_frame = kp[i].co[0]
                if base_frame >= self.base_start_time:
                    break
                i += 1

            while i < len(kp):
                set_value_by_prop_path(target, prop_path, kp[i].co[1])
                keyframe_insert(
                    target,
                    data_path,
                    interp(
                        kp[i].co[0],
                        self.base_start_time,
                        self.base_end_time,
                        start,
                        end,
                    ),
                )
                i += 1
