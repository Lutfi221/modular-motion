import bpy
from mathutils import Vector

from .types import ExtendedPropPath, PropPath

PREFIX_LIST_TEXT_NAME = "_M.reserved_prefixes"


class Grid:
    """Access a point (Vector) in the grid via `grid[x][y][z]`"""

    def __init__(
        self, corner_a: Vector, corner_b: Vector, columns: int, rows: int, height: int
    ):
        pass

    def get_points(self) -> list[Vector]:
        pass


def reserve_original_prefix(base_prefix: str, post="") -> str:
    """Generate and reserve an original prefix from a base prefix.

    Parameters
    ----------
    base_prefix : str
        Base prefix without numbering.
    post : str
        String to append after the count number.

    Returns
    -------
    str
        Original numbered prefix
    """

    if PREFIX_LIST_TEXT_NAME in bpy.data.texts:
        prefix_text = bpy.data.texts[PREFIX_LIST_TEXT_NAME]
    else:
        prefix_text = bpy.data.texts.new(PREFIX_LIST_TEXT_NAME)
        prefix_text.from_string(
            (
                "# List of reserved prefixes in use by modular_motion.\n"
                "# Do not delete or change the contents of this text.\n\n"
            )
        )

    # Move cursor to the last line
    prefix_text.cursor_set(999999)

    def is_prefix_reserved(prefix: str) -> bool:
        return any([line.body.startswith(prefix) for line in prefix_text.lines])

    counter = 0
    prefix = base_prefix + str(counter).zfill(2)

    while is_prefix_reserved(prefix):
        counter += 1
        prefix = base_prefix + str(counter).zfill(2)

    prefix_text.write(prefix + "\n")
    prefix_text.cursor_set(999999)

    return prefix


def release_prefix(prefix: str):
    """Remove prefix from the reserved prefix list.

    Parameters
    ----------
    prefix : str
        Prefix to remove
    """
    if PREFIX_LIST_TEXT_NAME not in bpy.data.texts:
        return

    prefix_text = bpy.data.texts[PREFIX_LIST_TEXT_NAME]
    body: str = prefix_text.as_string()
    new_body = ""

    for line in body.split("\n"):
        if line == "":
            continue
        if not line.startswith(prefix):
            new_body += line + "\n"

    prefix_text.from_string(new_body)
    prefix_text.cursor_set(999999)


def prop_path_to_data_path(prop_path: PropPath) -> str:
    """Converts prop_path to data_path that can be used
    in Blender's `keyframe_insert`.

    Parameters
    ----------
    prop_path : list[str]
        List of attributes and keys

    Returns
    -------
    str
        Data path
    """
    out = ""
    prev = False
    for elem in prop_path:
        if elem.startswith("["):
            out += '["' + elem[1:-1] + '"]'
        else:
            if prev:
                out += "."
            out += elem
            prev = True
    return out


def set_value_by_prop_path(obj: bpy.types.Object, prop_path: PropPath, value: any):
    """Sets the value pointed by the prop_path

    Parameters
    ----------
    obj : bpy.types.Object
        Blender object
    prop_path : list[str]
        List of attributes and keys
    value : any
        Value to change to
    """
    head = obj
    for i, elem in enumerate(prop_path):
        if elem.startswith("["):
            if i == len(prop_path) - 1:
                head[elem[1:-1]] = value
                return
            head = head[elem[1:-1]]
        else:
            if i == len(prop_path) - 1:
                setattr(head, elem, value)
                return
            head = getattr(head, elem)


def color_hex_to_vector(hex_str: str) -> tuple[float, float, float]:
    """Convert hex color code to normalized RGB vector.

    Parameters
    ----------
    hex_str : str
        Hex code

    Returns
    -------
    tuple[float, float, float]
        Normalized RGB vector.

    Examples
    --------
    >>> color_hex_to_vector("#ff0")
    (1.0, 1.0, 0.0)
    >>> color_hex_to_vector("E87D0D")
    (0.909, 0.490, 0.050)
    """
    hex_str = hex_str.lstrip("#")
    l = len(hex_str)
    if l == 6:
        return tuple(int(hex_str[i : i + 2], 16) / 255 for i in range(0, 6, 2))
    return tuple(int(2 * hex_str[i : i + 1], 16) / 255 for i in range(0, 3, 1))


# def color_hex_to_vector(hex_str: str) -> tuple[float, float, float]:
#     hex_str = hex_str.lstrip("#")
#     print(hex_str)
#     if len(hex_str) <= 4:
#         return tuple(int(hex_str[i] * 2, 16) / 255 for i in (1, 2, 3))
#     return tuple(int(hex_str[i : i + 2], 16) / 255 for i in (1, 3, 5))
