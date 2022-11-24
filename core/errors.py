class UndefinedStageColl(Exception):
    def __init__(
        self,
        message=(
            "Stage collection is undefined.\n"
            "Define the `coll` attribute in the Stage subclass."
        ),
    ):
        super().__init__(message)
