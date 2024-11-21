import tkinter as tk
import tkinter.ttk as ttk
import matplotlib.pyplot as plt
from astropy.io import fits

import widgets


class CubeView(tk.Frame):
    def __init__(self, master, filepath, **kwargs):
        super().__init__(master, **kwargs)
        self.filepath = filepath
        self.notebook = ttk.Notebook(self)
        self.notebook.pack()
        self.load_fits()

    def load_fits(self):
        with fits.open(self.filepath) as hdul:
            for hdu, info in zip(hdul, hdul.info(output=False)):
                if info[3] == "ImageHDU":
                    if len(info[5]) == 3:
                        wl = 100
                    elif len(info[5]) == 2:
                        wl = None
                    viewer = widgets.FitsViewer(self, hdu, wl=wl)
                    self.notebook.add(viewer, text=info[1])



root = tk.Tk()
cv = CubeView(root, R"\\uol.le.ac.uk\root\ALICE\data\nemesis\jwst\NIRSPEC_IFU\2022-12-24_JupSPole\2022-07-01_reduction\obs68S\stage4_despike\combined\Level3_0B_g395h-f290lp_s3d_nav.fits")
cv.pack()
root.mainloop()