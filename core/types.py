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

DomainRangeMap = tuple[float, float, float, float]
"""Domain to range map.
In the form of [domain_min, domain_max, range_min, range_max]
"""
