import tkinter as tk
import tkinter.ttk as ttk
import matplotlib.pyplot as plt
import matplotlib as mpl
from astropy.io import fits
import numpy as np

import widgets
from multiscale import MultiScale


class CubeView(tk.Frame):
    def __init__(self, master, filepath, **kwargs):
        super().__init__(master, **kwargs)

        # Load FITS file
        self.filepath = filepath
        self.notebook = ttk.Notebook(self)
        self.notebook.grid(row=0, column=0, columnspan=2)
        self.load_fits()

        # Create wavelength adjustment
        tk.Label(self, text="Wavelength").grid(row=1, column=0)
        wl_frame = tk.Frame(self)
        wl_frame.grid(row=2, column=0, columnspan=2)
        self.wl_slider = MultiScale(wl_frame, min_val=0, max_val=self.n_spec-1, step_size=1, init_lis=[0], show_value=False)
        self.wl_slider.setValueChangeCallback(self.update_wl)
        self.wl_label = tk.Label(wl_frame, text=f"{self.min_wl}um")
        self.wl_slider.grid(row=1, column=1, sticky="ew")
        tk.Label(wl_frame, text=f"{self.min_wl:.3f}um").grid(row=2, column=0)
        self.wl_label.grid(row=2, column=0, columnspan=3)
        tk.Label(wl_frame, text=f"{self.max_wl:.3f}um").grid(row=2, column=2)

    def load_fits(self):
        with fits.open(self.filepath) as hdul:
            self.min_wl = hdul[1].header["WAVSTART"] * 1e6
            self.max_wl = hdul[1].header["WAVEND"] * 1e6
            self.n_spec = hdul[1].header["NAXIS3"]
            self.wavelengths = np.linspace(self.min_wl, self.max_wl, self.n_spec)
            self.wl_res = self.wavelengths[1] - self.wavelengths[0]
            self.viewers = []
            self.cube_viewers = []
            for hdu, info in zip(hdul, hdul.info(output=False)):
                if info[3] == "ImageHDU":
                    viewer = widgets.FitsViewer(self, hdu)
                    if viewer.cube:
                        self.cube_viewers.append(viewer)
                    else:
                        self.viewers.append(viewer)
                    self.notebook.add(viewer, text=info[1])

    def update_wl(self, wl):
        wl = int(wl[0])
        self.wl_label.config(text=f"{round(self.wavelengths[wl], 5)}um")
        for viewer in self.cube_viewers:
            viewer.image.change_wavelength(wl)


def on_close():
    root.quit()
    root.destroy()

root = tk.Tk()
root.protocol("WM_DELETE_WINDOW", on_close)

cv = CubeView(root, R"\\uol.le.ac.uk\root\staff\home\s\scat2\Desktop Files\Level3_0B_g395h-f290lp_s3d_nav.fits")
cv.pack()
root.mainloop()