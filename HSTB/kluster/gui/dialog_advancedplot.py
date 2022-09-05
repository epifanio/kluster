from HSTB.kluster.gui.backends._qt import QtGui, QtCore, QtWidgets, Signal
import matplotlib.pyplot as plt
import numpy as np
import os
import logging

from HSTB.kluster.gui import common_widgets
from HSTB.kluster.modules import wobble, sat

from HSTB.shared import RegistryHelpers


class AdvancedPlotDialog(QtWidgets.QDialog):
    """
    Using the PlotDataHandler, allow the user to provide Kluster converted data and plot a variable across the whole
    time range or a subset of time (see PlotDataHandler for subsetting time)

    AdvancedPlot is where plots live that aren't generic inherit-from-xarray/matplotlib type plots.  All of those
    basic plots are in BasicPlot.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # fqpr = fully qualified ping record, the term for the datastore in kluster
        self.fqpr = None
        self.datasets = None
        self.variables = None
        self.recent_plot = None
        self.current_ping_count = 0

        self.wobble = None
        self.extinction = None
        self.period = None
        self.needs_rebuilding = False

        # self.plottypes = ['Wobble Test', 'Accuracy Test', 'Extinction Test', 'Data Density Test', 'Ping Period Test']
        self.plottypes = [
            "Wobble Test",
            "Accuracy Test",
            "Extinction Test",
            "Ping Period Test",
        ]
        self.modetypes = {
            "Wobble Test": [
                "Dashboard",
                "Allowable Percent Deviation",
                "Attitude Scaling One",
                "Attitude Scaling Two",
                "Attitude Latency",
                "Yaw Alignment",
                "X (Forward) Sonar Offset",
                "Y (Starboard) Sonar Offset",
                "Heave Sound Speed One",
                "Heave Sound Speed Two",
            ],
            "Accuracy Test": ["Use most prevalent mode and frequency"],
            "Extinction Test": [
                "Plot Extinction by Frequency",
                "Plot Extinction by Mode",
                "Plot Extinction by Sub Mode",
            ],
            "Data Density Test": ["By Frequency", "By Mode"],
            "Ping Period Test": [
                "Plot Period by Frequency",
                "Plot Period by Mode",
                "Plot Period by Sub Mode",
            ],
        }

        self.setWindowTitle("Advanced Plots")
        layout = QtWidgets.QVBoxLayout()

        self.data_widget = common_widgets.PlotDataHandler()

        self.hline = QtWidgets.QFrame()
        self.hline.setFrameShape(QtWidgets.QFrame.HLine)
        self.hline.setFrameShadow(QtWidgets.QFrame.Sunken)

        self.hlayout_main = QtWidgets.QHBoxLayout()
        self.vlayout_left = QtWidgets.QVBoxLayout()
        self.vlayout_right = QtWidgets.QVBoxLayout()

        self.hlayout_one = QtWidgets.QHBoxLayout()
        self.plot_type_label = QtWidgets.QLabel("Plot Type ", self)
        self.hlayout_one.addWidget(self.plot_type_label)
        self.plot_type_dropdown = QtWidgets.QComboBox(self)
        self.plot_type_dropdown.setSizeAdjustPolicy(
            QtWidgets.QComboBox.AdjustToContents
        )
        self.hlayout_one.addWidget(self.plot_type_dropdown)
        self.hlayout_one.addStretch()

        self.hlayout_two = QtWidgets.QHBoxLayout()
        self.mode_label = QtWidgets.QLabel("Mode       ", self)
        self.hlayout_two.addWidget(self.mode_label)
        self.mode_dropdown = QtWidgets.QComboBox(self)
        self.mode_dropdown.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.hlayout_two.addWidget(self.mode_dropdown)
        self.hlayout_two.addStretch()

        self.hlayout_extinction = QtWidgets.QHBoxLayout()
        self.roundedfreq = QtWidgets.QCheckBox("Round Frequency")
        self.roundedfreq.setChecked(True)
        self.roundedfreq.hide()
        self.hlayout_extinction.addWidget(self.roundedfreq)
        self.extinction_onlycomplete = QtWidgets.QCheckBox("Only Complete Swaths")
        self.extinction_onlycomplete.setChecked(True)
        self.extinction_onlycomplete.hide()
        self.hlayout_extinction.addWidget(self.extinction_onlycomplete)
        self.hlayout_extinction.addStretch()

        self.hlayout_extinction_two = QtWidgets.QHBoxLayout()
        self.extinction_pointsizelabel = QtWidgets.QLabel("Point Size (1-10): ")
        self.extinction_pointsizelabel.hide()
        self.hlayout_extinction_two.addWidget(self.extinction_pointsizelabel)
        self.extinction_pointsize = QtWidgets.QSpinBox()
        self.extinction_pointsize.setRange(1, 10)
        self.extinction_pointsize.setValue(3)
        self.extinction_pointsize.hide()
        self.hlayout_extinction_two.addWidget(self.extinction_pointsize)
        self.extinction_binsizelabel = QtWidgets.QLabel("Depth Bin Size (m): ")
        self.extinction_binsizelabel.hide()
        self.hlayout_extinction_two.addWidget(self.extinction_binsizelabel)
        self.extinction_binsize = QtWidgets.QDoubleSpinBox()
        self.extinction_binsize.setRange(0.1, 100.0)
        self.extinction_binsize.setSingleStep(1.0)
        self.extinction_binsize.setDecimals(1)
        self.extinction_binsize.setValue(1.0)
        self.extinction_binsize.hide()
        self.hlayout_extinction_two.addWidget(self.extinction_binsize)
        self.hlayout_extinction_two.addStretch()

        self.vlayout_accuracy = QtWidgets.QVBoxLayout()
        self.surface_label = QtWidgets.QLabel("Path to Kluster Surface:")
        self.surface_label.hide()
        self.hlayout_accone = QtWidgets.QHBoxLayout()
        self.surf_text = QtWidgets.QLineEdit("", self)
        self.surf_text.setReadOnly(True)
        self.surf_text.hide()
        self.hlayout_accone.addWidget(self.surf_text)
        self.surf_button = QtWidgets.QPushButton("Browse", self)
        self.surf_button.hide()
        self.hlayout_accone.addWidget(self.surf_button)
        self.vlayout_accuracy.addWidget(self.surface_label)
        self.vlayout_accuracy.addLayout(self.hlayout_accone)
        self.output_label = QtWidgets.QLabel("Output Folder for Plots:")
        self.output_label.hide()
        self.hlayout_acctwo = QtWidgets.QHBoxLayout()
        self.out_text = QtWidgets.QLineEdit("", self)
        self.out_text.setReadOnly(True)
        self.out_text.hide()
        self.hlayout_acctwo.addWidget(self.out_text)
        self.output_button = QtWidgets.QPushButton("Browse", self)
        self.output_button.hide()
        self.hlayout_acctwo.addWidget(self.output_button)
        self.show_accuracy = QtWidgets.QCheckBox("Show plots")
        self.show_accuracy.hide()
        self.vlayout_accuracy.addWidget(self.output_label)
        self.vlayout_accuracy.addLayout(self.hlayout_acctwo)
        self.vlayout_accuracy.addWidget(self.show_accuracy)
        self.vlayout_accuracy.addStretch()

        self.hlayout_four = QtWidgets.QHBoxLayout()
        self.hlayout_four.addStretch()
        self.plot_button = QtWidgets.QPushButton("Plot", self)
        self.plot_button.setDisabled(True)
        self.hlayout_four.addWidget(self.plot_button)
        self.hlayout_four.addStretch()

        self.hlayout_six = QtWidgets.QHBoxLayout()
        self.explanation = QtWidgets.QTextEdit("", self)
        self.hlayout_six.addWidget(self.explanation)

        layout.addWidget(self.data_widget)
        layout.addWidget(self.hline)

        self.vlayout_left.addLayout(self.hlayout_one)
        self.vlayout_left.addLayout(self.hlayout_two)
        self.vlayout_left.addStretch()
        self.vlayout_left.addLayout(self.hlayout_extinction)
        self.vlayout_left.addLayout(self.hlayout_extinction_two)
        self.vlayout_left.addLayout(self.vlayout_accuracy)
        self.vlayout_left.addStretch()

        self.vlayout_right.addLayout(self.hlayout_six)

        self.hlayout_main.addLayout(self.vlayout_left)
        self.hlayout_main.addLayout(self.vlayout_right)
        layout.addLayout(self.hlayout_main)

        layout.addLayout(self.hlayout_four)
        self.setLayout(layout)

        self.surf_button.clicked.connect(self.surf_browse)
        self.output_button.clicked.connect(self.output_browse)
        self.data_widget.fqpr_loaded.connect(self.new_fqpr_loaded)
        self.data_widget.ping_count_changed.connect(self.new_ping_count)
        self.plot_type_dropdown.currentTextChanged.connect(self.plottype_changed)
        self.mode_dropdown.currentTextChanged.connect(self.mode_changed)
        self.plot_button.clicked.connect(self.plot)
        self.roundedfreq.clicked.connect(self._clear_alldata)

    def print(self, msg: str, loglevel: int):
        if self.parent() is not None:
            self.parent().print(msg, loglevel)
        else:
            print(msg)

    def debug_print(self, msg: str, loglevel: int):
        if self.parent() is not None:
            self.parent().debug_print(msg, loglevel)
        else:
            print(msg)

    def surf_browse(self):
        msg, surf_path = RegistryHelpers.GetDirFromUserQT(
            self,
            RegistryKey="Kluster",
            Title="Select gridded data folder",
            AppName="\\reghelp",
        )
        if surf_path:
            if os.path.isdir(surf_path):
                self.surf_text.setText(surf_path)
            else:
                self.print(
                    "{} is not an existing directory".format(surf_path), logging.ERROR
                )

    def output_browse(self):
        msg, out_path = RegistryHelpers.GetDirFromUserQT(
            self,
            RegistryKey="Kluster",
            Title="Select folder to store plot images",
            AppName="\\reghelp",
        )
        if out_path:
            self.out_text.setText(out_path)

    def _clear_alldata(self):
        """
        Clear all the datasets stored for each test
        """

        self.extinction = None
        self.wobble = None
        self.period = None

    def new_fqpr_loaded(self, loaded: bool):
        """
        If a new fqpr is loaded (fqpr = converted Kluster data store) load the datasets

        Parameters
        ----------
        loaded
            if True, self.fqpr is valid
        """

        if loaded:
            self.fqpr = self.data_widget.fqpr
            self.load_datasets()
        else:
            self.fqpr = None
            self.datasets = {}
            self.plot_type_dropdown.clear()
            self.mode_dropdown.clear()
            self.plot_button.setDisabled(True)

    def load_datasets(self):
        """
        Build the lookup for the various kluster datasets and populate the dataset dropdown with the keys
        """
        if self.fqpr is not None:
            self.datasets = {}
            if self.fqpr.multibeam.raw_ping:
                self.datasets["multibeam"] = self.fqpr.multibeam.raw_ping
                self.datasets[
                    "raw navigation"
                ] = self.fqpr.multibeam.return_raw_navigation()
                procnav = self.fqpr.sbet_navigation
                if procnav is not None:
                    self.datasets["processed navigation"] = procnav

            if self.fqpr.multibeam.raw_att:
                self.datasets["attitude"] = self.fqpr.multibeam.raw_att

            self.plot_type_dropdown.clear()
            self.plot_type_dropdown.addItems(self.plottypes)
            self.plot_type_dropdown.setCurrentIndex(0)
            self._clear_alldata()

    def reload_datasets(self):
        """
        Triggered when self.fqpr is changed, we reload the datasets without the debug messaging just to keep it clean
        """

        if self.fqpr is not None:
            self.datasets = {}
            if self.fqpr.multibeam.raw_ping:
                self.datasets["multibeam"] = self.fqpr.multibeam.raw_ping
                self.datasets[
                    "raw navigation"
                ] = self.fqpr.multibeam.return_raw_navigation()
                procnav = self.fqpr.sbet_navigation
                if procnav is not None:
                    self.datasets["processed navigation"] = procnav
            if self.fqpr.multibeam.raw_att:
                self.datasets["attitude"] = self.fqpr.multibeam.raw_att

    def plottype_changed(self):
        """
        Triggered when changing the plottype dropdown
        """

        if self.datasets:
            self._clear_alldata()
            ky = self.plot_type_dropdown.currentText()
            if ky:
                modetypes = self.modetypes[ky]
                self.mode_dropdown.clear()
                self.mode_dropdown.addItems(modetypes)
                self.mode_dropdown.setCurrentIndex(0)
                data_is_there = False
                if ky == "Wobble Test":
                    data_is_there = np.all(
                        [
                            x in self.fqpr.multibeam.raw_ping[0]
                            for x in [
                                "depthoffset",
                                "corr_pointing_angle",
                                "corr_heave",
                                "corr_altitude",
                            ]
                        ]
                    )
                elif ky == "Accuracy Test":
                    data_is_there = np.all(
                        [
                            x in self.fqpr.multibeam.raw_ping[0]
                            for x in [
                                "x",
                                "y",
                                "z",
                                "corr_pointing_angle",
                                "mode",
                                "frequency",
                                "modetwo",
                            ]
                        ]
                    )
                elif ky == "Extinction Test":
                    data_is_there = np.all(
                        [
                            x in self.fqpr.multibeam.raw_ping[0]
                            for x in [
                                "acrosstrack",
                                "depthoffset",
                                "frequency",
                                "mode",
                                "modetwo",
                            ]
                        ]
                    )
                elif ky == "Ping Period Test":
                    data_is_there = np.all(
                        [
                            x in self.fqpr.multibeam.raw_ping[0]
                            for x in ["depthoffset", "frequency", "mode", "modetwo"]
                        ]
                    )

                if data_is_there:
                    self.plot_button.setEnabled(True)
                else:
                    self.data_widget.warning_message.setText(
                        "{}: Unable to find the necessary data to produce this plot"
                    )

    def mode_changed(self):
        """
        Triggered when changing the mode dropdown
        """

        if self.datasets:
            plottype = self.plot_type_dropdown.currentText()
            mode = self.mode_dropdown.currentText()
            if plottype in ["Extinction Test", "Ping Period Test"]:
                if mode in ["Plot Extinction by Frequency", "Plot Period by Frequency"]:
                    self.roundedfreq.show()
                else:
                    self.roundedfreq.hide()
                self.extinction_binsize.show()
                self.extinction_binsizelabel.show()
                if plottype == "Extinction Test":
                    self.extinction_onlycomplete.show()
                    self.extinction_pointsizelabel.show()
                    self.extinction_pointsize.show()
                else:
                    self.extinction_onlycomplete.hide()
                    self.extinction_pointsizelabel.hide()
                    self.extinction_pointsize.hide()
                self.surface_label.hide()
                self.surf_text.hide()
                self.surf_button.hide()
                self.output_label.hide()
                self.out_text.hide()
                self.output_button.hide()
                self.show_accuracy.hide()
            elif plottype == "Accuracy Test":
                self.extinction_binsize.hide()
                self.extinction_binsizelabel.hide()
                self.roundedfreq.hide()
                self.extinction_onlycomplete.hide()
                self.extinction_pointsizelabel.hide()
                self.extinction_pointsize.hide()
                self.surface_label.show()
                self.surf_text.show()
                self.surf_button.show()
                self.output_label.show()
                self.out_text.show()
                self.output_button.show()
                self.show_accuracy.show()
            else:
                self.extinction_binsize.hide()
                self.extinction_binsizelabel.hide()
                self.extinction_onlycomplete.hide()
                self.extinction_pointsizelabel.hide()
                self.extinction_pointsize.hide()
                self.roundedfreq.hide()
                self.surface_label.hide()
                self.surf_text.hide()
                self.surf_button.hide()
                self.output_label.hide()
                self.out_text.hide()
                self.show_accuracy.hide()
                self.output_button.hide()

        self.load_helptext()
        self.update_ping_warnings()

    def load_helptext(self):
        """
        Get the list of available plots for the provided variable/dataset
        """
        if self.datasets:
            plottype = self.plot_type_dropdown.currentText()
            mode = self.mode_dropdown.currentText()
            plottype_expl = ""
            mode_expl = ""

            if plottype == "Wobble Test":
                plottype_expl = "Implementation of 'Dynamic Motion Residuals in Swath Sonar Data: Ironing out the Creases' using Kluster processed"
                plottype_expl += " multibeam data.\nhttp://www.omg.unb.ca/omg/papers/Lect_26_paper_ihr03.pdf\n\nWobbleTest will generate the high"
                plottype_expl += " pass filtered mean depth and ping-wise slope, and build the correlation plots as described in the paper."
                plottype_expl += "\nRecommend the user start with 'Allowable Percent Deviation' to find the suitable time range."
                if mode == "Dashboard":
                    mode_expl = "Plot the full suite of plots.  See the allowable percent deviation to ensure that your dataset is flat enough for this to work."
                elif mode == "Allowable Percent Deviation":
                    mode_expl = "Plot the correlation plot between ping time and percent deviation in the ping slope linear regression.  Percent"
                    mode_expl += " deviation here is related to the standard error of the y in the regression.  Include bounds for invalid data"
                    mode_expl += " in the plot as a filled in red area.  According to source paper, greater than 5% should be rejected."
                elif mode == "Attitude Scaling One":
                    mode_expl = "Correlation between filtered ping slope and roll, should signify sensor scaling issues, really shouldn't be present with modern survey systems."
                    mode_expl += "\nIf scaling_one and scaling_two have your artifact, its probably a scaling issue. Otherwise, if the plots are different, it"
                    mode_expl += " is most likely sound speed.  Inner swath and outer swath will differ as the swath is curved"
                elif mode == "Attitude Scaling Two":
                    mode_expl = "Correlation between trimmed ping slope and roll, can signify possible surface sound speed issues.  When the soundspeed"
                    mode_expl += " at the face is incorrect, roll angles will introduce steering angle error, so your beampointingangle will be off."
                    mode_expl += "  As the roll changes, the error will change, making this a dynamic error that is correlated with roll."
                elif mode == "Attitude Latency":
                    mode_expl = "Plot to determine the attitude latency either in the attitude system initial processing or the transmission to the sonar."
                    mode_expl += " We use roll just because it is the most sensitive, most easy to notice.  It's a linear tilt we are looking for,"
                    mode_expl += " so the timing latency would be equal to the slope of the regression of roll rate vs ping slope."
                elif mode == "Yaw Alignment":
                    mode_expl = "Plot to determine the misalignment between roll/pitch and heading.  For us, the attitude/navigation system is a tightly "
                    mode_expl += "coupled system that provides these three data streams, so there really shouldn't be any yaw misalignment with roll/pitch."
                elif mode == "X (Forward) Sonar Offset":
                    mode_expl = "Plot to find the x lever arm error, which is determined by looking at the correlation between filtered depth"
                    mode_expl += " and pitch.  X lever arm error affects the induced heave by the following equation:\nInduced Heave Error = -x_error * sin(pitch)"
                elif mode == "Y (Starboard) Sonar Offset":
                    mode_expl = "Plot to find the y lever arm error, which is determined by looking at the correlation between filtered depth"
                    mode_expl += " and roll.  Y lever arm error affects the induced heave by the following equation:\nInduced Heave Error (y) = y_error * sin(roll) * cos(pitch)"
                elif mode == "Heave Sound Speed One":
                    mode_expl = "Plot to find error associated with heaving through sound speed layers.  For flat face sonar that are mostly"
                    mode_expl += " level while receiving, this affect should be minimal.  If I'm understanding this correctly, it's because the"
                    mode_expl += " system is actively steering the beams using the surface sv sensor.  For barrel arrays, there is no active"
                    mode_expl += (
                        " beam steering so there will be an error in the beam angles."
                    )
                elif mode == "Heave Sound Speed Two":
                    mode_expl = "See Heave Sound Speed One.  There are two plots for the port/starboard swaths.  You need two as the"
                    mode_expl += " swath artifact is a smile/frown, so the two plots should be mirror images if the artifact exists.  A full"
                    mode_expl += " swath analysis would not show this."
            elif plottype == "Extinction Test":
                plottype_expl = "Plot the outermost sound velocity corrected alongtrack/depth offsets to give a sense of the maximum swath"
                plottype_expl += " coverage versus depth.  Useful for operational planning where you can think to yourself, 'At 50 meters"
                plottype_expl += " depth, I can expect about 4 x 50 meters coverage (4x water depth)'"
                if mode == "Plot Extinction by Frequency":
                    mode_expl = "Group the plot by frequency, check the rounded frequency option to plot to the nearest kHz"
                elif mode == "Plot Extinction by Mode":
                    mode_expl = "Group the plot by primary mode, if you don't see the groupings you expect, try the sub mode option"
                elif mode == "Plot Extinction by Sub Mode":
                    mode_expl = "Group the plot by secondary mode, if you don't see the groupings you expect, try the mode option"
            elif plottype == "Ping Period Test":
                plottype_expl = "Plot the period of the pings binned by depth.  Illustrates the increase in ping period as depth increases."
                plottype_expl += " Gets some odd results with dual swath/dual head sonar.  We try to plot the rolling mean of the ping period"
                plottype_expl += " in these cases."
                if mode == "Plot Period by Frequency":
                    mode_expl = "Group the plot by frequency, check the rounded frequency option to plot to the nearest Hz"
                elif mode == "Plot Period by Mode":
                    mode_expl = "Group the plot by primary mode, if you don't see the groupings you expect, try the sub mode option"
                elif mode == "Plot Period by Sub Mode":
                    mode_expl = "Group the plot by secondary mode, if you don't see the groupings you expect, try the mode option"
            elif plottype == "Accuracy Test":
                plottype_expl = "Takes a surface (you must build the surface first) and accuracy test lines and creates"
                plottype_expl += " plots of depth difference between surface and lines for the soundings that are within grid cells."
                plottype_expl += "  Provides statistics of the bias between surface and soundings by beam and by angle for each mode and frequency combination."
                plottype_expl += "  Accuracy lines should be acquired on a flat seafloor and lines should be run with a variety of"
                plottype_expl += " frequency and mode settings.  The lines will automatically be organized into frequency and mode"
                plottype_expl += " categories.\n\n"
                plottype_expl += "The surface should only contain soundings from the accuracy test lines.  Using a grid that includes other multibeam"
                plottype_expl += " systems introduces additional error related to offsets, vertical control and other biases between multibeam systems.  Here"
                plottype_expl += " we try to isolate errors that scale with depth, such as sound speed, refraction, range measurements, etc."
                plottype_expl += "  For that reason, the Order 1 and Special Order lines only include the 'b' factor from the IHO TVU formula.\n\n"
                plottype_expl += "Order 1 line (grey) represents the 1.3% max allowable uncertainty wrt the depth range.\n"
                plottype_expl += "Special Order line (green) represents the 0.75% max allowable uncertainty wrt the depth range.\n"
                plottype_expl += "Mean depth line (blue) represents the mean depth for the beam/angle.\n"
                plottype_expl += (
                    "Pink region represents two standard deviations from the mean."
                )
                mode_expl = "Will use the most prevalent mode and frequency found for each line.\n"
                mode_expl += 'If "Show plots" is True, plots will be shown for you to edit, as well as saved to disk.\n'
                mode_expl += 'Path to Kluster Surface should be a grid folder created by Kluster that contains a "XXXX_Root".\n'
                mode_expl += "Output Folder for Plots is the folder that Kluster will save the accuracy test plots to.\n\n"
                mode_expl += 'Plots are saved with an encoded file name such as "CW-shCW-300000hz", which is equal to Mode-Modetwo-Frequency.\n\n'
                mode_expl += "Mode = (if TX Pulse Form) CW for continuous waveform, FM for frequency modulated, MIX for mix between FM and CW. (if Ping mode) VS for Very Shallow, SH for Shallow, ME for Medium, DE for Deep, VD for Very Deep, ED for Extra Deep\n\n"
                mode_expl += 'ModeTwo = (if Pulse Length) vsCW = very short continuous waveform, shCW = short cw, meCW = medium cw, loCW = long cw, vlCW = very long cw, elCW = extra long cw, shFM = short frequency modulated, loFM = long fm. (if Depth Mode) VS = Very Shallow, SH = Shallow, ME = Medium, DE = Deep, DR = Deeper, VD = Very Deep, ED = Extra deep, XD = Extreme Deep, if followed by "m" system is in manual mode\n\n'
                mode_expl += "Frequency = Rounded frequency for the line in Hertz"
            if plottype_expl and mode_expl:
                self.explanation.setText("{}\n\n{}".format(plottype_expl, mode_expl))
            else:
                self.explanation.setText("")

    def plot(self):
        """
        Build out the data that we plan to plot
        """
        if self.datasets:
            min_max = self.data_widget.return_trim_times()
            if min_max:
                err = self.fqpr.subset_by_time(min_max[0], min_max[1])
                if err:
                    self.data_widget.warning_message.setText(
                        "ERROR: no data in times {}-{}".format(min_max[0], min_max[1])
                    )
                    return
            self.reload_datasets()
            plottype = self.plot_type_dropdown.currentText()
            mode = self.mode_dropdown.currentText()

            if plottype == "Wobble Test":
                if self.needs_rebuilding or self.wobble is None:
                    self.wobble = wobble.WobbleTest(self.fqpr)
                    self.wobble.generate_starting_data()
                    self.needs_rebuilding = False
                if mode == "Dashboard":
                    self.wobble.plot_correlation_table()
                elif mode == "Allowable Percent Deviation":
                    self.wobble.plot_allowable_percent_deviation()
                elif mode == "Attitude Scaling One":
                    self.wobble.plot_attitude_scaling_one()
                elif mode == "Attitude Scaling Two":
                    self.wobble.plot_attitude_scaling_two()
                elif mode == "Attitude Latency":
                    self.wobble.plot_attitude_latency()
                elif mode == "Yaw Alignment":
                    self.wobble.plot_yaw_alignment()
                elif mode == "X (Forward) Sonar Offset":
                    self.wobble.plot_x_lever_arm_error()
                elif mode == "Y (Starboard) Sonar Offset":
                    self.wobble.plot_y_lever_arm_error()
                elif mode == "Heave Sound Speed One":
                    self.wobble.plot_heave_sound_speed_one()
                elif mode == "Heave Sound Speed Two":
                    self.wobble.plot_heave_sound_speed_two()
            elif plottype == "Extinction Test":
                try:
                    binsize = float(self.extinction_binsize.value())
                except:
                    self.data_widget.warning_message.setText(
                        "ERROR: Bin Size must be a number, found {}".format(
                            self.extinction_binsize.value()
                        )
                    )
                    return
                if self.needs_rebuilding or self.extinction is None:
                    self.extinction = sat.ExtinctionTest(
                        self.fqpr, round_frequency=self.roundedfreq.isChecked()
                    )
                    self.needs_rebuilding = False
                if mode == "Plot Extinction by Frequency":
                    self.extinction.plotv2(
                        mode="frequency",
                        depth_bin_size=binsize,
                        point_size=int(self.extinction_pointsize.text()),
                        filter_incomplete_swaths=self.extinction_onlycomplete.isChecked(),
                    )
                elif mode == "Plot Extinction by Mode":
                    self.extinction.plotv2(
                        mode="mode",
                        depth_bin_size=binsize,
                        point_size=int(self.extinction_pointsize.text()),
                        filter_incomplete_swaths=self.extinction_onlycomplete.isChecked(),
                    )
                elif mode == "Plot Extinction by Sub Mode":
                    self.extinction.plotv2(
                        mode="modetwo",
                        depth_bin_size=binsize,
                        point_size=int(self.extinction_pointsize.text()),
                        filter_incomplete_swaths=self.extinction_onlycomplete.isChecked(),
                    )
            elif plottype == "Ping Period Test":
                try:
                    binsize = float(self.extinction_binsize.value())
                except:
                    self.data_widget.warning_message.setText(
                        "ERROR: Bin Size must be a number, found {}".format(
                            self.extinction_binsize.value()
                        )
                    )
                    return
                if self.needs_rebuilding or self.period is None:
                    self.period = sat.PingPeriodTest(
                        self.fqpr, round_frequency=self.roundedfreq.isChecked()
                    )
                    self.needs_rebuilding = False
                if mode == "Plot Period by Frequency":
                    self.period.plot(mode="frequency", depth_bin_size=binsize)
                elif mode == "Plot Period by Mode":
                    self.period.plot(mode="mode", depth_bin_size=binsize)
                elif mode == "Plot Period by Sub Mode":
                    self.period.plot(mode="modetwo", depth_bin_size=binsize)
            elif plottype == "Accuracy Test":
                if mode == "Use most prevalent mode and frequency":
                    ping_times = (
                        np.min(
                            [rp.time.values[0] for rp in self.fqpr.multibeam.raw_ping]
                        ),
                        np.max(
                            [rp.time.values[-1] for rp in self.fqpr.multibeam.raw_ping]
                        ),
                    )
                    sat.accuracy_test(
                        self.surf_text.text(),
                        self.fqpr,
                        self.out_text.text(),
                        ping_times=ping_times,
                        show_plots=self.show_accuracy.isChecked(),
                    )
            if (
                min_max and plottype != "Accuracy Test"
            ):  # acc test restores the subset after it runs automatically
                self.fqpr.restore_subset()

        # set always on top
        plt.gcf().canvas.manager.window.setWindowFlags(
            self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint
        )
        plt.gcf().canvas.manager.window.show()

    def new_ping_count(self, ping_count: int):
        """
        We check some plottypes to ensure the number of pings provided makes sense

        Parameters
        ----------
        ping_count
            total number of pings that we plan on plotting
        """

        self.current_ping_count = ping_count
        if self.datasets:
            self.needs_rebuilding = True
            self.update_ping_warnings()

    def update_ping_warnings(self):
        """
        On changing the plot type or the current ping count, we update the warnings that are based on ping count for that plot
        """

        ping_count = self.current_ping_count
        if self.datasets:
            plottype = self.plot_type_dropdown.currentText()
            if plottype == "Wobble Test" and ping_count > 3000:
                self.data_widget.warning_message.setText(
                    "Warning: WobbleTest will be very slow with greater than 3000 pings"
                )
            elif plottype == "Wobble Test" and self.fqpr.multibeam.is_dual_head():
                self.data_widget.warning_message.setText(
                    "Warning: Dual Head - Each head will be treated as the port/starboard swath, provides some odd results"
                )
            else:
                self.data_widget.warning_message.setText("")


if __name__ == "__main__":
    try:  # pyside2
        app = QtWidgets.QApplication()
    except TypeError:  # pyqt5
        app = QtWidgets.QApplication([])
    dlog = AdvancedPlotDialog()
    dlog.show()
    app.exec_()
