import tkinter as tk
import tkinter.ttk as ttk
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk

import math
import time
from PIL import Image, ImageTk


class ColourmapSlider(tk.Frame):
    def __init__(self, master, label, from_, to, on_change, on_reset, **kwargs):
        super().__init__(master, **kwargs)
        self.master = master
        self.grid_columnconfigure(3, weight=1)

        self.on_change = on_change

        self.from_label = tk.Label(self, text=from_)
        self.to_label = tk.Label(self, text=to)

        self.on_reset = on_reset
        self.reset_button = tk.Button(self, text="Reset", command=self._on_reset)

        self.increment_vmin_button = tk.Button(self, text=">", command=self._increment_vmin)
        self.decrement_vmin_button = tk.Button(self, text="<", command=self._decrement_vmin)
        self.increment_vmax_button = tk.Button(self, text=">", command=self._increment_vmax)
        self.decrement_vmax_button = tk.Button(self, text="<", command=self._decrement_vmax)

        self.vmin_var = tk.DoubleVar()
        self.vmin_var.set(from_)
        self.vmin_slider = tk.Scale(self, orient=tk.HORIZONTAL, showvalue=False, from_=from_, to_=to, variable=self.vmin_var)
        self.vmin_var.trace_add("write", self._on_slider_change)

        self.vmax_var = tk.DoubleVar()
        self.vmax_var.set(to)
        self.vmax_slider = tk.Scale(self, orient=tk.HORIZONTAL, showvalue=False, from_=from_, to_=to, variable=self.vmax_var)
        self.vmax_var.trace_add("write", self._on_slider_change)

        tk.Label(self, text=label).grid(row=0, column=0)
        self.reset_button.grid(row=1, column=0)

        self.from_label.grid(row=0, column=1, rowspan=2)
        self.to_label.grid(row=0, column=5, rowspan=2)
        
        self.decrement_vmin_button.grid(row=0, column=2)
        self.vmin_slider.grid(row=0, column=3, sticky="ew")
        self.increment_vmin_button.grid(row=0, column=4)

        self.decrement_vmax_button.grid(row=1, column=2)
        self.vmax_slider.grid(row=1, column=3, sticky="ew")
        self.increment_vmax_button.grid(row=1, column=4)
    
    def _increment_vmin(self):
        self.vmin_var.set(self.vmin_var.get() + 1)

    def _decrement_vmin(self):
        self.vmin_var.set(self.vmin_var.get() - 1)

    def _increment_vmax(self):
        self.vmax_var.set(self.vmax_var.get() + 1)

    def _decrement_vmax(self):
        self.vmax_var.set(self.vmax_var.get() - 1)

    def _on_slider_change(self, *_):
        vmin, vmax = self.get_vlims()
        self.from_label.config(text=vmin)
        self.to_label.config(text=vmax)
        self.on_change(vmin, vmax)

    def _on_reset(self):
        vmin, vmax = self.on_reset()
        self.set_vlims(vmin, vmax)

    def get_vlims(self):
        return self.vmin_var.get(), self.vmax_var.get()

    def set_vlims(self, vmin, vmax):
        for slider in [self.vmin_slider, self.vmax_slider]:
            old_from = slider.cget("from")
            old_to = slider.cget("to")
            if vmin < old_from:
                slider.config(from_=vmin)
            if vmax > old_to:
                slider.config(to=vmax)
        self.vmin_var.set(vmin)
        self.vmax_var.set(vmax)


class WavelengthSlider(tk.Frame):
    def __init__(self, master, label, wavelengths, from_, to, on_change, **kwargs):
        super().__init__(master, **kwargs)
        self.master = master
        self.grid_columnconfigure(3, weight=1)

        self.wavelengths = wavelengths
        self.on_change = on_change

        self.wavelength_label = tk.Label(self, text=f"{self.wavelengths[0]:.5f}")
        self.sliceindex_label = tk.Label(self, text="0", width=4)
        self.increment_button = tk.Button(self, text=">", command=self._increment)
        self.decrement_button = tk.Button(self, text="<", command=self._decrement)

        self.slider_var = tk.IntVar()
        self.slider_var.trace_add("write", self._on_slider_change)
        self.slider = tk.Scale(self, orient=tk.HORIZONTAL, showvalue=False, from_=from_, to_=to, variable=self.slider_var)
        
        tk.Label(self, text=label).grid(row=0, column=0, sticky="ew")
        self.wavelength_label.grid(row=0, column=1)
        self.decrement_button.grid(row=0, column=2)
        self.slider.grid(row=0, column=3, sticky="ew")
        self.increment_button.grid(row=0, column=4)
        self.sliceindex_label.grid(row=0, column=5)

        self.grid(row=2, column=0, sticky="ew")
    
    def _increment(self):
        self.slider_var.set(self.slider_var.get() + 1)

    def _decrement(self):
        self.slider_var.set(self.slider_var.get() - 1)

    def _on_slider_change(self, *_):
        value = self.slider_var.get()
        self.wavelength_label.config(text=f"{self.get_wavelength():.5f}")
        self.sliceindex_label.config(text=value)
        self.on_change(value)

    def get_index(self):
        return self.slider_var.get()

    def get_wavelength(self):
        return self.wavelengths[self.get_index()]
        

class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.window = tk.Toplevel()
        self.label = tk.Label(self.window, text=text, borderwidth=1, relief=tk.SOLID)
        self.label.pack()
        self.window.wm_overrideredirect(True)
        self.widget.bind("<Motion>", self.move)
        self.window.withdraw()
        self.hidden = True
        self.lastx = -1
        self.lasty = -1
        self.lasttime = time.time()

    @property
    def hidden(self):
        return self._hidden
    
    @hidden.setter
    def hidden(self, value):
        self._hidden = value
        if value:
            self.window.withdraw()
        else:
            self.window.deiconify()

    def calculate_tooltip_position(self, tip_delta=(10, 5), pad=(5, 3, 5, 3)):

            s_width, s_height = self.widget.winfo_screenwidth(), self.widget.winfo_screenheight()

            width, height = (pad[0] + self.label.winfo_reqwidth() + pad[2],
                             pad[1] + self.label.winfo_reqheight() + pad[3])

            mouse_x, mouse_y = self.widget.winfo_pointerxy()

            x1, y1 = mouse_x + tip_delta[0], mouse_y + tip_delta[1]
            x2, y2 = x1 + width, y1 + height

            x_delta = x2 - s_width
            if x_delta < 0:
                x_delta = 0
            y_delta = y2 - s_height
            if y_delta < 0:
                y_delta = 0

            offscreen = (x_delta, y_delta) != (0, 0)

            if offscreen:

                if x_delta:
                    x1 = mouse_x - tip_delta[0] - width

                if y_delta:
                    y1 = mouse_y - tip_delta[1] - height

            offscreen_again = y1 < 0  # out on the top

            if offscreen_again:
                # No further checks will be done.

                # TIP:
                # A further mod might automagically augment the
                # wraplength when the tooltip is too high to be
                # kept inside the screen.
                y1 = 0

            return x1, y1

    def move(self, event):
        self.widget.after(500, lambda e=event:self.check(e))

    def check(self, event):
        screen_x, screen_y = self.calculate_tooltip_position()
        self.window.geometry(f"+{screen_x}+{screen_y}")
        if self.lastx != screen_x or self.lasty != screen_y:
            self.lastx = screen_x
            self.lasty = screen_y
            self.hidden = True
        else:
            line_num = math.floor(float(self.widget.index(f"@{event.x},{event.y}")))
            text = self.widget.get(f"{line_num}.0", f"{line_num}.end").split(" / ")
            self.label.config(text=text)
            self.hidden = False


class MplToolbar(NavigationToolbar2Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tkims = []
        self._icon_size = self._find_icon_size()

    def _find_icon_size(self):
        for child in self.winfo_children():
            if isinstance(child, tk.Button):
                try:
                    img = child.cget("image")
                    if img:
                        tkimg = child.tk.globalgetvar(img)
                        return (tkimg.width(), tkimg.height())
                except:
                    continue
        return (22, 22) 

    def add_toggle_button(self, image, callback):
        im = Image.open(image)
        im.thumbnail(self._icon_size)
        self._tkims.append(ImageTk.PhotoImage(im))
        btn = FlatToggleButton(self, command=callback, imagepath=image, size=self._icon_size)
        btn.pack(side=tk.LEFT, padx=2)


class FlatToggleButton(tk.Frame):
    def __init__(self, master, command, text=None, imagepath=None, size=(22,22), **kwargs):
        super().__init__(master, borderwidth=1, relief=tk.FLAT, **kwargs)
        self.im = Image.open(imagepath)
        self.im.thumbnail(size)
        self.tkim = ImageTk.PhotoImage(self.im)
        self._state = False
        self.callback = command
        self.lbl = tk.Label(self, text=text, image=self.tkim)
        self.lbl.pack(expand=True, fill=tk.BOTH)
        self.lbl.bind("<Button-1>", lambda e: self.toggle())
        self.lbl.bind("<Enter>", lambda e: self.config(relief=tk.SUNKEN if not self._state else tk.FLAT))
        self.lbl.bind("<Leave>", lambda e: self.config(relief=tk.FLAT if not self._state else tk.SUNKEN))

    def toggle(self):
        self._state = not self._state
        self.config(relief=tk.SUNKEN if self._state else tk.FLAT)
        self.callback()