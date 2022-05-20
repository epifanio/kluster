import unittest
import numpy as np
import pytest

from HSTB.kluster.modules.orientation import build_orientation_vectors
try:  # when running from pycharm console
    from kluster.tests.test_datasets import RealFqpr, load_dataset
    from kluster.tests.modules.module_test_arrays import expected_tx_vector, expected_rx_vector
except ImportError:  # relative import as tests directory can vary in location depending on how kluster is installed
    from ..test_datasets import RealFqpr, load_dataset
    from ..modules.module_test_arrays import expected_tx_vector, expected_rx_vector


class TestOrientation(unittest.TestCase):

    def test_orientation_module(self):
        dset = load_dataset(RealFqpr())
        raw_attitude = dset.raw_att
        # expand_dims required to maintain the time dimension metadata when you select only one value
        multibeam = dset.raw_ping[0].isel(time=0).expand_dims('time')
        traveltime = multibeam.traveltime
        delay = multibeam.delay
        timestamps = multibeam.time

        installation_params_time = list(dset.xyzrph['tx_r'].keys())[0]
        tx_orientation = [np.array([1, 0, 0]),  # starting vector for the tx transducer (points forward)
                          dset.xyzrph['tx_r'][installation_params_time],  # roll mounting angle for tx
                          dset.xyzrph['tx_p'][installation_params_time],  # pitch mounting angle for tx
                          dset.xyzrph['tx_h'][installation_params_time],  # yaw mounting angle for tx
                          installation_params_time]  # time stamp for the installation parameters record
        rx_orientation = [np.array([0, 1, 0]),  # same but for the receiver
                          dset.xyzrph['rx_r'][installation_params_time],
                          dset.xyzrph['rx_p'][installation_params_time],
                          dset.xyzrph['rx_h'][installation_params_time],
                          installation_params_time]
        latency = 0  # no latency applied for this test

        calc_tx_vector, calc_rx_vector = build_orientation_vectors(raw_attitude, traveltime, delay, timestamps,
                                                                   tx_orientation, rx_orientation, latency)

        try:
            assert np.array_equal(calc_tx_vector.values, expected_tx_vector)
        except AssertionError:
            print('Falling back to approx, should only be seen in TravisCI environment in my experience')
            # use approx here, I get ever so slightly different answers in the Travis CI environment
            assert calc_tx_vector.values == pytest.approx(expected_tx_vector, 0.000001)
        try:
            assert np.array_equal(calc_rx_vector.values, expected_rx_vector)
        except AssertionError:
            print('Falling back to approx, should only be seen in TravisCI environment in my experience')
            # use approx here, I get ever so slightly different answers in the Travis CI environment
            assert calc_rx_vector.values == pytest.approx(expected_rx_vector, 0.000001)

    def test_orientation_module_badtraveltime(self):
        dset = load_dataset(RealFqpr())
        raw_attitude = dset.raw_att
        # expand_dims required to maintain the time dimension metadata when you select only one value
        multibeam = dset.raw_ping[0].isel(time=0).expand_dims('time')
        traveltime = multibeam.traveltime
        delay = multibeam.delay
        timestamps = multibeam.time

        # set a bad traveltime, the test would be that the process completes successfully
        traveltime[0, 0] = -9999999.0

        installation_params_time = list(dset.xyzrph['tx_r'].keys())[0]
        tx_orientation = [np.array([1, 0, 0]),  # starting vector for the tx transducer (points forward)
                          dset.xyzrph['tx_r'][installation_params_time],  # roll mounting angle for tx
                          dset.xyzrph['tx_p'][installation_params_time],  # pitch mounting angle for tx
                          dset.xyzrph['tx_h'][installation_params_time],  # yaw mounting angle for tx
                          installation_params_time]  # time stamp for the installation parameters record
        rx_orientation = [np.array([0, 1, 0]),  # same but for the receiver
                          dset.xyzrph['rx_r'][installation_params_time],
                          dset.xyzrph['rx_p'][installation_params_time],
                          dset.xyzrph['rx_h'][installation_params_time],
                          installation_params_time]
        latency = 0  # no latency applied for this test

        calc_tx_vector, calc_rx_vector = build_orientation_vectors(raw_attitude, traveltime, delay, timestamps,
                                                                   tx_orientation, rx_orientation, latency)
        assert True
