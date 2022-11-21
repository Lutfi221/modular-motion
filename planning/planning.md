# To Learn From

1.  [Easy Bpy](https://github.com/curtisjamesholt/EasyBPY/blob/master/easybpy.py)
2.  [MANIM Syntax](https://docs.manim.community/en/stable/tutorials/quickstart.html)

# Specifications

## Scenarios

### Dancing Grid of Houses

```python
import mm

class DancingHouses(Stage):
    def construct(self):
        corner_a = self.get_mark('gridCornerA').location
        corner_b = self.get_mark('gridCornerB').location

        # grid[x][y][z] = Vector(x, y, z)
        grid = mm.Grid(corner_a, corner_b, 4, 3, 0)

        houses: list[House] = []

        for point in grid.get_points():
            house = House(point)
            house.customize('roof_color', '#E72B2B')
            houses.append(house)
            self.play(house.actions['create'], duration=0.3)

        for house in houses:
            self.play(house.animate.shift(1 * FORWARD, 1 * UP))
            self.play(house.animate.shift( -1 * UP))

        for house in houses:
            self.play(house.actions['destroy'], duration=0.3)
```

### Seesaw

```python
import mm
from mathutils import Vector, PI

class HouseSeesaw(Stage):
    def construct(self):
        seesaw = Seesaw()
        self.play(seesaw.actions['create'])
        self.play(seesaw.animate.rotate(Vector(0, 0, 2 * PI)))
        self.play(seesaw.animate.customize('slope', - PI / 4))
        self.play(seesaw.animate.customize('slope', PI / 4))

        self.play(seesaw.animate.customize('slope', 0))

        house_a = House(5 * UP)
        self.play(house_a.animate.attach_to(seesaw, 'left'))

        house_b = House(5 * UP)
        self.play(house_b.animate.attach_to(seesaw, 'right'))

        self.play(seesaw.animate.customize('slope', PI / 4))
```
