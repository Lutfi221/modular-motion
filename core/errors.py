class UndefinedStageColl(Exception):
    def __init__(
        self,
        message=(
            "Stage collection is undefined.\n"
            "Define the `coll` attribute in the Stage subclass."
        ),
    ):
        super().__init__(message)


class CustomPropertyUnanimatable(Exception):
    def __init__(
        self,
        message=(
            "Custom mobject property is unanimatable because "
            "the `is_animatable` attribute is set to `False`.\n"
            "You might forgot to set the `is_animatable` attribute to `True`"
        ),
    ):
        super().__init__(message)
