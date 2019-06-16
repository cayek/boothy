import cups
import tkinter as tk
import itertools
from PIL import ImageTk, Image, ImageDraw, ImageFont
import logging
import time
import subprocess
import picamera
import RPi.GPIO as GPIO


def init_logger(output_dir="./logs/"):
    logger = logging.getLogger("booth")
    logger.setLevel(logging.DEBUG)
    # create console handler and set level to info
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    # create error file handler and set level to error
    handler = logging.FileHandler(output_dir+"/"+time.strftime("%Y%m%d")+"_error.log","w", encoding=None, delay="true")
    handler.setLevel(logging.ERROR)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    # create debug file handler and set level to debug
    handler = logging.FileHandler(output_dir+"/"+time.strftime("%Y%m%d")+"_debug.log","w", encoding=None, delay="true")
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return(logger)


class Booth():
    def __init__(self,
                 logger,
                 wd=".",
                 screen_width=800,
                 screen_height=480,
                 camera_width=640,
                 camera_heigh=480,
                 countdown=3,
                 green_button_pin=26,
                 red_button_pin=16):
        self.countdown = countdown
        # init logger
        self.logger = logger
        self.wd = wd

        # init tk
        self.init_tk(wd, screen_width, screen_height)

        # init camera
        self.init_camera(camera_width, camera_heigh)

        # init gpio
        self.init_gpio(green_button_pin, red_button_pin)

        # montage command
        imgs = [["{}.jpg".format(i), "{}.jpg".format(i)] for i in range(1, 5)]
        imgs = list(itertools.chain.from_iterable(imgs))
        self.res_cmd = (["montage"]
                        + imgs
                        + ["-tile", "2x4", "-geometry", "+8+4"])
        imgs = ["{}.jpg".format(i) for i in range(1, 5)]
        self.show_cmd = (["montage"]
                         + imgs
                         + ["-tile", "2x2"]
                         + ["-geometry", "+2+2"])

    def init_tk(self, wd, screen_width, screen_height):
        # parameters
        self.w = screen_width
        self.h = screen_height
        # full screen
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.geometry("{0}x{1}+0+0".format(screen_width, screen_height))
        self.root.focus_set()  # <-- move focus to this widget
        self.root.bind("<Escape>", lambda e: e.widget.quit())
        # add images
        self.imgs = {}
        self.imgs["home"] = Image.open("{}/booth0.png".format(wd))
        d = ImageDraw.Draw(self.imgs["home"])
        fnt = ImageFont.truetype('Pillow/Tests/fonts/FreeMonoBold.ttf', 37)
        d.text((80, 340), "Appuyez sur le bouton VERT\n pour commencer !",
               font=fnt,
               fill=(0, 128, 0))
        self.imgs["smile"] = Image.open("{}/booth1.png".format(wd))
        self.imgs["end"] = Image.open("{}/end.png".format(wd))
        d = ImageDraw.Draw(self.imgs["end"])
        d.text((40, 15), "Les photos sont disponibles sur \n    https://photo.caye.fr ;)",
               font=fnt,
               fill=(220,20,60,255))
        d.text((120, 390), "Bouton VERT pour continuer.",
               font=fnt,
               fill=(0, 128, 0))
        self.imgs["print"] = Image.open("{}/print.png".format(wd))
        d = ImageDraw.Draw(self.imgs["print"])
        d.text((50, 380), "Les photos sont en cours \n   d'impression.....",
               font=fnt,
               fill=(220,20,60,255))

        # create canvas
        self.canvas = tk.Canvas(self.root,
                                width=self.w,
                                height=self.h)
        self.canvas.pack()
        self.canvas.configure(background='black')
        # image on canvas
        self.current_img = ImageTk.PhotoImage(self.imgs["home"])
        self.imagesprite = self.canvas.create_image(self.w/2,
                                                    self.h/2,
                                                    image=self.current_img)

    def init_camera(self, camera_width, camera_heigh):
        self.c_w, self.c_h = (camera_width, camera_heigh)
        self.logger.info("Initializing camera.")
        self.camera = picamera.PiCamera()
        # camera settings
        self.camera.resolution = (self.c_w, self.c_h)
        self.camera.framerate = 24
        self.camera.sharpness = 0
        self.camera.contrast = 0
        self.camera.brightness = 50
        self.camera.saturation = 0
        self.camera.ISO = 0
        self.camera.video_stabilization = False
        self.camera.exposure_compensation = 0
        self.camera.exposure_mode = 'auto'
        self.camera.meter_mode = 'average'
        self.camera.awb_mode = 'auto'
        self.camera.image_effect = 'none'
        self.camera.color_effects = None
        self.camera.rotation = 0
        self.camera.hflip = False
        self.camera.vflip = False
        self.camera.crop = (0.0, 0.0, 1.0, 1.0)

        self.overlay_renderer = None

    def init_gpio(self, green_button_pin, red_button_pin):
        self.green_button_pin, self.red_button_pin = (green_button_pin,
                                                      red_button_pin)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(green_button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(red_button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def show_home(self):
        self.current_img = ImageTk.PhotoImage(self.imgs["home"])
        self.canvas.itemconfig(self.imagesprite,
                               image=self.current_img)
        self.root.update()
        self.logger.info("show home")

    def show_toprint(self):
        # load image
        showprint_img = Image.open(self.showprint_path)
        # resize
        img_w, img_h = showprint_img.size
        if img_w > self.w or img_h > self.h:
            ratio = min(self.w/img_w, self.h/img_h)
            img_w = int(img_w*ratio)
            img_h = int(img_h*ratio)
            showprint_img = showprint_img.resize((img_w, img_h),
                                                 Image.ANTIALIAS)
        # get a drawing context
        d = ImageDraw.Draw(showprint_img)
        # draw text, half opacity
        fnt = ImageFont.truetype('Pillow/Tests/fonts/FreeMonoBold.ttf', 37)
        d.text((50, 150), "BOUTTON VERT : imprimer",
               font=fnt,
               fill=(0, 128, 0))
        d.text((50, 300), "BOUTTON ROUGE : acceuil",
               font=fnt,
               fill=(255, 51, 51))
        # show to screen
        self.current_img = ImageTk.PhotoImage(showprint_img)
        self.canvas.itemconfig(self.imagesprite,
                               image=self.current_img)
        self.root.update()
        self.logger.info("show toprint")

    def show_smile(self, write=None, x=100, y=380, size=80):
        smile_img = self.imgs["smile"].copy()
        if not write is None:
            d = ImageDraw.Draw(smile_img)
            # draw text, half opacity
            fnt = ImageFont.truetype('Pillow/Tests/fonts/FreeMonoBold.ttf', size)
            d.text((x, y), write,
                   font=fnt, fill=(220,20,60,200))
        self.current_img = ImageTk.PhotoImage(smile_img)
        self.canvas.itemconfig(self.imagesprite,
                               image=self.current_img)
        self.root.update()
        self.logger.info("show smile")

    def print_pic(self):
        self.logger.info("PRINT")
        self.current_img = ImageTk.PhotoImage(self.imgs["print"])
        self.canvas.itemconfig(self.imagesprite,
                               image=self.current_img)
        self.root.update()
        self.logger.info("show print in progress")
        # to be sure that the montage is over :D
        self.to_print_p.wait()
        # send print
        conn = cups.Connection()
        printers = conn.getPrinters()
        default_printer = "Canon_SELPHY_CP1300"
        if (default_printer in printers.keys()):
            cups.setUser('pi')
            conn.printFile(default_printer, self.toprint_path,
                           "boothy", {'fit-to-page':'True'})
        else:
            self.logger.info("Printer not found ! ")
        time.sleep(5)

    def user_input(self):
        green_event = False
        red_event = False
        output = None
        while output is None:
            green_state = GPIO.input(self.green_button_pin)
            red_state = GPIO.input(self.red_button_pin)
            if (not green_state) and (not green_event):
                self.logger.info("green down")
                green_event = True
            elif (not red_state) and (not red_event):
                self.logger.info("red down")
                red_event = True
            elif green_state and green_event:
                self.logger.info("green up")
                output = "green"
            elif red_state and red_event:
                self.logger.info("red up")
                output = "red"
        return output

    def add_preview_overlay(self, xcoord, ycoord,
                            fontSize, overlayText, color=(32, 178, 170, 210)):
        img = Image.new("RGBA", (self.c_w, self.c_h), (255, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.font = ImageFont.truetype(
            'Pillow/Tests/fonts/FreeMonoBold.ttf',
            fontSize)
        draw.text((xcoord, ycoord), overlayText, color)
        if self.overlay_renderer is None:
            self.overlay_renderer = self.camera.add_overlay(img.tobytes(),
                                                            layer=3,
                                                            size=img.size,
                                                            alpha=128)
        else:
            if self.remove_overlay:
                self.camera.remove_overlay(self.overlay_renderer)
            self.overlay_renderer = self.camera.add_overlay(img.tobytes(),
                                                            layer=3,
                                                            size=img.size,
                                                            alpha=128)
            # self.overlay_renderer.update(img.tobytes()) # generate error
        self.remove_overlay = True

    def countdown_from(self, countdown):
        s = countdown
        while s > 0:
            self.add_preview_overlay(250, 100, 240, str(s))
            time.sleep(1)
            s = s - 1

    def stop_camera_preview(self):
        self.camera.stop_preview()
        if self.remove_overlay:
            self.camera.remove_overlay(self.overlay_renderer)
            self.remove_overlay = False

    def capture_image(self, image_name):
        self.logger.info("Capture image {}".format(image_name))
        self.stop_camera_preview()
        self.camera.capture(image_name, resize=(self.c_w, self.c_h))
        self.camera.start_preview()

    def sync_withcloud(self):
        self.logger.info("Sync with piwigo cloud")
        p = subprocess.Popen(["sh",
                              '{}/sync_piwigo.sh'.format(self.wd),
                              self.photo_path],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def play(self):
        res_name = time.strftime("%Y%m%d-%H%M%S")+".jpg"
        self.photo_path = "{}/photos/{}".format(self.wd, res_name)
        self.toprint_path = "{}/toprint/{}".format(self.wd, res_name)
        self.show_smile()
        # capture 4 images
        for i in range(1, 5):
            self.countdown_from(self.countdown)
            img = "{}.jpg".format(i)
            self.show_smile('photo {} / 4 !'.format(i))
            self.capture_image(img)
            time.sleep(1)

        self.camera.stop_preview()
        self.show_smile("Un petit instant :D...", 40, 380, 50)
        # now merge all the images
        res_cmd = self.res_cmd + [self.toprint_path]
        self.to_print_p = subprocess.Popen(res_cmd,
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.STDOUT)
        self.showprint_path = self.photo_path
        subprocess.call(self.show_cmd + [self.showprint_path])
        # sync with cloud
        self.sync_withcloud()
        self.logger.info("Images have been merged.")

    def show_end(self):
        self.current_img = ImageTk.PhotoImage(self.imgs["end"])
        self.canvas.itemconfig(self.imagesprite,
                               image=self.current_img)
        self.root.update()
        self.logger.info("show end")

    def run(self):
        gogogo = True
        while gogogo:
            self.logger.info("new cycle")
            self.show_home()
            # wait for user to press green button
            button = self.user_input()
            while button != "green":
                button = self.user_input()
            self.logger.info("Start camera preview")
            self.camera.start_preview()
            self.add_preview_overlay(30, 10, 38, "Appuyez sur le bouton vert \n pour prendre 4 photos !", (34,139,34, 255))
            # wait for user to press green button
            button = self.user_input()
            while button != "green":
                button = self.user_input()
            self.play()
            self.stop_camera_preview()
            self.show_toprint()
            # green or red ?
            button = self.user_input()
            if button == "green":
                self.print_pic()
            else:
                self.logger.info("do not print the picture")
            self.show_end()
            # wait for user to press green button
            button = self.user_input()
            while button != "green":
                button = self.user_input()

    def teardown(self):
        self.logger.info("close everything")
        self.root.destroy()
        self.camera.close()


if __name__ == "__main__":
    logger = init_logger()
    booth = Booth(logger)
    try:
        booth.run()
    except BaseException:
        logging.error("Unhandled exception : " , exc_info=True)
    finally:
        logging.info("quitting...")
        booth.teardown()
