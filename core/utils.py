import bpy
from mathutils import Vector

from .types import PropPath

PREFIX_LIST_TEXT_NAME = "_M.reserved_prefixes"


def generate_grid_points(
    a: Vector, b: Vector, columns: int, rows: int, height: int
) -> list[Vector]:
    """Generate a grid of points.

    Parameters
    ----------
    a : Vector
        Bottom left corner of the grid
    b : Vector
        Top right corner of the grid
    columns : int
        Amount of columns
    rows : int
        Amount of rows
    height : int
        Amount of layers

    Returns
    -------
    list[Vector]
        List of points
    """
    points: list[Vector] = []
    delta_x = (b[0] - a[0]) / (columns - 1) if columns != 1 else 0
    delta_y = (b[1] - a[1]) / (rows - 1) if rows != 1 else 0
    delta_z = (b[2] - a[2]) / (height - 1) if height != 1 else 0
    for x in range(columns):
        for y in range(rows):
            for z in range(height):
                points.append(
                    Vector(
                        (
                            a[0] + delta_x * x,
                            a[1] + delta_y * y,
                            a[2] + delta_z * z,
                        )
                    )
                )
    return points


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
            if elem[1:-1].isdigit():
                out += "[" + elem[1:-1] + "]"
                continue
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
                if elem[1:-1].isdigit():
                    head[int(elem[1:-1])] = value
                    continue
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


def interp(x: float, min: float, max: float, new_min: float, new_max: float):
    return ((x - min) / (max - min)) * (new_max - new_min) + new_min


def keyframe_insert(obj: bpy.types.Object, path: str | PropPath, frame: float):
    """Insert keyframe to the object's property.

    If you were to input a path with a last index, such as
    `path='location[1]'`, this function assumes
    that last index is only a single digit. So a path like
    `path='property[12]'` will break the function.

    Parameters
    ----------
    obj : bpy.types.Object
        Blender object
    path : str | PropPath
        Data path or :type:`PropPath`
    """
    index = -1
    data_path: str

    if type(path) == str:
        if path[-2].isdigit():
            index = int(path[-2])
            data_path = path[:-3]
        else:
            data_path = path
    else:
        try:
            has_last_index = path[-1][-2].isdigit()
        except IndexError:
            pass

        if has_last_index:
            index = int(path[-1][-2])
            data_path = prop_path_to_data_path(path)[:-3]
        else:
            data_path = prop_path_to_data_path(path)

    obj.keyframe_insert(data_path, index=index, frame=frame)
