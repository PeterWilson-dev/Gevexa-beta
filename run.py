#!/usr/bin/env python3
"""
Gevexa-beta CLI — A futuristic terminal AI assistant.
Requires: prompt_toolkit, rich, pyfiglet
Run: python ai_terminal.py
"""

import json
import os
import sys
import time
import threading
from pathlib import Path

import pyfiglet
from rich.console import Console
from rich.panel import Panel

from prompt_toolkit import Application
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.dimension import D
from prompt_toolkit.widgets import TextArea, Frame
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style as PTStyle
from prompt_toolkit.formatted_text import HTML


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
BRAIN_FILE = Path(__file__).parent / "brain.json"
APP_NAME   = "Gevexa-beta"
VERSION    = "v1.0.0"
AI_NAME    = "Gevexa-beta"

# Gevexa logo — raw block art, each line stored as plain string
GEVEXA_LOGO = [
    "  ░██████╗░███████╗██╗░░░██╗███████╗██╗░░██╗░█████╗░  ",
    "  ██╔════╝░██╔════╝██║░░░██║██╔════╝╚██╗██╔╝██╔══██╗  ",
    "  ██║░░██╗░█████╗░░╚██╗░██╔╝█████╗░░░╚███╔╝░███████║  ",
    "  ██║░░╚██╗██╔══╝░░░╚████╔╝░██╔══╝░░░██╔██╗░██╔══██║  ",
    "  ╚██████╔╝███████╗░░╚██╔╝░░███████╗██╔╝╚██╗██║░░██║  ",
    "  ░╚═════╝░╚══════╝░░░╚═╝░░░╚══════╝╚═╝░░╚═╝╚═╝░░╚═╝  ",
]


# ─────────────────────────────────────────────
# LOAD BRAIN
# ─────────────────────────────────────────────
def load_brain() -> dict:
    if BRAIN_FILE.exists():
        try:
            with open(BRAIN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

brain: dict = load_brain()


# ─────────────────────────────────────────────
# AI LOGIC
# ─────────────────────────────────────────────
def query_brain(user_input: str) -> str:
    normalized = user_input.strip().lower()
    if normalized in brain:
        return brain[normalized]
    for key, val in brain.items():
        if key in normalized or normalized in key:
            return val
    return "I don't understand. Try typing 'help' to see what I know."


# ─────────────────────────────────────────────
# CHAT STATE
# ─────────────────────────────────────────────
chat_history: list[tuple[str, str]] = []
is_thinking: bool = False
status_message: str = ""


# ─────────────────────────────────────────────
# HEADER BUILDER
# ─────────────────────────────────────────────
def build_header_text() -> str:
    lines = []

    # Gevexa logo in purple
    for row in GEVEXA_LOGO:
        escaped = row.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        lines.append(f"<ansimagenta>{escaped}</ansimagenta>")

    logo_block = "\n".join(lines)

    tagline = (
        f'<ansibrightblack>  {VERSION}  --  terminal AI  --  type </ansibrightblack>'
        f'<ansibrightmagenta>help</ansibrightmagenta>'
        f'<ansibrightblack> to get started</ansibrightblack>'
    )
    divider = f'<ansimagenta>  {"─" * 56}</ansimagenta>'

    return f"{logo_block}\n{divider}\n{tagline}\n"


# ─────────────────────────────────────────────
# CHAT DISPLAY BUILDER
# ─────────────────────────────────────────────
def build_chat_content() -> list:
    result = []

    if not chat_history and not is_thinking:
        result.append(("class:dim", "\n  Start a conversation -- type something below and press Enter\n"))
        return result

    result.append(("", "\n"))

    for role, msg in chat_history:
        if role == "you":
            result.append(("class:user-label", "  You             > "))
            result.append(("class:user-text", msg))
            result.append(("", "\n\n"))
        elif role == "ai":
            result.append(("class:ai-label", f"  {AI_NAME}  > "))
            lines = msg.split("\n")
            for i, line in enumerate(lines):
                result.append(("class:ai-text", line))
                if i < len(lines) - 1:
                    result.append(("", "\n"))
                    result.append(("class:ai-label", "                    "))
            result.append(("", "\n\n"))
        elif role == "system":
            result.append(("class:system-text", f"  [sys]  {msg}"))
            result.append(("", "\n\n"))

    if is_thinking:
        result.append(("class:thinking", f"  {AI_NAME}  > "))
        result.append(("class:thinking", f"  {status_message}"))
        result.append(("", "\n\n"))

    return result


def build_status_bar() -> list:
    return [
        ("class:statusbar", "  "),
        ("class:statusbar-key", "Enter"),
        ("class:statusbar", " send    "),
        ("class:statusbar-key", "/clear"),
        ("class:statusbar", " clear    "),
        ("class:statusbar-key", "exit"),
        ("class:statusbar", " quit    "),
        ("class:statusbar-key", "Ctrl+C"),
        ("class:statusbar", " force quit  "),
    ]


# ─────────────────────────────────────────────
# STYLES  (purple theme)
# ─────────────────────────────────────────────
PT_STYLE = PTStyle.from_dict({
    # Borders — purple
    "frame.border":          "#7c3aed",
    "frame.label":           "bold #a855f7",

    # Chat area
    "chat-area":             "bg:#08080f #d8d8e8",
    "user-label":            "bold #818cf8",      # indigo-ish
    "user-text":             "#a5b4fc",
    "ai-label":              "bold #c084fc",       # purple
    "ai-text":               "#e9d5ff",
    "thinking":              "italic #7c3aed",
    "system-text":           "dim #6b7280",
    "dim":                   "dim #4b4b6b",

    # Input
    "input-field":           "bg:#0c0c18 #d8d8e8",

    # Status bar
    "statusbar":             "bg:#0f0f1a #4b4b6b",
    "statusbar-key":         "bg:#0f0f1a bold #a855f7",

    # Scrollbar
    "scrollbar.background":  "bg:#1a1a2e",
    "scrollbar.button":      "bg:#7c3aed",
})


# ─────────────────────────────────────────────
# APP CLASS
# ─────────────────────────────────────────────
class GevexaCLI:
    def __init__(self):
        self.app: Application | None = None
        self.chat_window_control: FormattedTextControl | None = None
        self.input_area: TextArea | None = None
        self._typing_thread: threading.Thread | None = None

    # ── helpers ──────────────────────────────
    def _refresh(self):
        if self.app and self.app.is_running:
            try:
                self.app.invalidate()
            except Exception:
                pass

    def _scroll_to_bottom(self):
        if self.app and self.app.is_running:
            try:
                for win in self.app.layout.find_all_windows():
                    if win.content is self.chat_window_control:
                        win.vertical_scroll = 10000
                        break
            except Exception:
                pass

    def _add_message(self, role: str, text: str):
        chat_history.append((role, text))
        self._refresh()
        self._scroll_to_bottom()

    # ── typing animation ─────────────────────
    def _type_response(self, response: str):
        global is_thinking, status_message

        # thinking dots
        is_thinking = True
        for n in range(1, 4):
            status_message = "thinking" + "." * n
            self._refresh()
            time.sleep(0.25)

        # character-by-character
        typed = ""
        delay = max(0.010, min(0.030, 1.2 / max(len(response), 1)))

        for char in response:
            typed += char
            status_message = typed + "|"
            self._refresh()
            time.sleep(delay)

        # commit
        is_thinking = False
        status_message = ""
        self._add_message("ai", response)
        self._refresh()

        if self.app and self.app.is_running:
            try:
                self.app.layout.focus(self.input_area)
            except Exception:
                pass

    # ── input handler ────────────────────────
    def _handle_input(self, text: str):
        stripped = text.strip()
        if not stripped:
            return

        if stripped.lower() == "exit":
            if self.app:
                self.app.exit()
            return

        if stripped.lower() == "/clear":
            chat_history.clear()
            self._refresh()
            return

        self._add_message("you", stripped)

        if self._typing_thread and self._typing_thread.is_alive():
            return

        def respond():
            self._type_response(query_brain(stripped))

        self._typing_thread = threading.Thread(target=respond, daemon=True)
        self._typing_thread.start()

    # ── layout ──────────────────────────────
    def build_layout(self):
        # Header
        header_control = FormattedTextControl(
            lambda: HTML(build_header_text()),
            focusable=False,
        )
        header_window = Window(
            content=header_control,
            height=D.exact(10),
        )

        # Chat
        self.chat_window_control = FormattedTextControl(
            build_chat_content,
            focusable=False,
            show_cursor=False,
        )
        chat_window = Window(
            content=self.chat_window_control,
            wrap_lines=True,
            style="class:chat-area",
        )
        chat_frame = Frame(
            body=chat_window,
            title=f" Conversation ",
            style="class:frame.border",
        )

        # Input
        self.input_area = TextArea(
            height=3,
            prompt=HTML('<ansibrightmagenta>  You  > </ansibrightmagenta>'),
            style="class:input-field",
            multiline=False,
            wrap_lines=True,
            focus_on_click=True,
        )
        input_frame = Frame(
            body=self.input_area,
            title=f" Message ",
            style="class:frame.border",
        )

        # Status bar
        status_window = Window(
            content=FormattedTextControl(build_status_bar),
            height=1,
            style="class:statusbar",
        )

        root = HSplit([header_window, chat_frame, input_frame, status_window])
        return Layout(root, focused_element=self.input_area)

    # ── keybindings ──────────────────────────
    def build_keybindings(self):
        kb = KeyBindings()

        @kb.add("enter")
        def _(event):
            text = self.input_area.text
            self.input_area.text = ""
            self._handle_input(text)

        @kb.add("c-c")
        @kb.add("c-q")
        def _(event):
            event.app.exit()

        @kb.add("c-l")
        def _(event):
            chat_history.clear()
            self._refresh()

        return kb

    # ── run ──────────────────────────────────
    def run(self):
        os.system("cls" if os.name == "nt" else "clear")

        self.app = Application(
            layout=self.build_layout(),
            key_bindings=self.build_keybindings(),
            style=PT_STYLE,
            full_screen=True,
            mouse_support=True,
            refresh_interval=0.08,
        )

        chat_history.append((
            "system",
            f"{APP_NAME} {VERSION} initialized -- brain.json loaded ({len(brain)} entries)"
        ))

        try:
            self.app.run()
        except KeyboardInterrupt:
            pass

        os.system("cls" if os.name == "nt" else "clear")
        Console().print(
            Panel(
                f"[bold #a855f7]Session ended. Thanks for using {APP_NAME}.[/]",
                border_style="#7c3aed",
                padding=(1, 4),
            )
        )


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
def check_dependencies():
    missing = []
    for pkg in ["prompt_toolkit", "rich", "pyfiglet"]:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"Missing: {', '.join(missing)}")
        print(f"Install: pip install {' '.join(missing)}")
        sys.exit(1)


if __name__ == "__main__":
    check_dependencies()
    GevexaCLI().run()
