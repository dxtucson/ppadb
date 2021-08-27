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

# Instagram has a limit of 1000 per 24 hours
likes_per_day_limit = 950
days_before_revisit = 100


class WorkerThread(threading.Thread):

    def __init__(self, mode: RunMode, count: IntVar, exceeded):
        threading.Thread.__init__(self)
        self.run_mode = mode
        self.likes = count
        self.show_limit_exceeded_label = exceeded

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

    os.system('cmd /c "C:\\Users\\David\\AppData\\Local\\Android\\Sdk\\platform-tools\\adb devices"')
    adb = Client(host='127.0.0.1', port=5037)
    devices = adb.devices()
    pytesseract.pytesseract.tesseract_cmd = 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

    connection = sqlite3.connect('likes.db', check_same_thread=False)
    cursor = connection.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS likes(user_id TEXT NOT NULL PRIMARY KEY, last_visit TEXT NOT NULL, 
        is_private INTEGER DEFAULT 0, times_seen INTEGER DEFAULT 1, like_success INTEGER DEFAULT 0)""")

    if len(devices) == 0:
        print('no device attached')
        quit()

    device = devices[0]

    current_screen = numpy.array([])  # use one variable instead of multiple to hold current screen

    # find start Y of black heart. Return -1 if not found
    def find_black_heart(self) -> int:
        vertical_slice = self.current_screen[:, 91]
        for ay in range(numpy.shape(vertical_slice)[0] - 57):
            if (vertical_slice[ay] == [38, 38, 38, 255]).all():
                # check ay + 57
                if (vertical_slice[ay + 57] == [38, 38, 38, 255]).all():
                    # check middle
                    if (vertical_slice[ay + 28] == [255, 255, 255, 255]).all():
                        # at least 40 continuous white pixels are needed to have an accurate judgement for heart
                        # the original logic is proven to be not accurate enough with a screenshot
                        this_is_heart = True
                        for pixel in vertical_slice[ay + 8: ay + 48]:
                            if not (pixel == [255, 255, 255, 255]).all():
                                this_is_heart = False
                                break
                        if this_is_heart:
                            return ay
            elif (vertical_slice[ay] == [237, 73, 86, 255]).all() and (
                    vertical_slice[ay + 28] == [237, 73, 86, 255]).all():
                return -1
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
            update_sql = "INSERT OR REPLACE INTO likes (user_id, last_visit, is_private, times_seen, like_success) VALUES (?, ?, ?, ?, ?)"
            self.connection.execute(update_sql, (result[0], result[1], result[2], result[3] + 1, result[4]))
            self.connection.commit()
            if result[2]:
                # the user is known to be private
                return False
            time_since_last_visit = datetime.datetime.now() - datetime.datetime.strptime(result[1],
                                                                                         '%Y-%m-%d %H:%M:%S.%f')
            if time_since_last_visit.days > days_before_revisit:
                return True
            else:
                return False
        else:
            return True

    def update_db_after_visit(self, user_id: str, visit_success: bool, clicked_on_like: bool, is_private: bool):
        sql = "INSERT OR REPLACE INTO likes (user_id, last_visit, is_private, times_seen, like_success) VALUES (?, ?, ?, ?, ?)"
        timestamp = str(datetime.datetime.now())
        existing_user = self.connection.execute('''SELECT * FROM likes WHERE user_id=?''', (user_id,)).fetchone()
        seen_times = existing_user[3] if existing_user else 1
        if visit_success:
            if clicked_on_like:
                self.connection.execute(sql, (user_id, timestamp, False, seen_times, True))
            else:
                self.connection.execute(sql, (user_id, timestamp, False, seen_times, False))
            self.connection.commit()
        elif is_private:
            self.connection.execute(sql, (user_id, timestamp, True, seen_times, False))
            self.connection.commit()
        elif not existing_user:
            self.connection.execute(sql, (user_id, timestamp, False, 1, False))
            self.connection.commit()

    def check_limit_exceeded(self):
        current_time = datetime.datetime.now() - datetime.timedelta(hours=24)
        count = self.connection.execute(
            '''SELECT COUNT(*) AS likes_in_24_hrs, * FROM likes WHERE like_success == 1 AND last_visit >= ?''',
            (current_time,)).fetchone()
        if count[0] > self.likes.get():
            self.likes.set(count[0])
        if count[0] >= likes_per_day_limit:
            self.ui_state = UiState.reached_limit
            # find out when is safe to resume
            # Calculate when another 200 likes will pass 24 hours.
            row_200th = self.connection.execute(
                '''SELECT last_visit FROM likes WHERE last_visit >= ? ORDER BY last_visit LIMIT 1 OFFSET 200''',
                (current_time,)).fetchone()[0]
            safe_datetime = str(
                datetime.datetime.strptime(row_200th, '%Y-%m-%d %H:%M:%S.%f') + datetime.timedelta(hours=24))[:16]
            self.show_limit_exceeded_label(f'More likes will be available after {safe_datetime}')

    bottom_button_Y = 0
    last_ocr_result = ''

    def find_follow_button_y_array(self, view_top=follow_top):
        vertical_slice = self.current_screen[view_top:self.feed_bottom, self.follow_button_x]
        follow_buttons_y = {}
        # the input will have one column of pixels
        follow_found = False
        for row in range(numpy.shape(vertical_slice)[0]):
            if (vertical_slice[row] == [255, 255, 255, 255]).all():
                follow_found = False
            elif (vertical_slice[row] == [219, 219, 219, 255]).all() and (
                    row + 97 < numpy.shape(vertical_slice)[0] and (vertical_slice[row + 97] == [219, 219, 219,
                                                                                                255]).all()):  # gray unfollow button, ignore partially shown buttons
                # update last button Y
                current_y_follow = row + view_top
                self.bottom_button_Y = max(self.bottom_button_Y, current_y_follow)
                name_image = self.current_screen[
                             current_y_follow - self.name_top_to_follow_button: current_y_follow + self.name_bottom_to_follow_button,
                             self.name_start_x: self.name_end_x]
                ocr_result = pytesseract.image_to_string(Image.fromarray(name_image),
                                                         config='tessedit_char_whitelist=0123456789abcdefghijklmnopqrstuvwxyz').split(
                    "\n")[0]
                self.last_ocr_result = ocr_result

            elif (vertical_slice[row] == [0, 149, 246, 255]).all() and (row + 97 < numpy.shape(vertical_slice)[0] and (
                    vertical_slice[row + 97] == [0, 149, 246,
                                                 255]).all()):  # blue follow button, ignore partially shown buttons
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
                    first_y = -1
                    continuous_black_pixels = 0
            elif (vertical_slice[row] == [255, 255, 255, 255]).all():
                if continuous_black_pixels == 4:
                    if (self.current_screen[first_y + 240, 240] == self.current_screen[first_y + 240, 720]).all() and (
                            self.current_screen[first_y + 240, 720] == self.current_screen[first_y + 240, 1200]).all():
                        if (self.current_screen[first_y + 240, 240] == [239, 239, 239, 255]).all():
                            return first_y + 240
                        else:
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
        # print(f'scroll up called. start={start}, end={end}')
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
            if self.ui_state == UiState.stopped or self.ui_state == UiState.reached_limit:
                break
            elif self.ui_state == UiState.paused:
                self.pause_for_a_sec()
            self.device.shell(f'input tap {self.half_width} {y}')  # tap on user
            self.sleep1()
            self.sleep_half()
            self.screenshot()

            private_user = False
            post_seen = False
            like_clicked = False

            first_image_y = self.find_first_image_y()
            if first_image_y < 0:  # private or too slow
                ocr_result = pytesseract.image_to_string(self.current_screen,
                                                         config='tessedit_char_whitelist=0123456789abcdefghijklmnopPqrstuvwxyz')
                if "Private" in ocr_result:
                    private_user = True

            else:  # found an image to like
                self.device.shell(f'input tap 250 {first_image_y}')  # tap on image
                self.sleep_half()
                self.screenshot()
                # if "Posts" are not found, it means clicking on the first image failed. Only one back is needed
                posts_area = self.current_screen[150: 235, 230: 445]
                ocr_result = pytesseract.image_to_string(Image.fromarray(posts_area),
                                                         config='tessedit_char_whitelist=0123456789abcdefghijklmnoPpqrsStuvwxyz').split(
                    "\n")[0]
                if ocr_result.startswith('Posts'):
                    # normal flow
                    post_seen = True
                    red_heart_y = self.find_red_heart()
                    if red_heart_y < 0:  # Never liked this post
                        black_heart_y = self.find_black_heart()
                        if black_heart_y > 1300:
                            self.device.shell(f'input tap 91 {black_heart_y}')
                            like_clicked = True
                            self.screenshot()
                            views_and_likes_area = self.current_screen[150:230, 220:720]
                            likes_ocr = pytesseract.image_to_string(Image.fromarray(views_and_likes_area),
                                                                    config='tessedit_char_whitelist=0123456789abcdefghijkLlmnopqrstuVvwxyz').split(
                                "\n")[0]
                            if likes_ocr.startswith('Likes') or likes_ocr.startswith('Views'):
                                # entered likes view by error, one more click is needed
                                self.tap_on_back()
                                like_clicked = False

            self.update_db_after_visit(user_id=y_map[y], visit_success=post_seen, clicked_on_like=like_clicked,
                                       is_private=private_user)
            if like_clicked:
                self.likes.set(self.likes.get() + 1)
                self.check_limit_exceeded()
            if post_seen:
                self.tap_on_back()  # to user view
                self.sleep_half()
            self.tap_on_back()  # to follower view

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
                    self.device.shell(f'input tap 91 {black_heart_y}')
                    self.likes.set(self.likes.get() + 1)
                    self.check_limit_exceeded()
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
                if len(followers_y) == 0:
                    # see if the screen has "suggestions for you"
                    suggested_area = self.current_screen[450: 650, :]
                    ocr_result = pytesseract.image_to_string(Image.fromarray(suggested_area),
                                                             config='tessedit_char_whitelist=0123456789abcdefghijklmnopqrsStuvwxyz').split(
                        "\n")[0]
                    # print(ocr_result)
                    if "Suggestions for you" in ocr_result:
                        self.ui_state = UiState.stopped
                        break
                if followers_y:
                    self.visit_users_and_like(followers_y)
                self.scroll_a_page(start=self.bottom_button_Y,
                                   end=self.follow_top - self.name_bottom_to_follow_button)
