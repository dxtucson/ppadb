#!/usr/bin/env python3

from ppadb.client import Client
from PIL import Image
import numpy
from numpy import save
from numpy import load
import time

adb = Client(host='127.0.0.1', port=5037)
devices = adb.devices()

if len(devices) == 0:
    print('no device attached')
    quit()

device = devices[0]

black_heart_saved = load('black_heart_saved.npy')
feed_top = 97
feed_bottom = 2536


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


while True:
    image = device.screencap()

    with open('screen.png', 'wb') as f:
        f.write(image)

    image = Image.open('screen.png')
    image = numpy.array(image, dtype=numpy.uint8)
    vertical_sample = image[:, 90:92]
    result = find_black_heart(vertical_sample)

    # steps to save snapshot of a heart
    # heart_sub = image[2130:2147, 89:93]
    # im = Image.fromarray(heart_sub)
    # im.save("vertical_slice.png")
    # save('black_heart_slice.npy', heart_sub)

    if result > 0:
        device.shell(f'input tap 91 {result + 10}')
        device.shell(f'input touchscreen swipe 500 2000 500 1000')
    else:
        device.shell(f'input touchscreen swipe 500 2000 500 1500')
    time.sleep(1)

# places in Hilo
# '4573910',  # Hawai`i Community College
#                '214565960',  # Hawaiian Style Café - Hilo
#                '652287',  # Cafe 100
#                '1369906793116040',  # KTA Super Stores
#                '286678182',  # Hilo High School
#                '252552111906405',  # Waiakea High School
#                '220719332',  # Suisan Fish Market
#                '259904138',  # Waikoloa, Hawaii
#                '248933518',  # Waimea Big Island
#                '153047301946370',  # Downtown Hilo
#                '353971',  # Big Island Candies
#                '5123262',  # Waiolena
#                '255285948',  # Keaau, Hawaii
#                '528017',  # University of Hawaiʻi at Hilo
#                '1014734662',  # Manono Street Marketplace
#                '215140125',  # Liliuokalani Park and Gardens
#                '7440188',  # Bayfront Beach Park
#                '234437663',  # Mauna Kea
#                '832944',  # Hilo Farmers Market
#                '217860447',  # Hilo, HI
#                '1400401506921170',  # Kamana Kitchen Indian Cuisine
#                '109359892424006',  # Pepeekeo, Hawaii
#                '213061859',  # Rainbow Falls
#                '753431934796611',  # Hilo Volcanoes National Park and Rainbow Falls Excursion
#                '1683284565326878'  # Boiling Pots, Wailuku River
