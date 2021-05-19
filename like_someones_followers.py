#!/usr/bin/env python3

from ppadb.client import Client
from PIL import Image
import numpy
from numpy import save
from numpy import load
import time
import os

os.system('cmd /c "C:\\Users\\David\\AppData\\Local\\Android\\Sdk\\platform-tools\\adb devices"')

adb = Client(host='127.0.0.1', port=5037)
devices = adb.devices()

if len(devices) == 0:
    print('no device attached')
    quit()

device = devices[0]

black_heart_saved = load('black_heart_saved.npy')

# these numbers are for Pixel 2 XL
feed_top = 97  # top bar bottom pixel
follow_top = 466  # top bar of follower page is taller
feed_bottom = 2536  # bottom bar top pixel
half_width = 720  # half of the screen width
follow_button_x = 1050  # this point should have blue(0, 149, 246, 255) if it is follow button
left_thin_margin = 20  # help to decide whether there is a tab indicator (thin black horizontal line)


# find start Y of black heart. Return -1 if not found
def find_black_heart(vertical_slice: numpy.array) -> int:
    y_start = -1
    equal_count = 0
    for ay in range(numpy.shape(vertical_slice)[0]):
        if y_start == -1:  # no potential heart found so far
            if (vertical_slice[ay] == black_heart_saved[0]).all():  # this could be heart
                y_start = ay
                equal_count = 1
        elif (vertical_slice[ay] == black_heart_saved[equal_count]).all():  # one more row equal
            equal_count += 1
            if equal_count == numpy.shape(black_heart_saved)[0]:  # found entire heart
                if y_start < feed_top:  # higher than toolbar
                    print('No heart found: y_start < feed_top.')
                    return -1
                elif y_start + equal_count > feed_bottom:  # lower than bottom bar
                    print('No heart found: y_start + equal_count > feed_bottom.')
                    return -1
                else:
                    top_check = y_start - 5
                    bottom_check = y_start + equal_count + 5
                    if top_check < feed_top:  # scroll down 10px to do the check
                        print('Could not verify: top_check < feed_top')
                        return -1
                    elif bottom_check > feed_bottom:  # scroll up 10px to do the check
                        print('Could not verify: bottom_check > feed_bottom')
                        return -1
                    # the potential heart has white pixels on both top and bottom
                    else:
                        for i in numpy.nditer(vertical_slice[top_check]):
                            if i != 255:
                                print('top_check is not all white!')
                                return -1
                        for i in numpy.nditer(vertical_slice[bottom_check]):
                            if i != 255:
                                print('bottom_check is not all white!')
                                return -1
                        return y_start

    print('Potential heart not found.')
    return -1


def find_follow_button_y_array(vertical_slice: numpy.array):
    follow_buttons_y = []
    # the input will have one column of pixels
    same_button = False
    for row in range(numpy.shape(vertical_slice)[0]):
        if (vertical_slice[row] == [0, 149, 246, 255]).all():
            if not same_button:
                follow_buttons_y.append(row + follow_top)
                same_button = True
        if (vertical_slice[row] == [255, 255, 255, 255]).all():
            if same_button:
                same_button = False
    return follow_buttons_y


def find_first_image_y(vertical_slice: numpy.array):
    # to like the first image of a user
    # find four pixels of [38, 38, 38, 255], expect one gray pixel and one white pixel
    first_image_y = -1
    continuous_black_pixels = 0
    for row in range(numpy.shape(vertical_slice)[0]):
        if (vertical_slice[row] == [38, 38, 38, 255]).all():
            if first_image_y == -1:
                first_image_y = row
            continuous_black_pixels += 1
            if continuous_black_pixels > 4:
                first_image_y = 0
                continuous_black_pixels = -1
        elif (vertical_slice[row] == [255, 255, 255, 255]).all():
            if continuous_black_pixels == 4:
                return first_image_y + 240  # center_Y of the first image
    return first_image_y


def tap_on_back():
    device.shell('input keyevent 4')


def sleep1():
    time.sleep(1)


while True:
    image = device.screencap()

    with open('screen.png', 'wb') as f:
        f.write(image)

    image = Image.open('screen.png')
    image = numpy.array(image, dtype=numpy.uint8)

    # find black heart
    # vertical_sample1 = image[:, 90:92]
    # result1 = find_black_heart(vertical_sample1)

    # find follow buttons
    # vertical_sample2 = image[follow_top:feed_bottom, follow_button_x]
    # result2 = find_follow_button_y_array(vertical_sample2)
    # from 2007

    vertical_sample3 = image[:, left_thin_margin]
    result3 = find_first_image_y(vertical_sample3)

    # device.shell(f'input tap {half_width} {result2[1]}')

    device.shell(f'input tap 250 {result3}')
    # tap on the first follower

    # im = Image.fromarray(vertical_sample2)
    # im.save("follow_button_slice.png")
    # save('black_heart_slice.npy', heart_sub)

    # steps to save snapshot of a heart
    # heart_sub = image[2130:2147, 89:93]
    # im = Image.fromarray(heart_sub)
    # im.save("vertical_slice.png")
    # save('black_heart_slice.npy', heart_sub)

    # click on like or keep scrolling
    # if result > 0:
    #     device.shell(f'input tap 91 {result + 10}')
    #     device.shell(f'input touchscreen swipe 500 2000 500 1000')
    # else:
    #     device.shell(f'input touchscreen swipe 500 2000 500 1500')
    sleep1()
    tap_on_back()
    sleep1()