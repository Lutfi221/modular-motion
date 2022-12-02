from __future__ import annotations
from math import floor
from typing import TypedDict
import bpy

from . import Mobject

from ..utils import (
    data_path_to_prop_path,
    interp,
    keyframe_insert,
    set_value_by_prop_path,
)
from ..animation import Animation


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
            Parent mobject.
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
        scale = (end - start) / (self.base_end_time - self.base_start_time)
        for actor in self.actors:
            base_name = actor["root"]["name"]
            base_fcurve = actor["base_fcurve"]
            data_path = actor["data_path"]
            prop_path = data_path_to_prop_path(data_path)
            target: bpy.types.ID = getattr(bpy.data, actor["root"]["scope"])[
                self.mobject.prefix + "." + base_name
            ]

            kps = base_fcurve.keyframe_points
            i = 0

            # Increment `i` until keyframe `kp[i]` is inside the action window
            # (between `self.base_start_time` and `self.base_end_time`).
            while i < len(kps):
                base_frame = kps[i].co[0]
                if base_frame >= self.base_start_time:
                    break
                i += 1

            target_fcurve = self._get_fcurve(
                target, base_fcurve.data_path, base_fcurve.array_index
            )

            while i < len(kps) and kps[i].co[0] <= self.base_end_time:
                base_kp = kps[i]
                set_value_by_prop_path(target, prop_path, base_kp.co[1])
                time = round(
                    interp(
                        base_kp.co[0],
                        self.base_start_time,
                        self.base_end_time,
                        start,
                        end,
                    )
                )
                keyframe_insert(target, data_path, time)

                new_kp = next(
                    k for k in target_fcurve.keyframe_points if k.co[0] == time
                )
                self._conform_keyframe(base_kp, new_kp, scale)
                i += 1

    def _get_fcurve(
        self, target: bpy.types.ID, data_path: str, array_index: int
    ) -> bpy.types.FCurve:
        """Get fcurve. If not exists, create it.

        Parameters
        ----------
        target : bpy.types.ID
            Blender ID
        data_path : str
            Fcurve data path
        array_index : int
            Fcurve array index

        Returns
        -------
        bpy.types.FCurve
            Fcurve
        """
        if target.animation_data and target.animation_data.action:
            for fcurve in target.animation_data.action.fcurves:
                if data_path == fcurve.data_path and array_index == fcurve.array_index:
                    return fcurve

        if not target.animation_data or not target.animation_data.action:
            target.animation_data_create()
            target.animation_data.action = bpy.data.actions.new(
                self.mobject.prefix + "." + target.name
            )
        target.animation_data.action.fcurves.new(data_path, index=array_index)
        return target.animation_data.action.fcurves[-1]

    def _conform_keyframe(
        self, base: bpy.types.Keyframe, target: bpy.types.Keyframe, scale=1
    ):
        """Copy keyframe attributes from `base` to `target`.

        Parameters
        ----------
        base : bpy.types.Keyframe
            Base keyframe as reference
        target : bpy.types.Keyframe
            Target keyframe that will be changed
        scale : int, optional
            multiplier for the handle distance, by default 1
        """
        for attr in [
            "easing",
            "handle_left_type",
            "handle_right_type",
            "interpolation",
            "type",
        ]:
            setattr(target, attr, getattr(base, attr))
        for handle in ["handle_left", "handle_right"]:
            getattr(target, handle)[0] = (
                getattr(base, handle)[0] - base.co[0]
            ) * scale + target.co[0]


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
