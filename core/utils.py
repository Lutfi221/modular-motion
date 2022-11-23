import bpy
from mathutils import Vector


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
    prefix_list_text_name = "_M.reserved_prefixes"

    if prefix_list_text_name in bpy.data.texts:
        prefix_text = bpy.data.texts[prefix_list_text_name]
    else:
        prefix_text = bpy.data.texts.new(prefix_list_text_name)
        prefix_text.from_string(
            (
                "# List of reserved prefixes in use by modular_motion.\n"
                "# Do not delete or change the contents of this text.\n"
            )
        )

    # Move cursor to the last line
    prefix_text.cursor_set(len(prefix_text.lines))

    def is_prefix_reserved(prefix: str) -> bool:
        return any([line.body.startswith(prefix) for line in prefix_text.lines])

    counter = 0
    prefix = base_prefix + str(counter).zfill(2)

    while is_prefix_reserved(prefix):
        counter += 1
        prefix = base_prefix + str(counter).zfill(2)

    prefix_text.write(prefix + "\n")

    return prefix
