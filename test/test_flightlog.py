from nose.tools import raises
from nose.tools import assert_raises
import flightlog


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
        assert flight.manufacturer == "123ABCXYZ:1"

    def test_logline_a_blank(self):
        flight = flightlog.Flight()
        flight._parseline("A")
        assert flight.manufacturer == ""

    def test_logline_h_flightdate(self):
        import datetime
        flight = flightlog.Flight()
        flight._parseline("HFDTE250809")
        assert flight.flightdate == datetime.date(2009, 8, 25)

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
        assert flight.manufacturer == "LXNGIIFLIGHT:1"
        assert flight.flightdate == datetime.date(2009, 8, 25)
        assert len(flight.fixrecords) == 1
        assert len(flight.optionalrecords) == 0