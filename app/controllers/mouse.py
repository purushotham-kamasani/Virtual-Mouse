"""Mouse controller interface + PyAutoGUI implementation.

Same pattern as the LLM client in the four backend repos: a tiny abstract
interface plus one concrete implementation. Tests use a recording stub.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class MouseController(ABC):
    """The set of operations the gesture engine can request."""

    @abstractmethod
    def move(self, x: int, y: int) -> None: ...

    @abstractmethod
    def click(self) -> None: ...

    @abstractmethod
    def right_click(self) -> None: ...

    @abstractmethod
    def scroll(self, amount: int) -> None: ...

    @abstractmethod
    def screen_size(self) -> tuple[int, int]: ...


class PyAutoGUIMouse(MouseController):
    """PyAutoGUI-backed implementation. Lazy-imports pyautogui."""

    def __init__(self) -> None:
        import pyautogui

        # PyAutoGUI's failsafe corner-abort feature has bitten too many demos.
        # We disable it explicitly so a wild cursor doesn't kill the session,
        # but keep it noted in the README.
        pyautogui.FAILSAFE = False
        self._pyautogui = pyautogui

    def move(self, x: int, y: int) -> None:
        self._pyautogui.moveTo(x, y, duration=0)

    def click(self) -> None:
        self._pyautogui.click()

    def right_click(self) -> None:
        self._pyautogui.rightClick()

    def scroll(self, amount: int) -> None:
        self._pyautogui.scroll(amount)

    def screen_size(self) -> tuple[int, int]:
        size = self._pyautogui.size()
        return int(size.width), int(size.height)


class RecordingMouse(MouseController):
    """Test double — records every call instead of moving the real cursor."""

    def __init__(self, *, screen_size: tuple[int, int] = (1920, 1080)) -> None:
        self.events: list[tuple[str, object]] = []
        self._screen_size = screen_size

    def move(self, x: int, y: int) -> None:
        self.events.append(("move", (x, y)))

    def click(self) -> None:
        self.events.append(("click", None))

    def right_click(self) -> None:
        self.events.append(("right_click", None))

    def scroll(self, amount: int) -> None:
        self.events.append(("scroll", amount))

    def screen_size(self) -> tuple[int, int]:
        return self._screen_size
