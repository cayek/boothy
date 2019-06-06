import tkinter as tk
from PIL import ImageTk, Image

# full screen
root = tk.Tk()
root.overrideredirect(True)
w, h = (800, 480)
# root.geometry("{0}x{1}+0+0".format(root.winfo_screenwidth(), root.winfo_screenheight()))
root.geometry("{0}x{1}+0+0".format(w, h))
root.focus_set()  # <-- move focus to this widget
root.bind("<Escape>", lambda e: e.widget.quit())

# add picture
img = Image.open("./boothy0.png")
canvas = tk.Canvas(root,width=w,height=h)
canvas.pack()
canvas.configure(background='black')
imgtk = ImageTk.PhotoImage(img)
imagesprite = canvas.create_image(w/2,h/2,image=imgtk)
root.update()
root.update_idletasks()

# add an other picture
canvas2 = tk.Canvas(root,width=w,height=h)
img2 = Image.open("./boothy1.png")
imgtk2 = ImageTk.PhotoImage(img2)
canvas.itemconfig(imagesprite, image = imgtk2)
root.update()
root.update_idletasks()

# switch again
canvas.itemconfig(imagesprite, image = imgtk)
root.update()
root.update_idletasks()

# add camera
import picamera
camera = picamera.PiCamera()
camera.resolution = (640, 480)
camera.start_preview()

camera.stop_preview()
