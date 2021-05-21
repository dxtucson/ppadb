import threading
from tkinter import IntVar
from ppadb.client import Client
from PIL import Image
import numpy
from numpy import load
import time
import os

from RunMode import RunMode
from UiState import UiState


class WorkerThread(threading.Thread):

    def __init__(self, mode: RunMode, count: IntVar):
        threading.Thread.__init__(self)
        self.run_mode = mode
        self.likes = count

    ui_state = UiState.running
    run_mode = RunMode.followers
    likes: IntVar
    # these numbers are for Pixel 2 XL
    feed_top = 97  # top bar bottom pixel
    follow_top = 466  # top bar of follower page is taller
    feed_bottom = 2536  # bottom bar top pixel
    half_width = 720  # half of the screen width
    follow_button_x = 1050  # this point should have blue(0, 149, 246, 255) if it is follow button
    left_thin_margin = 5  # help to decide whether there is a tab indicator (thin black horizontal line)

    os.system('cmd /c "C:\\Users\\David\\AppData\\Local\\Android\\Sdk\\platform-tools\\adb devices"')
    adb = Client(host='127.0.0.1', port=5037)
    devices = adb.devices()

    if len(devices) == 0:
        print('no device attached')
        quit()

    device = devices[0]

    black_heart_saved = load('black_heart_saved.npy')

    # find start Y of black heart. Return -1 if not found
    def find_black_heart(self) -> int:
        image = self.screenshot()
        vertical_slice = image[:, 90:92]
        y_start = -1
        equal_count = 0

        for ay in range(numpy.shape(vertical_slice)[0]):
            if y_start == -1:  # no potential heart found so far
                if (vertical_slice[ay] == self.black_heart_saved[0]).all():  # this could be heart
                    y_start = ay
                    equal_count = 1
            elif (vertical_slice[ay] == self.black_heart_saved[equal_count]).all():  # one more row equal
                equal_count += 1
                if equal_count == numpy.shape(self.black_heart_saved)[0]:  # found entire heart
                    if y_start < self.feed_top:  # higher than toolbar
                        # print('No heart found: y_start < feed_top.')
                        return -1
                    elif y_start + equal_count > self.feed_bottom:  # lower than bottom bar
                        # print('No heart found: y_start + equal_count > feed_bottom.')
                        return -1
                    else:
                        top_check = y_start - 5
                        bottom_check = y_start + equal_count + 5
                        if top_check < self.feed_top:  # scroll down 10px to do the check
                            # print('Could not verify: top_check < feed_top')
                            return -1
                        elif bottom_check > self.feed_bottom:  # scroll up 10px to do the check
                            # print('Could not verify: bottom_check > feed_bottom')
                            return -1
                        # the potential heart has white pixels on both top and bottom
                        else:
                            for i in numpy.nditer(vertical_slice[top_check]):
                                if i != 255:
                                    # print('top_check is not all white!')
                                    return -1
                            for i in numpy.nditer(vertical_slice[bottom_check]):
                                if i != 255:
                                    # print('bottom_check is not all white!')
                                    return -1
                            return y_start

        # print('Potential heart not found.')
        return -1

    def find_follow_button_y_array(self):
        image = self.screenshot()
        vertical_slice = image[self.follow_top:self.feed_bottom, self.follow_button_x]
        follow_buttons_y = []
        # the input will have one column of pixels
        same_button = False
        for row in range(numpy.shape(vertical_slice)[0]):
            if (vertical_slice[row] == [0, 149, 246, 255]).all():
                if not same_button:
                    follow_buttons_y.append(row + self.follow_top)
                    same_button = True
            if (vertical_slice[row] == [255, 255, 255, 255]).all():
                if same_button:
                    same_button = False
        return follow_buttons_y

    def find_first_image_y(self):
        # to like the first image of a user
        # find four pixels of [38, 38, 38, 255], expect one gray pixel and one white pixel
        image = self.screenshot()
        vertical_slice = image[:, self.left_thin_margin]
        first_y = -1
        continuous_black_pixels = 0
        for row in range(numpy.shape(vertical_slice)[0]):
            if (vertical_slice[row] == [38, 38, 38, 255]).all():
                if first_y == -1:
                    first_y = row
                continuous_black_pixels += 1
                if continuous_black_pixels > 4:
                    first_y = 0
                    continuous_black_pixels = -1
            elif (vertical_slice[row] == [255, 255, 255, 255]).all():
                if continuous_black_pixels == 4:
                    return first_y + 240  # center_Y of the first image
        return first_y

    def tap_on_back(self):
        self.device.shell('input keyevent 4')

    def sleep1(self):
        if self.ui_state == UiState.paused:
            self.pause_for_a_sec()
        else:
            time.sleep(1)

    def sleep2(self):
        if self.ui_state == UiState.paused:
            self.pause_for_a_sec()
        else:
            time.sleep(2)

    def sleep5(self):
        if self.ui_state == UiState.paused:
            self.pause_for_a_sec()
        else:
            time.sleep(5)

    def pause_for_a_sec(self):
        while self.ui_state == UiState.paused:
            time.sleep(1)

    def scroll_a_page(self):
        self.device.shell(f'input touchscreen swipe 500 {self.feed_bottom} 500 {self.follow_top} 2000')

    def screenshot(self):
        image = self.device.screencap()

        with open('screen.png', 'wb') as f:
            f.write(image)

        image = Image.open('screen.png')
        image = numpy.array(image, dtype=numpy.uint8)
        return image

    def run(self, *args, **kwargs):

        while self.ui_state == UiState.running or self.ui_state == UiState.paused:

            if self.run_mode == RunMode.continuous:  # same with like_place
                black_heart_y = self.find_black_heart()
                if black_heart_y > 0:
                    self.device.shell(f'input tap 91 {black_heart_y + 10}')
                    self.likes.set(self.likes.get() + 1)
                    self.device.shell(f'input touchscreen swipe 500 2000 500 1000')
                else:
                    self.device.shell(f'input touchscreen swipe 500 2000 500 1500')
            elif self.run_mode == RunMode.followers:
                # find follow buttons
                follow_buttons_y = self.find_follow_button_y_array()
                if not follow_buttons_y:
                    # scroll a entire page
                    self.scroll_a_page()
                else:
                    # click on the users found in this page
                    for y in follow_buttons_y:
                        if self.ui_state == UiState.stopped:
                            break
                        self.device.shell(f'input tap {self.half_width} {y}')  # tap on user
                        self.sleep5()  # load user page
                        first_image_y = self.find_first_image_y()
                        if first_image_y > 0:  # found an image to like
                            self.device.shell(f'input tap 250 {first_image_y}')  # tap on image
                            self.sleep2()
                            black_heart_y = self.find_black_heart()
                            if black_heart_y > 0:
                                self.device.shell(f'input tap 91 {black_heart_y + 10}')
                                self.likes.set(self.likes.get() + 1)
                            if self.ui_state == UiState.stopped:
                                break
                            self.sleep1()
                            self.tap_on_back()  # to user view
                            self.sleep1()
                            self.tap_on_back()  # to follower view
                        else:  # private user or no image
                            self.tap_on_back()
                        self.sleep1()
                    self.scroll_a_page()
            self.sleep1()
