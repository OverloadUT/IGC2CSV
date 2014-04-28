from nose.tools import raises
from nose.tools import assert_raises
import flightlog


def test_haversine():
    km = flightlog.haversine(100, 10, 180, 50)
    assert int(km) == 8438


def test_lat_to_degrees():
    # North is positive
    expected = 52 + 10.978/60
    assert flightlog.lat_to_degrees("5210978N") == expected
    # South is negative
    expected = (1 + 2.003/60) * -1
    assert flightlog.lat_to_degrees("0102003S") == expected


def test_lon_to_degrees():
    # East is positive
    expected = 0 + 6.639/60
    assert flightlog.lon_to_degrees("00006639E") == expected
    # West is negative
    expected = (120 + 59.999/60) * -1
    assert flightlog.lon_to_degrees("12059999W") == expected


class TestFlight():
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_fail(self):
        raise Exception("Unit tests not yet complete; results cannot be trusted")

    @raises(IOError)
    def test_init_file_does_not_exist(self):
        flightlog.Flight('a_file_that_does_not_exist.igc')

    def test_logline_a_valid(self):
        flight = flightlog.Flight()
        flight._parseline("A123ABCXYZ:1")
        assert flight.auxdata['flightrecorder'] == "123ABCXYZ:1"

    def test_logline_a_blank(self):
        flight = flightlog.Flight()
        flight._parseline("A")
        assert flight.auxdata['flightrecorder'] == ""

    def test_logline_h_flightdate(self):
        import datetime
        flight = flightlog.Flight()
        flight._parseline("HFDTE250809")
        assert flight.date == datetime.date(2009, 8, 25)

    def test_logline_h_glidertype(self):
        flight = flightlog.Flight()
        flight._parseline("HFGTYGLIDERTYPE:LS_8-18")
        assert flight.auxdata['glidertype'] == "LS_8-18"

    def test_logline_i_valid(self):
        flight = flightlog.Flight()
        flight._parseline("I023638FXA3941ENL")
        assert "FXA" in flight.optionalrecords
        assert flight.optionalrecords['FXA'] == (35, 38)
        assert "ENL" in flight.optionalrecords
        assert flight.optionalrecords['ENL'] == (38, 41)

    def test_logline_h_flightdate_invalid_date(self):
        flight = flightlog.Flight()
        # Month is 13
        assert_raises(flightlog.IGCError, flight._parseline, "HFDTE251309")
        # Day is 60
        assert_raises(flightlog.IGCError, flight._parseline, "HFDTE600809")
        # Not numbers
        assert_raises(flightlog.IGCError, flight._parseline, "HFDTEGARBAGE")
        # No year
        assert_raises(flightlog.IGCError, flight._parseline, "HFDTE2513")

    def test_init_simple_igc_file(self):
        import datetime
        flight = flightlog.Flight('test/sample_simple_igc_file.txt')
        assert flight.auxdata['flightrecorder'] == "LXNGIIFLIGHT:1"
        assert flight.date == datetime.date(2009, 8, 25)
        assert len(flight.fixrecords) == 1
        assert len(flight.optionalrecords) == 0

    def test_init_complex_igc_file(self):
        flight = flightlog.Flight('test/sample_complex_igc_file.txt')
        assert len(flight.fixrecords) == 1144
