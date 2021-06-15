import threading
from tkinter import IntVar
from ppadb.client import Client
from PIL import Image
import numpy
from numpy import load
import time
import os
import pytesseract
from RunMode import RunMode
from UiState import UiState
import sqlite3
import datetime


class WorkerThread(threading.Thread):

    def __init__(self, mode: RunMode, count: IntVar):
        threading.Thread.__init__(self)
        self.run_mode = mode
        self.likes = count

    ui_state = UiState.running
    run_mode = RunMode.followers
    likes: IntVar
    # these numbers are for Pixel 2 XL
    feed_top = 294  # top bar bottom pixel
    follow_top = 466  # top bar of follower page is taller
    feed_bottom = 2536  # bottom bar top pixel
    half_width = 720  # half of the screen width
    follow_button_x = 1050  # this point should have blue(0, 149, 246, 255) if it is follow button
    left_thin_margin = 5  # help to decide whether there is a tab indicator (thin black horizontal line)
    name_start_x = 300  # to get names of followers (or likers)
    name_end_x = 990
    name_top_to_follow_button = 65
    name_bottom_to_follow_button = 170
    days_before_revisit = 30

    os.system('cmd /c "C:\\Users\\David\\AppData\\Local\\Android\\Sdk\\platform-tools\\adb devices"')
    adb = Client(host='127.0.0.1', port=5037)
    devices = adb.devices()
    pytesseract.pytesseract.tesseract_cmd = 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

    connection = sqlite3.connect('likes.db', check_same_thread=False)
    cursor = connection.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS likes(user_id TEXT NOT NULL PRIMARY KEY, last_visit TEXT NOT NULL, 
        is_private INTEGER DEFAULT 0, times_seen INTEGER DEFAULT 1)""")

    if len(devices) == 0:
        print('no device attached')
        quit()

    device = devices[0]

    black_heart_saved = load('black_heart_saved.npy')
    current_screen = numpy.array([])  # use one variable instead of multiple to hold current screen

    # find start Y of black heart. Return -1 if not found
    def find_black_heart(self) -> int:
        vertical_slice = self.current_screen[:, 90:92]
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
            else:
                y_start = -1
                equal_count = 0
        # print('Potential heart not found.')
        return -1

    def find_red_heart(self) -> int:
        vertical_slice = self.current_screen[:, 90:92]
        y_start = -1
        equal_count = 0
        for ay in range(numpy.shape(vertical_slice)[0]):
            if (vertical_slice[ay] == [237, 73, 86, 255]).all():  # this could be heart
                if y_start == -1:  # no potential red heart found so far
                    y_start = ay
                equal_count += 1
                if equal_count == 2:
                    break
            else:
                y_start = -1
                equal_count = 0
        if y_start > 0:
            # print('Potential heart not found.')
            # check the text is below contains "Liked" or " likes"
            no_likes_image = self.current_screen[y_start + 110: y_start + 170, 40: 1300]
            ocr_result = pytesseract.image_to_string(Image.fromarray(no_likes_image),
                                                     config='tessedit_char_whitelist=0123456789abcdefghijkLlmnopqrstuvwxyz')
            # print(f'ocr_result: {ocr_result}')
            if 'Liked' in ocr_result or 'likes' in ocr_result or 'views' in ocr_result:
                return y_start
        return -1

    def find_black_or_red_heart(self) -> int:
        heart_y = self.find_black_heart()
        if heart_y > 0:
            return heart_y
        else:
            heart_y = self.find_red_heart()
        if heart_y > 0:
            return heart_y
        return -1

    def should_visit(self, u_name):
        # look up db see if user has been visited
        result = self.connection.execute('''SELECT * FROM likes WHERE user_id=?''', (u_name,)).fetchone()
        if result:
            update_sql = "INSERT OR REPLACE INTO likes (user_id, last_visit, is_private, times_seen) VALUES (?, ?, ?, ?)"
            self.connection.execute(update_sql, (result[0], result[1], result[2], result[3] + 1))
            self.connection.commit()
            if result[2]:
                # the user is known to be private
                return False
            time_since_last_visit = datetime.datetime.now() - datetime.datetime.strptime(result[1],
                                                                                         '%Y-%m-%d %H:%M:%S.%f')
            if time_since_last_visit.days > self.days_before_revisit:
                return True
            else:
                return False
        else:
            return True

    def save_visited(self, user_id: str, success: bool):
        sql = "INSERT OR REPLACE INTO likes (user_id, last_visit, is_private, times_seen) VALUES (?, ?, ?, ?)"
        timestamp = str(datetime.datetime.now())
        existing_user = self.connection.execute('''SELECT * FROM likes WHERE user_id=?''', (user_id,)).fetchone()
        seen_times = existing_user[3] if existing_user else 1
        if success:
            self.connection.execute(sql, (user_id, timestamp, False, seen_times))
            self.connection.commit()
            # print(f'visit user {user_id} done')
        else:
            # check if the account is private
            ocr_result = pytesseract.image_to_string(Image.open('screen.png'),
                                                     config='tessedit_char_whitelist=0123456789abcdefghijklmnopPqrstuvwxyz')
            if "Private" in ocr_result:
                self.connection.execute(sql, (user_id, timestamp, True, seen_times))
                # print(f'visit user {user_id} not done: Private User')
            else:
                # the visit was not successful due to slow connection
                # could also be the user has zero image, consider visited for a number of days is fine
                self.connection.execute(sql, (user_id, timestamp, False, seen_times))
            self.connection.commit()
        return

    bottom_button_Y = 0
    last_ocr_result = ''
    def find_follow_button_y_array(self, view_top=follow_top):
        vertical_slice = self.current_screen[view_top:self.feed_bottom, self.follow_button_x]
        follow_buttons_y = {}
        # the input will have one column of pixels
        follow_found = False
        unfollow_found = 0
        for row in range(numpy.shape(vertical_slice)[0]):
            if (vertical_slice[row] == [255, 255, 255, 255]).all():
                follow_found = False
            elif (vertical_slice[row] == [219, 219, 219, 255]).all():  # gray unfollow button
                if unfollow_found == 0:
                    # update last button Y
                    self.bottom_button_Y = max(self.bottom_button_Y, row + view_top)
                    current_y_follow = row + view_top
                    self.bottom_button_Y = max(self.bottom_button_Y, current_y_follow)
                    name_image = self.current_screen[
                                 current_y_follow - self.name_top_to_follow_button: current_y_follow + self.name_bottom_to_follow_button,
                                 self.name_start_x: self.name_end_x]
                    ocr_result = pytesseract.image_to_string(Image.fromarray(name_image),
                                                             config='tessedit_char_whitelist=0123456789abcdefghijklmnopqrstuvwxyz').split(
                        "\n")[0]
                    self.last_ocr_result = ocr_result
                unfollow_found += 1
                if unfollow_found == 8:
                    unfollow_found = 0
            elif (vertical_slice[row] == [0, 149, 246, 255]).all():  # blue follow button
                if not follow_found:
                    # update follow and user name map
                    current_y_follow = row + view_top
                    self.bottom_button_Y = max(self.bottom_button_Y, current_y_follow)
                    name_image = self.current_screen[
                                 current_y_follow - self.name_top_to_follow_button: current_y_follow + self.name_bottom_to_follow_button,
                                 self.name_start_x: self.name_end_x]
                    ocr_result = pytesseract.image_to_string(Image.fromarray(name_image),
                                                             config='tessedit_char_whitelist=0123456789abcdefghijklmnopqrstuvwxyz').split(
                        "\n")[0]
                    self.last_ocr_result = ocr_result
                    # print(f'name of follower: {ocr_result}')
                    if self.should_visit(ocr_result):
                        follow_buttons_y[current_y_follow] = ocr_result
                follow_found = True
        return follow_buttons_y

    def find_first_image_y(self):
        # to like the first image of a user
        # find four pixels of [38, 38, 38, 255], expect one gray pixel and one white pixel
        vertical_slice = self.current_screen[:, self.left_thin_margin]
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
                    if (self.current_screen[first_y + 240, 240] == self.current_screen[first_y + 240, 720]).all():
                        return -1
                    return first_y + 240  # center_Y of the first image
        return first_y

    def tap_on_back(self):
        self.device.shell('input keyevent 4')

    def sleep1(self):
        if self.ui_state == UiState.paused:
            self.pause_for_a_sec()
        else:
            time.sleep(1)

    def sleep_half(self):
        if self.ui_state == UiState.paused:
            self.pause_for_a_sec()
        else:
            time.sleep(0.5)

    def pause_for_a_sec(self):
        while self.ui_state == UiState.paused:
            time.sleep(1)

    def scroll_a_page(self, start=feed_bottom, end=follow_top):
        if start == 0:
            return
        self.device.shell(f'input touchscreen swipe 500 {start} 500 {end} 2000')
        self.bottom_button_Y = 0
        self.last_ocr_result = ''

    def screenshot(self):
        image = self.device.screencap()
        with open('screen.png', 'wb') as f:
            f.write(image)
        image = Image.open('screen.png')
        self.current_screen = numpy.array(image, dtype=numpy.uint8)

    def visit_users_and_like(self, y_map):
        for y in y_map.keys():
            if self.ui_state == UiState.stopped:
                break
            self.device.shell(f'input tap {self.half_width} {y}')  # tap on user
            self.sleep1()
            self.screenshot()
            first_image_y = self.find_first_image_y()
            if first_image_y > 0:  # found an image to like
                self.device.shell(f'input tap 250 {first_image_y}')  # tap on image
                self.sleep_half()
                self.screenshot()
                black_heart_y = self.find_black_heart()
                if black_heart_y > 1300:  # in case the user's icon has heart
                    self.device.shell(f'input tap 91 {black_heart_y + 10}')
                    self.save_visited(user_id=y_map[y], success=True)
                    self.likes.set(self.likes.get() + 1)
                else:
                    self.save_visited(user_id=y_map[y], success=True)
                if self.ui_state == UiState.stopped:
                    break
                self.tap_on_back()  # to user view
                self.sleep_half()
                self.tap_on_back()  # to follower view
            else:  # private user or no image
                self.save_visited(user_id=y_map[y], success=False)
                self.tap_on_back()

    def run(self, *args, **kwargs):
        copy_of_last_ocr_result = ''
        while self.ui_state == UiState.running or self.ui_state == UiState.paused:
            if self.run_mode == RunMode.posts:
                self.screenshot()
                black_or_red_heart_y = self.find_black_or_red_heart()
                if black_or_red_heart_y > 0:
                    self.device.shell(f'input tap 91 {black_or_red_heart_y + 150}')
                    # now in likes page
                    self.sleep_half()
                    while self.ui_state == UiState.running:
                        self.screenshot()
                        cur_map = self.find_follow_button_y_array(view_top=self.feed_top)
                        if len(copy_of_last_ocr_result) > 0 and copy_of_last_ocr_result == self.last_ocr_result:
                            break
                        if cur_map:
                            self.visit_users_and_like(cur_map)
                        copy_of_last_ocr_result = str(self.last_ocr_result)
                        self.scroll_a_page(start=self.bottom_button_Y,
                                           end=self.feed_top - self.name_bottom_to_follow_button)
                    self.tap_on_back()
                    self.scroll_a_page(start=black_or_red_heart_y, end=40)
                else:
                    self.device.shell(f'input touchscreen swipe 500 2536 500 1200 1000')
            elif self.run_mode == RunMode.continuous:  # same with like_place
                self.screenshot()
                black_heart_y = self.find_black_heart()
                if black_heart_y > 0:
                    self.device.shell(f'input tap 91 {black_heart_y + 10}')
                    self.likes.set(self.likes.get() + 1)
                    self.device.shell(f'input touchscreen swipe 500 {black_heart_y} 500 100 1000')
                    self.screenshot()
                else:
                    # scroll to half and look for heart again
                    self.device.shell(f'input touchscreen swipe 500 2536 500 1200 1000')
                    self.screenshot()
            elif self.run_mode == RunMode.followers:
                # find follow buttons
                self.screenshot()
                followers_y = self.find_follow_button_y_array()
                if len(copy_of_last_ocr_result) > 0 and copy_of_last_ocr_result == self.last_ocr_result:
                    self.ui_state = UiState.stopped
                    break
                if followers_y:
                    self.visit_users_and_like(followers_y)
                copy_of_last_ocr_result = str(self.last_ocr_result)
                self.scroll_a_page(start=self.bottom_button_Y,
                                   end=self.follow_top - self.name_bottom_to_follow_button)
                self.sleep_half()

            self.sleep1()
