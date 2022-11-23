from abc import abstractmethod


class Animation:
    @abstractmethod
    def apply_animation(start_time: float, duration: float):
        """Sets animation keyframes in the timeline

        Parameters
        ----------
        start_time : float
            Start time
        duration : float
            Duration
        """
        pass
