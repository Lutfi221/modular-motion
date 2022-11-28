from __future__ import annotations
from abc import abstractmethod

import bpy

from ..utils import (
    interp,
    keyframe_insert,
    prop_path_to_data_path,
    set_value_by_prop_path,
)
from ..types import DomainRangeMap, ExtendedPropPath
from ..errors import CustomPropertyUnanimatable
from ..animation import PlannedKeyframe
from .mobject import Mobject


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
