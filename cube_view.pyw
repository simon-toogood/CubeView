import tkinter as tk
import tkinter.ttk as ttk
from tkinter.filedialog import askopenfilename
from tkinter.scrolledtext import ScrolledText

from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure
import matplotlib as mpl
import matplotlib.pyplot as plt
from astropy.io import fits
import numpy as np
import sys
import re
import time
import math


class IterX:
    def __init__(self, iterable):
        self.iterable = list(iterable)
        self.i = 0

    def next(self):
        self.i += 1
        if self.i >= len(self.iterable):
            self.i = 0
        return self.iterable[self.i]
    __next__ = next

    def prev(self):
        self.i -= 1
        return self.iterable[self.i]

    def __call__(self):
        return self.iterable[self.i]


class CubeView(tk.Toplevel):
    def __init__(self, parent=None, filepath=None):
        super().__init__(parent)
        self.title("CubeView")

        self._create_menu()
        self.protocol("WM_DELETE_WINDOW", self._on_exit)
        self.bind("<<NotebookTabChanged>>", self._on_tab_change)

        if filepath is None:
            self._get_filepath()
        else:
            self.filepath = filepath
        
        self.title(f"CubeView: {self.filepath}")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill=tk.BOTH)
        self.after(0, self._load_fits)

    def _create_menu(self):
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open...", command=self._on_open)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_exit)
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        self.config(menu=menubar)

    def _on_new(self, *e):
        print("New clicked")

    def _on_open(self, *e):
        print("Opening new CubeView...")
        CubeView(self)

    def _get_filepath(self):
        label = tk.Label(self, text="Please select a FITS file to view")
        label.pack()
        self.filepath = askopenfilename(filetypes=[("FITS files", "*.fits *.fit")])
        if not self.filepath:
            self.destroy()
            return
        label.destroy()

    def _load_fits(self):
        self.hdul = fits.open(self.filepath)
        for hdu in self.hdul:
            if hdu.name == "SCI":
                self.wavelengths = generate_wavelengths_from_header(hdu.header)
            panel = ExtensionPanel(self.notebook, hdu)
            self.notebook.add(panel, text=hdu.name)

    def _on_exit(self):
        if hasattr(self, 'hdul'):
            self.hdul.close()
        self.destroy()

    def _on_tab_change(self, event):
        try:
            tab = self.notebook.nametowidget(self.notebook.select())
            tab.image_viewer._create_mpl_widgets()
        except Exception as e:
            print(e)



class ExtensionPanel(tk.Frame):
    def __init__(self, master, hdu, **kwargs):
        super().__init__(master, **kwargs)
        self.master = master
        self.hdu = hdu
        self.panes = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        self.panes.pack(fill=tk.BOTH, expand=True)

        self.header_viewer = HeaderViewer(self.panes, hdu)
        self.panes.add(self.header_viewer)

        if isinstance(hdu, fits.ImageHDU):
            self.image_viewer = ImageViewer(self.panes, hdu)
            self.panes.add(self.image_viewer)
        elif isinstance(hdu, fits.BinTableHDU) or isinstance(hdu, fits.TableHDU):
            pass
        elif isinstance(hdu, fits.PrimaryHDU):
            if hdu.data is not None:
                self.image_viewer = ImageViewer(self.panes, hdu)
                self.panes.add(self.image_viewer)            

class HeaderViewer(tk.Frame):
    def __init__(self, master, hdu, **kwargs):
        super().__init__(master, **kwargs)
        self.master = master
        self.hdu = hdu
        self.header = self._format_header(hdu.header)
        self.text = ScrolledText(self, width=80, height=32)
        self.text.insert(tk.INSERT, self.header)
        # self.tooltip = Tooltip(self.text, text="Hello world!")
        self.text.pack(fill=tk.BOTH, expand=True)

    def _format_header(self, header):
        header = str(header)
        x = re.sub("(.{80})", "\\1\n", header, 0, re.DOTALL)
        lines = x.split("\n")
        out = ""
        for l in lines:
            out += l.strip() + "\n"
        return out


class ImageViewer(tk.Frame):
    def __init__(self, master, hdu, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.master = master
        self.hdu = hdu
        self.data = hdu.data
        self.ndims = len(self.data.shape)
        self.loaded = False
        self.cmap_slider = ColourmapSlider(self, "Colourmap", from_=np.nanmin(self.data[0]), to=np.nanmax(self.data[0]), on_change=self.update_image_vlim, on_reset=self.reset_image_vlim)
        self.cmap_slider.grid(row=3, column=0, sticky="ew")
        self.is_wavelength_cube = False
        self.selected_spaxels = []
        self._scatter_artists = []
        self._plot_artists = []
        self._color_cycler = IterX(mpl.rcParams['axes.prop_cycle'].by_key()['color'])
        if self.ndims == 3:
            self.is_wavelength_cube = True
            self.wavelengths = self.master.master.master.master.wavelengths #horrid horrid horrid do not like
            self.wl_slider = WavelengthSlider(self, "Wavelength", wavelengths=self.wavelengths, from_=0, to=self.data.shape[0] - 1, on_change=self.update_image_slice)
            self.wl_slider.grid(row=2, column=0, sticky="ew")

    def _create_mpl_widgets(self):
        if self.loaded:
            return
                
        self.fig = Figure(figsize=(5, 4), dpi=100)
        if self.is_wavelength_cube:
            self.imax = self.fig.add_subplot(211)
            self.specax = self.fig.add_subplot(212)
            self.wl_rule = self.specax.axvline(x=self.wavelengths[0], c="r")
        else:
            self.imax = self.fig.add_subplot(111)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        self.canvas.mpl_connect("key_press_event", self._on_key_press)
        self.canvas.mpl_connect("motion_notify_event", self._on_mouse_move)
        self.canvas.mpl_connect("button_press_event", self._on_mouse_click)

        toolbar_frame = tk.Frame(self)
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()
        toolbar_frame.grid(row=1, column=0, sticky="nsew")

        self.imax.set_axis_off()
        self._plot_image_slice()
        if self.is_wavelength_cube:
            self._plot_spectrum()
        self.fig.tight_layout()

        self.loaded = True

    def _on_key_press(self, event):
        key_press_handler(event, self.canvas, self.toolbar)

    def _on_mouse_move(self, event):
        if event.inaxes == self.imax: 
            x, y = event.xdata, event.ydata 
            self.update_spectrum(x, y)
        else:
            self.spec.set_ydata(np.nanmean(self.data, axis=(1,2)))
            self.canvas.draw()

    def _on_mouse_click(self, event):
        if event.inaxes == self.imax:
            x, y = round(event.xdata), round(event.ydata)
            if (x,y) not in self.selected_spaxels:
                scatter_art = self.imax.scatter(x,y, c=self._color_cycler())
                plot_art = self.specax.plot(self.wavelengths, self.data[:, y,x], color=self._color_cycler(), lw=0.4)[0]
                self._scatter_artists.append(scatter_art)
                self._plot_artists.append(plot_art)
                self.selected_spaxels.append((x,y))
                self._create_toplevel_info(event, self._color_cycler())
                next(self._color_cycler)
            else:
                i = self.selected_spaxels.index((x,y))
                self._scatter_artists[i].remove()
                self._plot_artists[i].remove()
                del self._scatter_artists[i]
                del self._plot_artists[i]
                del self.selected_spaxels[i]
        self.canvas.draw_idle()

    def _create_toplevel_info(self, event, colour):
        top = tk.Toplevel(self)
        top.geometry(f"1x1+{event.guiEvent.x_root}+{event.guiEvent.y_root}")
        x, y = round(event.xdata), round(event.ydata)
        tk.Label(top, text=f"X={x}     Y={y}", bg=colour, fg=choose_text_color(colour)).grid(row=0, columnspan=2, sticky="nesw")

        i = 1
        for hdu in self.master.master.master.master.hdul:
            if isinstance(hdu, fits.ImageHDU) and len(hdu.data.shape) == 2:
                tk.Label(top, text=hdu.name).grid(row=i, column=0)
                tk.Label(top, text=hdu.data[y,x]).grid(row=i, column=1)
                i += 1

        top.update_idletasks()
        top.geometry("")

    def _plot_image_slice(self):
        if self.ndims == 3:
            self.im = self.imax.imshow(self.data[0], origin="lower")
        elif self.ndims == 2:
            self.im = self.imax.imshow(self.data, origin="lower")

    def _plot_spectrum(self):
        self.spec, = self.specax.plot(self.wavelengths, np.nanmean(self.data, axis=(1,2)), lw=0.5, c="k")
        ymin = np.nanpercentile(self.data, 0.1)
        if ymin < 1e0:
            ymin = 1e0
        ymax = np.nanpercentile(self.data, 99.9)
        if ymax > 1e10:
            ymax = 1e10
        self.specax.set_ylim(ymin, ymax)
        self.specax.set_yscale("log")
        
    def update_image_slice(self, value):
        new = self.data[value]
        self.im.set_data(new)
        self.wl_rule.set_xdata([self.wavelengths[value]])
        self.canvas.draw()

    def update_image_vlim(self, vmin, vmax):
        self.im.set_clim(vmin, vmax)
        self.canvas.draw()

    def reset_image_vlim(self):
        d = self.data[self.wl_slider.get_index()]
        vmin = np.nanmin(d)
        vmax = np.nanmax(d)
        self.update_image_vlim(vmin, vmax)
        return vmin, vmax

    def update_spectrum(self, x, y):
        d = self.data[:, int(round(y)), int(round(x))]
        self.spec.set_ydata(d)
        #self.specax.set_ylim(np.clip(np.nanmin(d), a_min=0.001, a_max=float("inf")), np.nanmax(d))
        self.canvas.draw()
        

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

    
def generate_wavelengths_from_header(
    header: fits.Header | dict,
    *,
    check_ctype: bool = True,
    axis: int = 3,) -> np.ndarray:
    """
    Generate wavelength array from keyword values in a FITS Header.

    This uses the NAXIS3, CRVAL3, CDELT3 (or CD3_3) and CRPIX3 keywords to generate the
    wavelength array described by the Header. The axis to generate wavelengths for can
    be customised using the `axis` parameter.

    By default, this function will raise an exception if the CTYPE of the axis is not
    'WAVE'. This can be disabled by setting `check_ctype` to False.

    See the
    `JWST documentation <https://jwst-docs.stsci.edu/jwst-calibration-status/miri-calibration-status/miri-mrs-calibration-status>`_
    for an an example of how the wavelength array can be generated from the FITS Header.

    Args:
        header: FITS Header object (or dictionary).
        check_ctype: Check that the CTYPE of the axis is 'WAVE'.
        axis: Axis to generate wavelengths for, using FITS (1-based) counting. This
            defaults to 3.

    Returns:
        Wavelength array.

    Raises:
        GetWavelengthsError: If the wavelength array cannot be generated from the
            FITS Header.
    """
    try:
        if check_ctype and header[f'CTYPE{axis}'] != 'WAVE':
            raise ValueError(
                f'Header item CTYPE{axis} = {header[f"CTYPE{axis}"]!r} (not \'WAVE\')'
            )

        naxis3 = int(header[f'NAXIS{axis}'])  # type: ignore
        crval3 = float(header[f'CRVAL{axis}'])  # type: ignore
        try:
            cdelt3 = float(header[f'CDELT{axis}'])  #  type: ignore
        except KeyError:
            cdelt3 = float(header[f'CD{axis}_{axis}'])  # type: ignore
        crpix3 = float(header.get(f'CRPIX{axis}', 1))  #  type: ignore
    except (KeyError, ValueError, TypeError) as e:
        raise ValueError(
            'Could not generate wavelength array from FITS Header'
        ) from e

    # https://jwst-docs.stsci.edu/jwst-calibration-status/miri-calibration-status/miri-mrs-calibration-status
    wavl = (np.arange(naxis3) + crpix3 - 1) * cdelt3 + crval3
    return wavl


def choose_text_color(bg_hex):
    """
    Given bg color as hex string (e.g. "#RRGGBB"), 
    return 'white' or 'black' depending on brightness.
    """
    bg_hex = bg_hex.lstrip('#')
    r, g, b = (int(bg_hex[i:i+2], 16) for i in (0, 2, 4))

    # Calculate luminance (perceived brightness)
    luminance = 0.299*r + 0.587*g + 0.114*b

    return 'black' if luminance > 186 else 'white'


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    CubeView(root)
    root.mainloop()
