from abc import abstractmethod
import bpy
from mathutils import Vector

from .errors import UndefinedStageColl

from .animation import Animation, PlannedKeyframe

from .utils import (
    prop_path_to_data_path,
    release_prefix,
    reserve_original_prefix,
    set_value_by_prop_path,
)


class Stage:
    coll: bpy.types.Collection
    """Collection used for stage output
    """

    origin = Vector((0, 0, 0))
    """The stage origin (global)
    """

    prefix: str
    """Prefix to append to blender object names inside the stage collection.
    Used to prevent name collisions.
    """

    start_time = 0
    """Starting time"""

    curr_time = 0
    """Current time"""

    def __init__(self):
        if not hasattr(self, "coll"):
            raise UndefinedStageColl()

        # Remove every objects in the stage collection
        for obj in self.coll.all_objects:
            obj: bpy.types.Object
            bpy.data.objects.remove(obj)

        # Remove every subcollections in the stage collection.
        for child in self.coll.children_recursive:
            child: bpy.types.Collection
            if child.name.endswith(" [stage_prefix]"):
                # Get the previous stage's prefix
                prev_prefix = child.name[:-15]
                release_prefix(prev_prefix)

            bpy.data.collections.remove(child)

        self.prefix = reserve_original_prefix("_M.S")
        prefix_coll = bpy.data.collections.new(self.prefix + " [stage_prefix]")
        self.coll.children.link(prefix_coll)

    @abstractmethod
    def construct(self):
        """Construct and populate the stage."""
        pass

    def play(self, *args, duration=24):
        """Play animations

        Parameters
        ----------
        args
            Animations to be played
        duration : int, optional
            Duration, by default 1
        """
        for anim in args:
            anim: Animation
            planned_keyframes = anim.dump_planned_keyframes()

            # We need to insert the starting keyframes first,
            # and then the ending keyframes.
            # It is done in this order so the ending keyframe
            # don't affect the property value when we're inserting
            # the starting keyframe.
            for type in ["start", "end"]:
                for k in filter(lambda k: k["type"] == type, planned_keyframes):
                    k: PlannedKeyframe

                    if type == "start":
                        frame = self.curr_time
                    else:
                        frame = self.curr_time + duration

                    if k["value"] is not None:
                        set_value_by_prop_path(k["object"], k["prop_path"], k["value"])

                    k["object"].keyframe_insert(
                        prop_path_to_data_path(k["prop_path"]),
                        frame=frame,
                    )
        self.curr_time += duration

    def wait(self, duration=24):
        self.curr_time += duration
