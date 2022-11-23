from __future__ import annotations
import bpy

from mathutils import Vector

from .stage import Stage
from .animation import Animation


class Mobject:
    """Standard Mobject (Modular Motion Object)"""

    marks: dict[str, bpy.types.Object]
    """Dictionary of empties.
    Used for attaching other mobjects via :meth:`attach_to`."""

    actions: dict[str, Animation] = {}
    """List of playable actions for the Mobject.
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

        base_coll_objs = base_coll.all_objects

        # Create origin empty
        origin_empty = bpy.data.objects.new("BROO", None)
        origin_empty.empty_display_type = "ARROWS"
        origin_empty.scale = (0.1, 0.1, 0.1)
        origin_empty.location = base_coll_objs[0].location
        stage.coll.objects.link(origin_empty)

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

    def move_to(self, location: Vector) -> Mobject:
        self.set_prop_value("ORIGIN", "location", location)

    @property
    def animate(self) -> MobjectAnimationBuilder:
        return MobjectAnimationBuilder(self)

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


class MobjectAnimationBuilder(Mobject, Animation):
    mobject: Mobject

    def __init__(self, mobject: Mobject):
        self.mobject = mobject

    def __getattr__(self, name) -> any:
        if name == "set_prop_value":
            print("hahaha! overridden")
        attr = getattr(self.mobject, name)
        return attr
