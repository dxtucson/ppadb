from tkinter import *
from RunMode import RunMode
from ScreenshotThread import ScreenshotThread
from UiState import UiState
from WorkerThread import WorkerThread


def start_clicked():
    global worker_thread, run_mode, rb_1, rb_2, rb_3, counter_var
    ignore_button = True
    if worker_thread is None or worker_thread.ui_state == UiState.stopped:
        ignore_button = False
        worker_thread = WorkerThread(run_mode, counter_var, show_exceeded)
        worker_thread.start()
    elif worker_thread.ui_state == UiState.paused:
        ignore_button = False
        worker_thread.ui_state = UiState.running
    if not ignore_button:
        rb_1['state'] = DISABLED
        rb_2['state'] = DISABLED
        rb_3['state'] = DISABLED
        root.after(5000, update_ui)


def pause_clicked():
    global worker_thread
    if worker_thread is None:
        return
    if worker_thread.ui_state == UiState.running:
        worker_thread.ui_state = UiState.paused


def stop_clicked():
    global worker_thread, rb_1, rb_2, rb_3
    if worker_thread is None:
        return
    worker_thread.ui_state = UiState.stopped
    rb_1['state'] = NORMAL
    rb_2['state'] = NORMAL
    rb_3['state'] = NORMAL


def screenshot_clicked():
    t = ScreenshotThread()
    t.start()


def selected():
    global run_mode
    if radio_selection.get() == 1:
        run_mode = RunMode.continuous
    elif radio_selection.get() == 2:
        run_mode = RunMode.followers
    elif radio_selection.get() == 3:
        run_mode = RunMode.posts


def on_closing():
    if worker_thread is not None:
        worker_thread.ui_state = UiState.stopped
    root.destroy()


def update_ui():
    if worker_thread is None:
        rb_1['state'] = NORMAL
        rb_2['state'] = NORMAL
        rb_3['state'] = NORMAL
    elif worker_thread is not None:
        if worker_thread.ui_state == UiState.stopped:
            rb_1['state'] = NORMAL
            rb_2['state'] = NORMAL
            rb_3['state'] = NORMAL
        else:
            root.after(5000, update_ui)


def show_exceeded(detail):
    exceeded_label.place(x=180, y=320, anchor='center')
    exceeded_var.set(detail)
    rb_1['state'] = DISABLED
    rb_2['state'] = DISABLED
    rb_3['state'] = DISABLED
    start_button['state'] = DISABLED
    pause_button['state'] = DISABLED
    stop_button['state'] = DISABLED


worker_thread: WorkerThread = None
run_mode = RunMode.followers

root = Tk()
root.title('IG Awareness Helper')
root.resizable(False, False)
root.protocol("WM_DELETE_WINDOW", on_closing)
c = Canvas(root, width=360, height=340, bg='#f2f2f2')
c.pack()

radio_selection = IntVar()
radio_selection.set(2)

counter_var = IntVar()
counter_var.set(0)
exceeded_var = StringVar()
exceeded_var.set('Limit exceeded.')

rb_1 = Radiobutton(root, font='Arial 11', width='12', text="Continuous", padx=20, value=1, variable=radio_selection,
                   command=selected)
rb_1.place(x=132, y=20, width=100, height=30)

rb_2 = Radiobutton(root, font='Arial 11', width='12', text="Followers ", padx=20, value=2, variable=radio_selection,
                   command=selected)
rb_2.place(x=129, y=50, width=100, height=30)

rb_3 = Radiobutton(root, font='Arial 11', width='12', text="Likes on post", padx=20, value=3, variable=radio_selection,
                   command=selected)
rb_3.place(x=128, y=80, width=120, height=30)

c.create_text(180, 130, font='Arial 13', text='Total likes in 24 hrs:')
counter_label = Label(root, font='Arial 20', textvariable=counter_var)
counter_label.place(x=180, y=170, anchor='center')

start_button = Button(root, font='Arial 11', text='Start', bd='2', command=start_clicked)
start_button.place(x=80, y=200, width=50, height=40)

pause_button = Button(root, font='Arial 11', text='Pause', bd='2', command=pause_clicked)
pause_button.place(x=155, y=200, width=50, height=40)

stop_button = Button(root, font='Arial 11', text='Stop', bd='2', command=stop_clicked)
stop_button.place(x=230, y=200, width=50, height=40)

screenshot_button = Button(root, font='Arial 11', text='Screenshot', bd='2', command=screenshot_clicked)
screenshot_button.place(x=130, y=260, width=100, height=40)

exceeded_label = Label(root, font='Arial 10', textvariable=exceeded_var)
exceeded_label.configure(foreground="red")

check_thread = WorkerThread(run_mode, counter_var, show_exceeded)
check_thread.check_limit_exceeded()

root.mainloop()

# to build: pyinstaller -w -F -i "heart.ico" IGLikeHelper.py
