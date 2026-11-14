"""Launcher for the StatikAI 3D frame desktop app (code lives in statikai/gui)."""
import argparse
import os
from pathlib import Path
import sys
import traceback

ROOT=Path(__file__).resolve().parent
WORK=ROOT/'work'/'desktop'
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'work'/'matplotlib'))
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser(description='StatikAI 3B çerçeve masaüstü uygulaması')
    parser.add_argument('--smoke-test',action='store_true',help='otomatik GUI kontrolü çalıştırıp kapan')
    args=parser.parse_args()
    import tkinter as tk
    from statikai.gui.app import StatikApp
    root=tk.Tk();app=StatikApp(root,args.smoke_test)
    root.mainloop()
    if app.smoke_error:
        raise RuntimeError(app.smoke_error)


if __name__=='__main__':
    try:
        main()
    except Exception:
        WORK.mkdir(parents=True,exist_ok=True)
        log=WORK/'baslatma_hatasi.log'
        log.write_text(traceback.format_exc(),encoding='utf8')
        try:
            from tkinter import messagebox
            messagebox.showerror('StatikAI başlatılamadı','Hata kaydı: '+str(log))
        except Exception:
            pass
        raise
