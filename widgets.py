import tkinter as tk
import tkinter.ttk as ttk
from tkinter.scrolledtext import ScrolledText
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.backend_bases import key_press_handler
from astropy.io import fits


def insert_newlines(string, every=80):
    lines = []
    for i in range(0, len(string), every):
        lines.append(string[i:i+every])
    return '\n'.join(lines)


class FitsViewer(tk.Frame):
    def __init__(self, master, hdu, **kwargs):
        super().__init__(master, **kwargs)
        self.hdu = hdu
        self.cube = True if hdu.header["NAXIS"] == 3 else False
        self.header = ScrolledText(self, width=80, height=32)
        self.header.insert(tk.INSERT, insert_newlines(str(hdu.header)))
        self.header.config(state=tk.DISABLED)
        self.header.pack(side=tk.RIGHT)
        if self.cube:
            self.image = Image3D(self, self.hdu.data)
        else:
            self.image = Image2D(self, self.hdu.data)
        self.image.pack(side=tk.LEFT)


class Image(tk.Frame):
    def __init__(self, master, img_data, **kwargs):
        super().__init__(master, **kwargs)
        self.img_data = img_data
        self.fig, self.ax = plt.subplots(1, 1)
        self.ax.set_axis_off()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()
        self.toolbar = NavigationToolbar2Tk(self.canvas, self)
        self.toolbar.update()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    def add_colorbar(self):
        plt.colorbar(self.artist, ax=self.ax)


class Image3D(Image):
    def __init__(self, master, img_data):
        super().__init__(master, img_data)
        self.artist = self.ax.imshow(self.img_data[0])
        self.fig.tight_layout()

    def change_wavelength(self, wl):
        self.artist.set_data(self.img_data[wl])
        self.canvas.draw()

class Image2D(Image):
    def __init__(self, master, img_data):
        super().__init__(master, img_data)
        self.artist = self.ax.imshow(img_data)
        self.fig.tight_layout()

class Plot(tk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.fig, self.ax = plt.subplots(1, 1)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()
        self.toolbar = NavigationToolbar2Tk(self.canvas, self)
        self.toolbar.update()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    def update_data(self, x_data, y_data, **plot_kwargs):
        self.x_data = x_data
        self.y_data = y_data
        self.ax.plot(x_data, y_data, **plot_kwargs)
        self.fig.tight_layout()