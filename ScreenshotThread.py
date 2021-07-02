import threading
from ppadb.client import Client
import os
import datetime
from PIL import Image
import numpy
from numpy import load

class ScreenshotThread(threading.Thread):
    os.system('cmd /c "C:\\Users\\David\\AppData\\Local\\Android\\Sdk\\platform-tools\\adb devices"')
    adb = Client(host='127.0.0.1', port=5037)
    devices = adb.devices()

    if len(devices) == 0:
        print('no device attached')
        quit()

    device = devices[0]

    def screenshot(self):
        image = self.device.screencap()
        timestamp = str(datetime.datetime.now()).replace(':', '-')

        with open(f'{timestamp}.png', 'wb') as f:
            f.write(image)

        # Enable the code below in case the heart icon changed again.

        # image = Image.open(f'{timestamp}.png')
        # image_array = numpy.array(image, dtype=numpy.uint8)
        # like_image = image_array[2115:2181, 90:92]
        # numpy.save('like_heart_new.npy', like_image)

    def run(self, *args, **kwargs):
        self.screenshot()
