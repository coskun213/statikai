"""Colours and ttk styles shared by the desktop panels."""
from tkinter import ttk

BACKGROUND='#f3f6fa'
HEADING='#12304b'
TEXT='#40566c'
MUTED='#53697c'
ACCENT='#176d9c'
COLUMN='#c43b42'
BEAM='#1d6b9a'
DEFORMED='#e59b27'
WARNING_BG='#fff3d5'
WARNING_FG='#944c00'
STATUS_BG='#e3edf6'
OVER_LIMIT_BG='#fbe0e0'


def apply_styles(root):
    style=ttk.Style(root);style.theme_use('clam')
    style.configure('.',font=('Segoe UI',10),background=BACKGROUND)
    style.configure('TFrame',background=BACKGROUND)
    style.configure('Title.TLabel',font=('Segoe UI',22,'bold'),foreground=HEADING)
    style.configure('Group.TLabel',font=('Segoe UI',11,'bold'),foreground=HEADING)
    style.configure('Action.TButton',font=('Segoe UI',12,'bold'),padding=9,background=ACCENT,foreground='white')
    style.configure('Treeview',rowheight=25,fieldbackground='white',background='white')
    style.configure('Treeview.Heading',font=('Segoe UI',10,'bold'))
    return style
