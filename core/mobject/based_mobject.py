from __future__ import annotations
import bpy

from mathutils import Vector

from . import Mobject
from .action import generate_actions
from ..stage import Stage
from ..animation import Animation


class BasedMobject(Mobject, Animation):
    """Mobject that is created from a reference
    collection"""

    base_coll: bpy.types.Collection
    """Base collection containing the mobject reference."""

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
        super().__init__(stage)
        # For some reason, when initializing, this attribute can
        # contain the previous value from the previous instance.
        # That's why we empty it here.
        self._planned_keyframes = []

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
