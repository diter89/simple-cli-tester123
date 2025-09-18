import datetime
from rich import box 
from rich.panel import Panel
from rich.table import Table
from rich.align import Align
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.styles import Style
import time 
from pygments.lexers.html import HtmlLexer
from prompt_toolkit.lexers import PygmentsLexer

def custom_colorsUX():
    return {
            "panel_app": "#888888 bold",
            "table_box": box.ROUNDED,
            }


# iquirerStyle
def inquirerstyle():
    return {
    "questionmark": "#e5c07b",
    "answermark": "#e5c07b",
    "answer": "#61afef",
    "input": "#98c379",
    "question": "",
    "answered_question": "",
    "instruction": "#abb2bf",
    "long_instruction": "#abb2bf",
    "pointer": "#61afef bold",
    "checkbox": "#98c379",
    "separator": "",
    "skipped": "#5c6370",
    "validator": "",
    "marker": "#e5c07b",
    "fuzzy_prompt": "#c678dd",
    "fuzzy_info": "#abb2bf",
    "fuzzy_border": "#4b5263",
    "fuzzy_match": "#c678dd",
    "spinner_pattern": "#e5c07b",
    "spinner_text": "",
    }

#------ themes syntax --------------
def syntax_for_personagenerator():
    """ 
abap, algol_nu, algol, arduino, autumn, borland, bw, colorful, default,
emacs, friendly_grayscale, friendly, fruity, github-dark, gruvbox-dark,
gruvbox-light, igor, inkpot, lightbulb, lilypond, lovelace, manni,
material, monokai (default), murphy, native, nord-darker, nord, one-dark,
paraiso-dark, paraiso-light, pastie, perldoc, rainbow_dash, rrt, sas,
solarized-dark, solarized-light, staroffice, stata-dark, stata-light,
stata, tango, trac, vim, vs, xcode, zenburn
    """
    return {"style": "vim"}

#----- grammar ---------
def pygment():
    return PygmentsLexer(HtmlLexer)


#----- get_prompt -----------
def get_prompt():
    now = datetime.datetime.now()
    return [
            ("fg:#FFFFFF","["),
            ("fg:#008800", f"{now.strftime('%H:%M:%S')}"),
            ("fg:#FFFFFF","]~> ")
    ]

#----- styles ---------------
def stylecompleter():
    return Style.from_dict(
            {
                "completion.menu": "#0a0a0a",
                "scrollbar.background": "bg:#0a7e98 bold",
                "completion-menu.completion": "bg:#0a0a0a fg:#aaaaaa bold",
                "completion-menu.completion fuzzymatch.outside": "#aaaaaa underline",
                "completion-menu.completion fuzzymatch.inside": "fg:#9ece6a bold",
                "completion-menu.completion fuzzymatch.inside.character": "underline bold",
                "completion-menu.completion.current fuzzymatch.outside": "fg:#9ece6a underline",
                "completion-menu.completion.current fuzzymatch.inside": "fg:#f7768e bold",
                "completion-menu.meta.completion": "bg:#0a0a0a fg:#aaaaaa bold",
                "completion-menu.meta.completion.current": "bg:#888888",
            },
        )

#---- banner ------------
def Banners(mode: str):
    banner = Panel(Align.center(f"""
█▀ █ █▀▄▀█ █▀█ █░░ ▄▄ █▀▀ █░░ █ 
▄█ █ █░▀░█ █▀▀ █▄▄ ░░ █▄▄ █▄▄ █ 
    """),border_style="#888888 bold",style="green bold")

    description = f"""
📦 Mode: [green bold]{mode}[/green bold]
📦 Features: Smart Router, Modular Persona, Cross-Session Memory
📦 [dim]Type 'keluar', 'exit', or Ctrl-C to quit[/dim]
"""

    table = Table.grid(expand=True)

    table.add_row(banner)
    table.add_row(description)
    
    panel = Panel(
        table, 
        border_style=custom_colorsUX()["panel_app"], 
        title="[bold #FFFFFF]Simpl-CLI[/bold #FFFFFF]",
    )
    return panel

