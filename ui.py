from tkinter import *

from RunMode import RunMode
from UiState import UiState
from WorkerThread import WorkerThread


def start_clicked():
    global worker_thread, run_mode, rb_1, rb_2
    if worker_thread is None or worker_thread.ui_state == UiState.stopped:
        worker_thread = WorkerThread(run_mode)
        worker_thread.start()
        rb_1['state'] = DISABLED
        rb_2['state'] = DISABLED
    elif worker_thread.ui_state == UiState.paused:
        worker_thread.ui_state = UiState.running
        rb_1['state'] = DISABLED
        rb_2['state'] = DISABLED


def pause_clicked():
    global worker_thread
    if worker_thread is None:
        return
    if worker_thread.ui_state == UiState.running:
        worker_thread.ui_state = UiState.paused


def stop_clicked():
    global worker_thread, rb_1, rb_2
    if worker_thread is None:
        return
    worker_thread.ui_state = UiState.stopped
    rb_1['state'] = NORMAL
    rb_2['state'] = NORMAL


def selected():
    global run_mode
    if radio_selection.get() == 1:
        run_mode = RunMode.continuous
    elif radio_selection.get() == 2:
        run_mode = RunMode.followers


def on_closing():
    if worker_thread is not None:
        worker_thread.ui_state = UiState.stopped
    root.destroy()


worker_thread: WorkerThread = None
run_mode = RunMode.followers

root = Tk()
root.title('IG Awareness Helper')
root.resizable(False, False)
root.protocol("WM_DELETE_WINDOW", on_closing)
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
