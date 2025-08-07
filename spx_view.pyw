import tkinter as tk
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure
import numpy as np
from tkinter import ttk
import tkinter.filedialog as tkdialog
import itertools as it
import matplotlib.pyplot as plt
from eleos import parsers


class SpxViewer(tk.Tk):
    def __init__(self):
        super().__init__()

        self.filepaths = []

        self.title(".spx Viewer")
        self.geometry("1200x600")
        self.protocol("WM_DELETE_WINDOW", self._quit)

        self.fig = Figure(figsize=(5, 4), dpi=100, constrained_layout=True)
        self.ax = self.fig.add_subplot(111)
        self.colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
        self.reset_color_cycler()
        self._create_canvas_and_toolbar()
        self._create_widgets()
        self._refresh_enablers()
        self.refresh_plot()

    def _create_canvas_and_toolbar(self):
        self.mpl_frame = tk.Frame(self)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.mpl_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        self.toolbar = NavigationToolbar2Tk(self.canvas, self.mpl_frame)
        self.toolbar.update()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        self.canvas.mpl_connect("key_press_event", self._on_key_press)

    def _create_widgets(self):
        self.enabler_frame = tk.Frame(self)
        self.add_button = tk.Button(self, text="Add spectrum", command=self.add_file)
        self.add_button.pack()
        self.reset_lim_button = tk.Button(self, text="See all", command=self.set_lims)
        self.reset_lim_button.pack()
        self.enabler_frame.pack()
        self.mpl_frame.pack(expand=True, fill=tk.BOTH)

    def _refresh_enablers(self):
        self.checkbox_states = [tk.BooleanVar(value=True) for fp in self.filepaths]
        self.checkboxes = [tk.Checkbutton(self.enabler_frame, command=self.refresh_plot, variable=v) for v in self.checkbox_states]
        self.labels = [tk.Label(self.enabler_frame, text=fp) for fp in self.filepaths]

        for i in range(len(self.filepaths)):
            self.checkboxes[i].grid(row=i, column=0)
            self.labels[i].grid(row=i, column=1)

    def _on_key_press(self, event):
        print(f"You pressed {event.key}")
        key_press_handler(event, self.canvas, self.toolbar)

    def _quit(self):
        self.quit()
        self.destroy()

    def set_lims(self):
        self.ax.relim()
        self.ax.autoscale()
        self.canvas.draw()

    def reset_color_cycler(self):
        self.color_cycler = it.cycle(self.colors)

    def add_file(self):
        fps = tkdialog.askopenfilenames(filetypes=[(".spx files", "*.spx")])
        self.filepaths += fps
        self._refresh_enablers()
        self.refresh_plot()

    def refresh_plot(self):
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        self.ax.clear()
        for i, fp in enumerate(self.filepaths):
            c = next(self.color_cycler)
            if self.checkbox_states[i].get():
                spx = parsers.NemesisSpx(fp)
                self.ax.plot(spx.wavelengths, spx.spectrum, label=fp, c=c, lw=0.5)
                self.ax.fill_between(spx.wavelengths, spx.spectrum - spx.errors, spx.spectrum + spx.errors, alpha=0.5, color=c)
        self.ax.legend()
        self.ax.set_yscale("log")
        self.ax.set_xlabel("Wavelength (microns)")
        self.ax.set_ylabel("Radiance (W/cm2/sr/um)")
        self.ax.set_xlim(*xlim)
        self.ax.set_ylim(*ylim)
        self.canvas.draw()
        self.reset_color_cycler()

if __name__ == "__main__":
    app = SpxViewer()
    app.mainloop()
