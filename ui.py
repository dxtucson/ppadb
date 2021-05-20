import time
import tkinter

from tkinter import *
from datetime import date, datetime


def start_clicked():
    print('start clicked')


def pause_clicked():
    print('pause clicked')


def stop_clicked():
    print('stop clicked')


def selected():
    print(f'radio selected: {radio_selection.get()}')


root = Tk()
root.title('IG Awareness Helper')
root.resizable(False, False)
c = Canvas(root, width=360, height=280, bg='#f2f2f2')
c.pack()

radio_selection = IntVar()
radio_selection.set(2)

rb_1 = Radiobutton(root, font='Arial 11', width='12', text="Continuous", padx=20, value=1, variable=radio_selection,
                   command=selected)
rb_1.place(x=132, y=30, width=100, height=30)

rb_2 = Radiobutton(root, font='Arial 11', width='12', text="Followers ", padx=20, value=2, variable=radio_selection,
                   command=selected)
rb_2.place(x=129, y=60, width=100, height=30)

c.create_text(180, 120, font='Arial 13', text='Posts you\'ve liked today:')
c.create_text(180, 160, font='Arial 18', text='888')

start_button = Button(root, font='Arial 11', text='Start', bd='2', command=start_clicked)
start_button.place(x=80, y=200, width=50, height=40)

pause_button = Button(root, font='Arial 11', text='Pause', bd='2', command=pause_clicked)
pause_button.place(x=155, y=200, width=50, height=40)

stop_button = Button(root, font='Arial 11', text='Stop', bd='2', command=stop_clicked)
stop_button.place(x=230, y=200, width=50, height=40)

root.mainloop()
