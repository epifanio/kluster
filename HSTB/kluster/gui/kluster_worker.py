import numpy as np
import traceback

from HSTB.kluster.gui.backends._qt import QtGui, QtCore, QtWidgets, Signal
from HSTB.kluster.fqpr_project import return_project_data, reprocess_fqprs
from HSTB.kluster.fqpr_convenience import generate_new_surface, import_processed_navigation, overwrite_raw_navigation, \
    update_surface, reload_data, reload_surface


class ActionWorker(QtCore.QThread):
    """
    Executes code in a seperate thread.
    """

    started = Signal(bool)
    finished = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.action_container = None
        self.action_index = None
        self.result = None
        self.action_type = None
        self.error = False
        self.exceptiontxt = None

    def populate(self, action_container, action_index):
        self.action_container = action_container
        self.action_index = action_index
        self.result = None
        self.error = False
        self.exceptiontxt = None

    def run(self):
        self.started.emit(True)
        try:
            self.action_type = self.action_container.actions[self.action_index].action_type
            self.result = self.action_container.execute_action(self.action_index)
        except Exception as e:
            self.error = True
            self.exceptiontxt = traceback.format_exc()
        self.finished.emit(True)


class OpenProjectWorker(QtCore.QThread):
    """
    Thread that runs when the user drags in a new project file or opens a project using the menu
    """

    started = Signal(bool)
    finished = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.new_project_path = None
        self.force_add_fqprs = None
        self.force_add_surfaces = None
        self.new_fqprs = []
        self.new_surfaces = []
        self.error = False
        self.exceptiontxt = None

    def populate(self, new_project_path=None, force_add_fqprs=None, force_add_surfaces=None):
        self.new_project_path = new_project_path
        self.force_add_fqprs = force_add_fqprs
        self.force_add_surfaces = force_add_surfaces
        self.new_fqprs = []
        self.new_surfaces = []
        self.error = False
        self.exceptiontxt = None

    def run(self):
        self.started.emit(True)
        try:
            self.new_fqprs = []
            if self.new_project_path:
                data = return_project_data(self.new_project_path)
            else:
                data = {'fqpr_paths': [], 'surface_paths': []}
                if self.force_add_fqprs:
                    data['fqpr_paths'] = self.force_add_fqprs
                if self.force_add_surfaces:
                    data['surface_paths'] = self.force_add_surfaces
            for pth in data['fqpr_paths']:
                fqpr_entry = reload_data(pth, skip_dask=True, silent=True, show_progress=True)
                if fqpr_entry is not None:  # no fqpr instance successfully loaded
                    self.new_fqprs.append(fqpr_entry)
                else:
                    print('Unable to load converted data from {}'.format(pth))
            for pth in data['surface_paths']:
                surf_entry = reload_surface(pth)
                if surf_entry is not None:  # no grid instance successfully loaded
                    self.new_surfaces.append(surf_entry)
                else:
                    print('Unable to load surface from {}'.format(pth))
        except Exception as e:
            self.error = True
            self.exceptiontxt = traceback.format_exc()
        self.finished.emit(True)


class DrawNavigationWorker(QtCore.QThread):
    """
    On opening a project, you have to get the navigation for each line and draw it in the 2d view
    """

    started = Signal(bool)
    finished = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project = None
        self.new_fqprs = None
        self.line_data = {}
        self.error = False
        self.exceptiontxt = None

    def populate(self, project, new_fqprs):
        self.project = project
        self.new_fqprs = new_fqprs
        self.error = False
        self.exceptiontxt = None
        self.line_data = {}

    def run(self):
        self.started.emit(True)
        try:
            for fq in self.new_fqprs:
                print('building tracklines for {}...'.format(fq))
                for ln in self.project.return_project_lines(proj=fq, relative_path=True):
                    lats, lons = self.project.return_line_navigation(ln)
                    self.line_data[ln] = [lats, lons]
        except Exception as e:
            self.error = True
            self.exceptiontxt = traceback.format_exc()
        self.finished.emit(True)


class DrawSurfaceWorker(QtCore.QThread):
    """
    On opening a new surface, you have to get the surface tiles to display as in memory geotiffs in kluster_main
    """

    started = Signal(bool)
    finished = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.surface_path = None
        self.surf_object = None
        self.resolution = None
        self.surface_layer_name = None
        self.surface_data = {}
        self.error = False
        self.exceptiontxt = None

    def populate(self, surface_path, surf_object, resolution, surface_layer_name):
        self.surface_path = surface_path
        self.surf_object = surf_object
        self.resolution = resolution
        # handle optional hillshade layer
        self.surface_layer_name = surface_layer_name
        self.error = False
        self.exceptiontxt = None
        self.surface_data = {}

    def run(self):
        self.started.emit(True)
        try:
            if self.surface_layer_name == 'tiles':
                x, y = self.surf_object.get_tile_boundaries()
                self.surface_data = [x, y]
            else:
                if self.surface_layer_name == 'hillshade':
                    surface_layer_name = 'depth'
                else:
                    surface_layer_name = self.surface_layer_name
                for resolution in self.resolution:
                    self.surface_data[resolution] = {}
                    chunk_count = 1
                    for geo_transform, maxdim, data in self.surf_object.get_chunks_of_tiles(resolution=resolution, layer=surface_layer_name,
                                                                                            nodatavalue=np.float32(np.nan), z_positive_up=False,
                                                                                            for_gdal=True):
                        data = list(data.values())
                        self.surface_data[resolution][self.surface_layer_name + '_{}'.format(chunk_count)] = [data, geo_transform]
                        chunk_count += 1
        except Exception as e:
            self.error = True
            self.exceptiontxt = traceback.format_exc()
        self.finished.emit(True)


class LoadPointsWorker(QtCore.QThread):
    """
    Executes code in a seperate thread.
    """

    started = Signal(bool)
    finished = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.polygon = None
        self.azimuth = None
        self.project = None
        self.points_data = None
        self.error = False
        self.exceptiontxt = None

    def populate(self, polygon=None, azimuth=None, project=None):
        self.polygon = polygon
        self.azimuth = azimuth
        self.project = project
        self.points_data = None
        self.error = False
        self.exceptiontxt = None

    def run(self):
        self.started.emit(True)
        try:
            self.points_data = self.project.return_soundings_in_polygon(self.polygon)
        except Exception as e:
            self.error = True
            self.exceptiontxt = traceback.format_exc()
        self.finished.emit(True)


class ImportNavigationWorker(QtCore.QThread):
    """
    Executes code in a seperate thread.
    """

    started = Signal(bool)
    finished = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fq_chunks = None
        self.fqpr_instances = []
        self.error = False
        self.exceptiontxt = None

    def populate(self, fq_chunks):
        self.fq_chunks = fq_chunks
        self.fqpr_instances = []
        self.error = False
        self.exceptiontxt = None

    def run(self):
        self.started.emit(True)
        try:
            for chnk in self.fq_chunks:
                self.fqpr_instances.append(import_processed_navigation(chnk[0], **chnk[1]))
        except Exception as e:
            self.error = True
            self.exceptiontxt = traceback.format_exc()
        self.finished.emit(True)


class OverwriteNavigationWorker(QtCore.QThread):
    """
    Executes code in a seperate thread.
    """

    started = Signal(bool)
    finished = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fq_chunks = None
        self.fqpr_instances = []
        self.error = False
        self.exceptiontxt = None

    def populate(self, fq_chunks):
        self.fq_chunks = fq_chunks
        self.error = False
        self.exceptiontxt = None
        self.fqpr_instances = []

    def run(self):
        self.started.emit(True)
        try:
            for chnk in self.fq_chunks:
                self.fqpr_instances.append(overwrite_raw_navigation(chnk[0], **chnk[1]))
        except Exception as e:
            self.error = True
            self.exceptiontxt = traceback.format_exc()
        self.finished.emit(True)


class ExportWorker(QtCore.QThread):
    """
    Executes code in a seperate thread.
    """

    started = Signal(bool)
    finished = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fq_chunks = None
        self.line_names = None
        self.datablock = []
        self.fqpr_instances = []
        self.export_type = ''
        self.mode = ''
        self.z_pos_down = False
        self.delimiter = ' '
        self.filterset = False
        self.separateset = False
        self.error = False
        self.exceptiontxt = None

    def populate(self, fq_chunks, line_names, datablock, export_type, z_pos_down, delimiter, filterset, separateset, basic_mode, line_mode, points_mode):
        if basic_mode:
            self.mode = 'basic'
        elif line_mode:
            self.mode = 'line'
        elif points_mode:
            self.mode = 'points'

        self.fqpr_instances = []
        self.line_names = line_names
        self.datablock = datablock
        self.fq_chunks = fq_chunks
        self.export_type = export_type
        self.z_pos_down = z_pos_down
        if delimiter == 'comma':
            self.delimiter = ','
        elif delimiter == 'space':
            self.delimiter = ' '
        else:
            raise ValueError('ExportWorker: Expected either "comma" or "space", received {}'.format(delimiter))
        self.filterset = filterset
        self.separateset = separateset
        self.error = False
        self.exceptiontxt = None

    def export_process(self, fq, datablock=None):
        if self.mode == 'basic':
            fq.export_pings_to_file(file_format=self.export_type, csv_delimiter=self.delimiter, filter_by_detection=self.filterset,
                                    z_pos_down=self.z_pos_down, export_by_identifiers=self.separateset)
        elif self.mode == 'line':
            fq.export_lines_to_file(linenames=self.line_names, file_format=self.export_type, csv_delimiter=self.delimiter,
                                    filter_by_detection=self.filterset, z_pos_down=self.z_pos_down, export_by_identifiers=self.separateset)
        else:
            fq.export_soundings_to_file(datablock=datablock, file_format=self.export_type, csv_delimiter=self.delimiter,
                                        filter_by_detection=self.filterset, z_pos_down=self.z_pos_down)
        return fq

    def run(self):
        self.started.emit(True)
        try:
            if self.mode in ['basic', 'line']:
                for chnk in self.fq_chunks:
                    self.fqpr_instances.append(self.export_process(chnk[0]))
            else:
                fq = self.fq_chunks[0][0]
                self.fqpr_instances.append(self.export_process(fq, datablock=self.datablock))
        except Exception as e:
            self.error = True
            self.exceptiontxt = traceback.format_exc()
        self.finished.emit(True)


class FilterWorker(QtCore.QThread):
    """
    Executes code in a seperate thread.
    """

    started = Signal(bool)
    finished = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fq_chunks = None
        self.line_names = None
        self.fqpr_instances = []
        self.new_status = []
        self.mode = ''
        self.selected_index = None
        self.filter_name = ''

        self.args = None
        self.kwargs = None

        self.error = False
        self.exceptiontxt = None

    def populate(self, fq_chunks, line_names, filter_name, basic_mode, line_mode, points_mode, *args, **kwargs):
        if basic_mode:
            self.mode = 'basic'
        elif line_mode:
            self.mode = 'line'
        elif points_mode:
            self.mode = 'points'

        self.fqpr_instances = []
        self.new_status = []
        self.line_names = line_names
        self.fq_chunks = fq_chunks
        self.filter_name = filter_name

        self.args = args
        self.kwargs = kwargs

        self.error = False
        self.exceptiontxt = None

    def filter_process(self, fq, subset_time=None, subset_beam=None):
        if self.mode == 'basic':
            new_status = fq.run_filter(self.filter_name, None, *self.args, **self.kwargs)
        elif self.mode == 'line':
            fq.subset_by_lines(self.line_names)
            new_status = fq.run_filter(self.filter_name, None, *self.args, **self.kwargs)
            fq.restore_subset()
        else:
            # take the provided Points View time and subset the provided fqpr to just those times,beams
            selected_index = fq.subset_by_time_and_beam(subset_time, subset_beam)
            new_status = fq.run_filter(self.filter_name, selected_index, *self.args, **self.kwargs)
            fq.restore_subset()
        return fq, new_status

    def run(self):
        self.started.emit(True)
        try:
            if self.mode in ['basic', 'line']:
                for chnk in self.fq_chunks:
                    fq, new_status = self.filter_process(chnk[0])
                    self.fqpr_instances.append(fq)
                    self.new_status.append(new_status)
            else:
                for chnk in self.fq_chunks:
                    fq, subset_time, subset_beam = chnk
                    fq, new_status = self.filter_process(fq, subset_time, subset_beam)
                    self.fqpr_instances.append(fq)
                    self.new_status.append(new_status)
        except Exception as e:
            self.error = True
            self.exceptiontxt = traceback.format_exc()
        self.finished.emit(True)


class ExportTracklinesWorker(QtCore.QThread):
    """
    Executes code in a seperate thread.
    """

    started = Signal(bool)
    finished = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fq_chunks = None
        self.line_names = None
        self.fqpr_instances = []
        self.export_type = ''
        self.mode = ''
        self.output_path = ''
        self.error = False
        self.exceptiontxt = None

    def populate(self, fq_chunks, line_names, export_type, basic_mode, line_mode, output_path):
        if basic_mode:
            self.mode = 'basic'
        elif line_mode:
            self.mode = 'line'

        self.fqpr_instances = []
        self.line_names = line_names
        self.fq_chunks = fq_chunks
        self.export_type = export_type
        self.output_path = output_path
        self.error = False
        self.exceptiontxt = None

    def export_process(self, fq):
        if self.mode == 'basic':
            fq.export_tracklines_to_file(linenames=None, output_file=self.output_path, file_format=self.export_type)
        elif self.mode == 'line':
            fq.export_tracklines_to_file(linenames=self.line_names, output_file=self.output_path, file_format=self.export_type)
        return fq

    def run(self):
        self.started.emit(True)
        try:
            for chnk in self.fq_chunks:
                self.fqpr_instances.append(self.export_process(chnk[0]))
        except Exception as e:
            self.error = True
            self.exceptiontxt = traceback.format_exc()
        self.finished.emit(True)


class ExportGridWorker(QtCore.QThread):
    """
    Executes code in a seperate thread.
    """

    started = Signal(bool)
    finished = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.surf_instance = None
        self.export_type = ''
        self.output_path = ''
        self.z_pos_up = True
        self.bag_kwargs = {}
        self.error = False
        self.exceptiontxt = None

    def populate(self, surf_instance, export_type, output_path, z_pos_up, bag_kwargs):
        self.surf_instance = surf_instance
        self.export_type = export_type
        self.output_path = output_path
        self.bag_kwargs = bag_kwargs
        self.z_pos_up = z_pos_up
        self.error = False
        self.exceptiontxt = None

    def run(self):
        self.started.emit(True)
        try:
            # None in the 4th arg to indicate you want to export all resolutions
            self.surf_instance.export(self.output_path, self.export_type, self.z_pos_up, None, **self.bag_kwargs)
        except Exception as e:
            self.error = True
            self.exceptiontxt = traceback.format_exc()
        self.finished.emit(True)


class SurfaceWorker(QtCore.QThread):
    """
    Executes code in a seperate thread.
    """

    started = Signal(bool)
    finished = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fqpr_instances = None
        self.fqpr_surface = None
        self.opts = {}
        self.error = False
        self.exceptiontxt = None

    def populate(self, fqpr_instances, opts):
        self.fqpr_instances = fqpr_instances
        self.fqpr_surface = None
        self.opts = opts
        self.error = False
        self.exceptiontxt = None

    def run(self):
        self.started.emit(True)
        try:
            self.fqpr_surface = generate_new_surface(self.fqpr_instances, **self.opts)
        except Exception as e:
            self.error = True
            self.exceptiontxt = traceback.format_exc()
        self.finished.emit(True)


class SurfaceUpdateWorker(QtCore.QThread):
    """
    Executes code in a seperate thread.
    """

    started = Signal(bool)
    finished = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fqpr_surface = None
        self.add_fqpr_instances = None
        self.remove_fqpr_instances = None
        self.opts = {}
        self.error = False
        self.exceptiontxt = None

    def populate(self, fqpr_surface, add_fqpr_instances, remove_fqpr_instances, opts):
        self.fqpr_surface = fqpr_surface
        self.add_fqpr_instances = add_fqpr_instances
        self.remove_fqpr_instances = remove_fqpr_instances
        self.opts = opts
        self.error = False
        self.exceptiontxt = None

    def run(self):
        self.started.emit(True)
        try:
            self.fqpr_surface = update_surface(self.fqpr_surface, self.add_fqpr_instances, self.remove_fqpr_instances,
                                               **self.opts)
        except Exception as e:
            self.error = True
            self.exceptiontxt = traceback.format_exc()
        self.finished.emit(True)


class PatchTestUpdateWorker(QtCore.QThread):
    """
    Executes code in a seperate thread.
    """

    started = Signal(bool)
    finished = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fqprs = None
        self.newvalues = []
        self.headindex = None
        self.prefixes = None
        self.timestamps = None
        self.serial_number = None
        self.polygon = None

        self.result = []
        self.error = False
        self.exceptiontxt = None

    def populate(self, fqprs=None, newvalues=None, headindex=None, prefixes=None, timestamps=None, serial_number=None,
                 polygon=None):
        self.fqprs = fqprs
        self.newvalues = newvalues
        self.headindex = headindex
        self.prefixes = prefixes
        self.timestamps = timestamps
        self.serial_number = serial_number
        self.polygon = polygon

        self.result = []
        self.error = False
        self.exceptiontxt = None

    def run(self):
        self.started.emit(True)
        try:
            self.result = reprocess_fqprs(self.fqprs, self.newvalues, self.headindex, self.prefixes, self.timestamps,
                                          self.serial_number, self.polygon)
        except Exception as e:
            self.error = True
            self.exceptiontxt = traceback.format_exc()
        self.finished.emit(True)
