class Stage:
    def __init__(self):
        pass

    def construct(self):
        """To be implemented in the subclass."""
        pass

    def play(self, *args, duration=1):
        """Play animations

        Parameters
        ----------
        args
            Animations to be played
        """
        pass
