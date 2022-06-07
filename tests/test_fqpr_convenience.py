import os
import shutil
import unittest
import numpy as np
import tempfile

from HSTB.drivers import par3
from HSTB.kluster.fqpr_convenience import convert_multibeam, reload_data, process_multibeam, reprocess_sounding_selection, generate_new_surface


class TestFqprConvenience(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.testfile = os.path.join(os.path.dirname(__file__), 'resources', '0009_20170523_181119_FA2806.all')
        cls.expected_output = os.path.join(tempfile.tempdir, 'TestFqprConvenience')

        try:
            os.mkdir(cls.expected_output)
        except FileExistsError:
            shutil.rmtree(cls.expected_output)
            os.mkdir(cls.expected_output)

        assert os.path.exists(cls.testfile)

        cls.out = convert_multibeam(cls.testfile)
        cls.out = process_multibeam(cls.out, coord_system='NAD83')
        assert os.path.exists(cls.expected_output)
        cls.datapath = cls.out.multibeam.converted_pth

    @classmethod
    def tearDownClass(cls) -> None:
        cls.out.close()
        shutil.rmtree(cls.expected_output)
        resources_folder = os.path.join(os.path.dirname(__file__), 'resources')
        data_folders = [os.path.join(resources_folder, fldr) for fldr in os.listdir(resources_folder) if fldr[:9] == 'converted']
        [shutil.rmtree(fold) for fold in data_folders]

    def test_converted_data_content(self):
        out = reload_data(self.datapath)
        ad = par3.AllRead(self.testfile)
        ad.mapfile()

        # assert that they have the same number of pings
        assert out.multibeam.raw_ping[0].time.shape[0] == ad.map.getnum(78)

        # assert that there are the same number of attitude/navigation packets
        totatt = 0
        for i in range(ad.map.getnum(65)):
            rec = ad.getrecord(65, i)
            totatt += rec.data['Time'].shape[0]
        assert out.multibeam.raw_att.time.shape[0] == totatt

        ad.close()
        out.close()

    def test_return_all_profiles(self):
        pkeys, pcasts, pcasttimes, pcastlocs = self.out.multibeam.return_all_profiles()
        assert pkeys == ['profile_1495563079']
        assert pcasts == [[[0.0, 0.32, 0.5, 0.55, 0.61, 0.65, 0.67, 0.79, 0.88, 1.01, 1.04, 1.62, 2.0300000000000002,
                            2.43, 2.84, 3.25, 3.67,
                            4.45, 4.8500000000000005, 5.26, 6.09, 6.9, 7.71, 8.51, 8.91, 10.13, 11.8,
                            12.620000000000001, 16.79, 20.18, 23.93,
                            34.79, 51.15, 56.13, 60.67, 74.2, 12000.0],
                           [1489.2000732421875, 1489.2000732421875, 1488.7000732421875, 1488.300048828125,
                            1487.9000244140625, 1488.2000732421875,
                            1488.0, 1487.9000244140625, 1487.9000244140625, 1488.2000732421875, 1488.0999755859375,
                            1488.0999755859375, 1488.300048828125,
                            1488.9000244140625, 1488.5, 1487.7000732421875, 1487.2000732421875, 1486.800048828125,
                            1486.800048828125, 1486.5999755859375,
                            1485.7000732421875, 1485.0999755859375, 1484.800048828125, 1484.0, 1483.800048828125,
                            1483.7000732421875, 1483.0999755859375,
                            1482.9000244140625, 1482.9000244140625, 1481.9000244140625, 1481.300048828125,
                            1480.800048828125, 1480.800048828125, 1481.0,
                            1481.5, 1481.9000244140625, 1675.800048828125]]]
        assert pcasttimes == [1495563079]
        assert pcastlocs == [[47.78890945494799, -122.47711319986821]]

    def test_is_dual_head(self):
        assert not self.out.multibeam.is_dual_head()

    def test_return_tpu_parameters(self):
        params = self.out.multibeam.return_tpu_parameters('1495563079')
        assert params == {'tx_to_antenna_x': 0.0, 'tx_to_antenna_y': 0.0, 'tx_to_antenna_z': 0.0, 'heave_error': 0.05,
                          'roll_sensor_error': 0.001, 'pitch_sensor_error': 0.001, 'heading_sensor_error': 0.02,
                          'x_offset_error': 0.2,
                          'y_offset_error': 0.2, 'z_offset_error': 0.2, 'surface_sv_error': 0.5,
                          'roll_patch_error': 0.1, 'pitch_patch_error': 0.1,
                          'heading_patch_error': 0.5, 'latency_patch_error': 0.0, 'timing_latency_error': 0.001,
                          'separation_model_error': 0.0,
                          'waterline_error': 0.02, 'vessel_speed_error': 0.1, 'horizontal_positioning_error': 1.0,
                          'vertical_positioning_error': 0.5,
                          'tx_opening_angle': 1.0, 'rx_opening_angle': 1.3}

    def test_return_system_time_indexed_array(self):
        sysidx = self.out.multibeam.return_system_time_indexed_array()
        assert len(sysidx) == 1  # there is only one head for this sonar.
        tstmp_list = sysidx[0]
        assert len(tstmp_list) == 1  # there is only one installation parameter entry for this dataset
        parameters_list = tstmp_list[0]
        sonar_idxs = parameters_list[0]
        assert sonar_idxs.shape == self.out.multibeam.raw_ping[
            0].time.shape  # first element are the indices for the applicable data
        assert sonar_idxs.all()
        sonar_tstmp = parameters_list[1]
        assert sonar_tstmp == '1495563079'  # second element is the utc timestamp for the applicable installation parameters entry
        sonar_txrx = parameters_list[2]
        assert sonar_txrx == ['tx', 'rx']  # third element are the prefixes used to look up the installation parameters

        subset_start = float(self.out.multibeam.raw_ping[0].time[50])
        subset_end = float(self.out.multibeam.raw_ping[0].time[100])
        sysidx = self.out.multibeam.return_system_time_indexed_array(subset_time=[subset_start, subset_end])
        tstmp_list = sysidx[0]
        parameters_list = tstmp_list[0]
        sonar_idxs = parameters_list[0]
        assert np.count_nonzero(sonar_idxs) == 51

    def test_return_utm_zone_number(self):
        assert self.out.multibeam.return_utm_zone_number() == '10N'

    def test_return_total_pings(self):
        pc = self.out.return_total_pings(min_time=1495563100, max_time=1495563130)
        assert pc == 123
        pc = self.out.return_total_pings()
        assert pc == 216

    def test_reprocess_sounding_selection(self):
        fqpr_copy = self.out.copy()
        fqpr_copy.multibeam.xyzrph['rx_r']['1495563079'] = 10
        newout, soundings = reprocess_sounding_selection(fqpr_copy, return_soundings=True, georeference=True)
        # generate a tilt of 10 degrees on the receiver and see how the resulting soundings are altered
        x, y, z, heave_correct, alt_correct, vdatum_unc, geohash, proc_status = newout.intermediate_dat['40111']['georef']['1495563079'][0][0]
        assert newout.multibeam.xyzrph['rx_r']['1495563079'] == 10
        # original
        assert float(self.out.multibeam.raw_ping[0].isel(time=0).isel(beam=0).z.values) == 92.74199676513672
        assert float(self.out.multibeam.raw_ping[0].isel(time=0).isel(beam=399).z.values) == 73.44100189208984
        # new
        assert float(z[0][0]) == 53.2859992980957
        assert float(z[0][399]) == 111.13099670410156

    def test_generate_new_surface_empty(self):
        bs = generate_new_surface()
        assert bs.data is None
        assert bs.cell_count == {}
        assert bs.container == {}
        assert bs.coverage_area_square_meters == 0.0
        assert bs.coverage_area_square_nm == 0.0
        assert bs.epsg is None
        assert not bs.has_tiles
        assert bs.height is None
        assert bs.layer_names == []
        assert bs.is_empty

    def test_generate_new_sr_surface(self):
        bs = generate_new_surface(self.out)
        assert bs.data is None
        assert bs.cell_count == {8.0: 901}
        assert bs.container == {'converted__0009_20170523_181119_FA2806.all': ['0009_20170523_181119_FA2806.all']}
        assert bs.coverage_area_square_meters == 57664.0
        assert round(bs.coverage_area_square_nm, 6) == 0.016791
        assert bs.epsg == 6339
        assert bs.has_tiles
        assert bs.height == 2048.0
        assert bs.layer_names == ['depth', 'density', 'vertical_uncertainty', 'horizontal_uncertainty']
        assert bs.min_x == 538624.0
        assert bs.max_x == 539648.0
        assert bs.min_y == 5292032.0
        assert bs.min_y == 5292032.0
        assert int(bs.mean_depth) == 89
        assert bs.resolutions == [8.0]
        assert bs.number_of_tiles == 2
        assert not bs.is_empty
        assert bs.sub_type == 'srtile'

    def test_generate_new_vr_surface(self):
        bs = generate_new_surface(self.out, grid_type='variable_resolution_tile')
        assert bs.data is None
        assert bs.cell_count == {8.0: 901}
        assert bs.container == {'converted__0009_20170523_181119_FA2806.all': ['0009_20170523_181119_FA2806.all']}
        assert bs.coverage_area_square_meters == 57664.0
        assert round(bs.coverage_area_square_nm, 6) == 0.016791
        assert bs.epsg == 6339
        assert not bs.has_tiles
        assert bs.height == 2048.0
        assert bs.layer_names == ['depth', 'density', 'vertical_uncertainty', 'horizontal_uncertainty']
        assert bs.min_x == 538624.0
        assert bs.max_x == 539648.0
        assert bs.min_y == 5292032.0
        assert bs.min_y == 5292032.0
        assert int(bs.mean_depth) == 89
        assert bs.resolutions == [8.0]
        assert bs.number_of_tiles == 2
        assert not bs.is_empty
        assert bs.sub_type == 'grid'
