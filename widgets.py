import tkinter as tk
import tkinter.ttk as ttk
from tkinter.scrolledtext import ScrolledText
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.backend_bases import key_press_handler
from astropy.io import fits
import numpy as np

from multiscale import MultiScale 


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
        # header info panel
        self.header = ScrolledText(self, width=80, height=32)
        self.header.insert(tk.INSERT, insert_newlines(str(hdu.header)))
        self.header.config(state=tk.DISABLED)
        self.header.grid(row=0, column=1)
        # image view panel
        if self.cube:
            self.image = Image3D(self, self.hdu.data)
        else:
            self.image = Image2D(self, self.hdu.data)
        min_val, max_val = self.image.get_value_range()
        self.image.grid(row=0, column=0)
        # colour norm limit adjustment panel
        self.norm_scale = MultiScale(self, min_val=min_val, max_val=max_val, init_lis=[min_val, max_val])
        self.norm_scale.setValueChangeCallback(self.image.update_norm)
        self.image.update_norm((min_val, max_val))
        self.norm_scale.grid(row=1, columnspan=2)
        self.set_limit_button = tk.Button(self, text="Set to slice limits", command=self.image.reset_norm)
        self.set_limit_button.grid(row=2, column=0)




class Image(tk.Frame):
    def __init__(self, master, img_data, **kwargs):
        super().__init__(master, **kwargs)
        self.master = master
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

    def update_norm(self, norm_lims):
        norm = mpl.colors.Normalize(vmin=norm_lims[0], vmax=norm_lims[1])
        self.artist.set(norm=norm)
        self.canvas.draw()

    def reset_norm(self):
        self.update_norm(self.get_value_range())

    def get_value_range(self):
        return np.nanmin(self.img_data), np.nanmax(self.img_data)


class Image3D(Image):
    def __init__(self, master, img_data):
        super().__init__(master, img_data)
        self.wl_index = 0
        self.artist = self.ax.imshow(self.img_data[self.wl_index])
        self.fig.tight_layout()

    def change_wavelength(self, wl_index):
        self.wl_index = wl_index
        self.artist.set_data(self.img_data[wl_index])
        self.canvas.draw()

    def reset_norm(self):
        bounds = (np.nanmin(self.img_data[self.wl_index]), np.nanmax(self.img_data[self.wl_index]))
        self.master.norm_scale.setRange(*bounds)
        self.update_norm(bounds)


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