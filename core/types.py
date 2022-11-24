PropPath = list[str]
"""Path to a Blender object property.

Examples
--------
`["modifiers", "[Array]", "count"]`
`["location"]`
"""

ExtendedPropPath = list[str]
"""Similiar to :type:`PropPath`, but the first element contains
the unprefixed Blender object's name.
"""
