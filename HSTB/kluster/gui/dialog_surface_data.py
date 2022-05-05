import os

from HSTB.kluster.gui.backends._qt import QtGui, QtCore, QtWidgets, Signal

from HSTB.kluster.gui.common_widgets import TwoListWidget, SaveStateDialog
from HSTB.shared import RegistryHelpers
from HSTB.kluster import kluster_variables


class SurfaceDataDialog(SaveStateDialog):
    """
    Dialog for managing surface data, accessed when you right click on a surface and view the surface data.  You can
    add or remove days of multibeam data from this surface using this dialog, and optionally regrid the surface.
    """

    def __init__(self, parent=None, title='', settings=None):
        super().__init__(parent, settings, widgetname='surface_data')

        self.toplayout = QtWidgets.QVBoxLayout()
        self.setWindowTitle('Update Surface Data')

        self.listdata = TwoListWidget(title, 'In the Surface', 'Possible Containers')
        self.mark_for_update_button = QtWidgets.QPushButton('Mark Update')
        self.mark_for_update_button.setToolTip('Mark one of the "In the Surface" containers as needing to be re-added to the grid')
        self.mark_for_update_button.setDisabled(True)
        self.listdata.center_layout.addWidget(self.mark_for_update_button)
        self.listdata.center_layout.addStretch()
        self.toplayout.addWidget(self.listdata)

        self.update_checkbox = QtWidgets.QCheckBox('Update Existing Container Data')
        self.update_checkbox.setToolTip('Check this box to update all asterisk (*) marked containers in this surface for changes.\n' +
                                        'Updating means the container will be removed and then added back into the surface.  This must\n' +
                                        'be done for changes made in Kluster to take effect in the surface.')
        self.update_checkbox.setChecked(True)
        self.toplayout.addWidget(self.update_checkbox)

        self.regrid_layout = QtWidgets.QHBoxLayout()
        self.regrid_checkbox = QtWidgets.QCheckBox('Re-Grid Data')
        self.regrid_checkbox.setToolTip('Check this box to immediately grid all/updated containers after hitting OK')
        self.regrid_checkbox.setChecked(True)
        self.regrid_layout.addWidget(self.regrid_checkbox)
        self.regrid_options = QtWidgets.QComboBox()
        self.regrid_options.addItems(['The whole grid', 'Only where points have changed'])
        self.regrid_options.setToolTip('Controls what parts of the grid get re-gridded on running this tool\n\n' +
                                       'The whole grid - will regrid the whole grid, generally this is not needed\n' +
                                       'Only where points have changed - will only update the grid where containers have been removed or added')
        self.regrid_options.setCurrentText('Only where points have changed')
        self.regrid_layout.addWidget(self.regrid_options)
        self.regrid_layout.addStretch()
        self.toplayout.addLayout(self.regrid_layout)

        # self.use_dask_checkbox = QtWidgets.QCheckBox('Process in Parallel')
        # self.use_dask_checkbox.setToolTip('With this checked, gridding will be done in parallel using the Dask Client.  Assuming you have multiple\n' +
        #                                   'tiles, this should improve performance significantly.  You may experience some instability, although this\n' +
        #                                   'current implementation has not shown any during testing.')
        # self.toplayout.addWidget(self.use_dask_checkbox)

        self.status_msg = QtWidgets.QLabel('')
        self.status_msg.setStyleSheet("QLabel { color : " + kluster_variables.error_color + "; }")
        self.toplayout.addWidget(self.status_msg)

        self.hlayout_button = QtWidgets.QHBoxLayout()
        self.hlayout_button.addStretch(1)
        self.ok_button = QtWidgets.QPushButton('OK', self)
        self.hlayout_button.addWidget(self.ok_button)
        self.hlayout_button.addStretch(1)
        self.cancel_button = QtWidgets.QPushButton('Cancel', self)
        self.hlayout_button.addWidget(self.cancel_button)
        self.hlayout_button.addStretch(1)
        self.toplayout.addLayout(self.hlayout_button)

        self.setLayout(self.toplayout)

        self.original_current = []
        self.original_possible = []
        self.canceled = False

        self.mark_for_update_button.clicked.connect(self.mark_for_update)
        self.listdata.left_list.itemClicked.connect(self.enable_markbutton)
        self.listdata.right_list.itemClicked.connect(self.disable_markbutton)
        self.ok_button.clicked.connect(self.start_processing)
        self.cancel_button.clicked.connect(self.cancel_processing)

        self.text_controls = [['regrid_options', self.regrid_options]]
        self.checkbox_controls = [['update_checkbox', self.update_checkbox], ['regrid_checkbox', self.regrid_checkbox]]
        self.read_settings()

    def mark_for_update(self):
        curitem = self.listdata.left_list.selectedItems()[0]
        curitem_text = curitem.text()
        if curitem_text[-1] == '*':
            curitem.setText(curitem_text[:-1])
        else:
            curitem.setText(curitem_text + '*')

    def enable_markbutton(self):
        self.mark_for_update_button.setDisabled(False)

    def disable_markbutton(self):
        self.mark_for_update_button.setDisabled(True)

    def setup(self, current_containers: list, possible_containers: list):
        for cont in current_containers:
            self.listdata.add_left_list(cont)
        for cont in possible_containers:
            self.listdata.add_right_list(cont)
        self.original_current = current_containers
        self.original_possible = possible_containers

    def return_processing_options(self):
        current_containers = self.listdata.return_left_list_data()
        possible_containers = self.listdata.return_right_list_data()
        update_container = self.update_checkbox.isChecked()
        regrid_container = self.regrid_checkbox.isChecked()
        regrid_option = self.regrid_options.currentText()
        if regrid_option == 'The whole grid':
            regrid_option = 'full'
        elif regrid_option == 'Only where points have changed':
            regrid_option = 'update'
        else:
            raise ValueError("Expected regrid option to be one of ['The whole grid', 'Only where points have changed'], found {}".format(regrid_option))

        add_fqpr = []
        remove_fqpr = []
        if update_container:  # an update is simply a remove/add of a container
            needs_update = [cont[:-1] for cont in current_containers if cont[-1] == '*']
            for nu in needs_update:
                add_fqpr.append(nu)
                remove_fqpr.append(nu)
        for curr in self.original_current:
            if curr not in current_containers:
                if curr[-1] == '*':
                    curr = curr[:-1]
                if curr not in remove_fqpr:
                    remove_fqpr.append(curr)
        for newcurr in current_containers:
            if newcurr in self.original_possible and newcurr not in add_fqpr:
                add_fqpr.append(newcurr)
        return add_fqpr, remove_fqpr, {'regrid': regrid_container, 'use_dask': False,
                                       'regrid_option': regrid_option}

    def start_processing(self):
        if not self.listdata.return_left_list_data():
            self.status_msg.setText('Error: You must include at least one point source to continue')
        else:
            self.canceled = False
            self.save_settings()
            self.accept()

    def cancel_processing(self):
        self.canceled = True
        self.accept()


if __name__ == '__main__':
    try:  # pyside2
        app = QtWidgets.QApplication()
    except TypeError:  # pyqt5
        app = QtWidgets.QApplication([])
    dlog = SurfaceDataDialog()
    dlog.setup(['a', 'b', 'c*'], ['d', 'e', 'f'])
    dlog.show()
    if dlog.exec_():
        print(dlog.return_processing_options())