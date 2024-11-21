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
    def __init__(self, master, hdu, wl, **kwargs):
        super().__init__(master, **kwargs)
        self.hdu = hdu
        self.wl = wl
        if wl is None:
            self.img = self.hdu.data
        else:
            self.img = self.hdu.data[wl]
        self.header = ScrolledText(self, width=80, height=32)
        self.header.insert(tk.INSERT, insert_newlines(str(hdu.header)))
        self.header.config(state=tk.DISABLED)
        self.image = Image(self, self.img)
        self.header.pack(side=tk.RIGHT)
        self.image.pack(side=tk.LEFT)


class Image(tk.Frame):
    def __init__(self, master, img_data, **kwargs):
        super().__init__(master, **kwargs)
        self.fig, self.ax = plt.subplots(1, 1)
        self.ax.set_axis_off()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()
        self.toolbar = NavigationToolbar2Tk(self.canvas, self)
        self.toolbar.update()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        self.update_img(img_data)

    def update_img(self, img_data, **imshow_kwargs):
        self.img_data = img_data
        i = self.ax.imshow(img_data, **imshow_kwargs)
        self.colorbar = plt.colorbar(i, ax=self.ax)
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