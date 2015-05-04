from nose.tools import raises
from nose.tools import assert_raises
import flightlog


def test_haversine():
    """Calculate distance using haversine formula"""
    fix1 = flightlog.FixRecord(
        {'latitude': 100, 'longitude': 100})
    fix2 = flightlog.FixRecord(
        {'latitude': 0, 'longitude': 0})
    km = flightlog.haversine(fix1, fix2)
    assert int(km) == 9809


def test_haversine_zero():
    """Use haversine for zero distance traveled"""
    fix1 = flightlog.FixRecord(
        {'latitude': 100, 'longitude': 100})
    fix2 = flightlog.FixRecord(
        {'latitude': 100, 'longitude': 100})
    km = flightlog.haversine(fix1, fix2)
    assert int(km) == 0


def test_lat_to_degrees():
    """Convert IGC-spec latitude string to decimal degrees"""
    # North is positive
    expected = 52 + 10.978/60
    assert flightlog.lat_to_degrees("5210978N") == expected
    # South is negative
    expected = (1 + 2.003/60) * -1
    assert flightlog.lat_to_degrees("0102003S") == expected


def test_lon_to_degrees():
    """Convert IGC-spec longitude string to decimal degrees"""
    # East is positive
    expected = 0 + 6.639/60
    assert flightlog.lon_to_degrees("00006639E") == expected
    # West is negative
    expected = (120 + 59.999/60) * -1
    assert flightlog.lon_to_degrees("12059999W") == expected


def test_abs_distance():
    """Calculate 3-dimensional distance traveled"""
    fix1 = flightlog.FixRecord(
        {'latitude': 0, 'longitude': 0, 'alt_gps': 0})
    fix2 = flightlog.FixRecord(
        {'latitude': 0, 'longitude': 0, 'alt_gps': 10000})
    fix3 = flightlog.FixRecord(
        {'latitude': 1, 'longitude': 1, 'alt_gps': 100000})

    assert flightlog.abs_distance(fix1, fix2) == 10
    assert flightlog.abs_distance(fix1, fix1) == 0
    assert int(flightlog.abs_distance(fix1, fix3)) == 186


def test_todo_true_airspeed(self):
    raise NotImplementedError(
        "Need to handle computations for true airspeed (tas_peak)")


def test_todo_alt_peak_and_floor(self):
    raise NotImplementedError(
        "Need to compute max and min altitude, and alt range for the flight")


class TestFixRecord():
    def test_compute_deltas(self):
        raise NotImplementedError("Need unit tests for the deltas conputation")


class TestFlight():
    @raises(IOError)
    def test_init_file_does_not_exist(self):
        """Raise exception if nonexistent igc file specified"""
        flightlog.Flight('a_file_that_does_not_exist.igc')

    def test_logline_a_valid(self):
        """Parse a valid A record"""
        flight = flightlog.Flight()
        flight._parseline("A123ABCXYZ:1")
        assert flight.flightinfo['flightrecorder'] == "123ABCXYZ:1"

    def test_logline_a_blank(self):
        """Parse a blank A record"""
        flight = flightlog.Flight()
        flight._parseline("A")
        assert flight.flightinfo['flightrecorder'] == ""

    def test_logline_h_flightdate(self):
        """Parse a valid flight date H record"""
        import datetime
        flight = flightlog.Flight()
        flight._parseline("HFDTE250809")
        assert flight.date == datetime.date(2009, 8, 25)

    def test_logline_h_glidertype(self):
        """Parse a valid glidertype H record"""
        flight = flightlog.Flight()
        flight._parseline("HFGTYGLIDERTYPE:LS_8-18")
        assert flight.flightinfo['glidertype'] == "LS_8-18"
        flight._parseline("HFGTYGLIDERTYPE:")
        assert flight.flightinfo['glidertype'] == ""

    def test_logline_i_valid(self):
        """Parse a valid I record"""
        flight = flightlog.Flight()
        flight._parseline("I023638FXA3941ENL")
        assert "fxa" in flight.optfields
        assert flight.optfields['fxa'] == (35, 38)
        assert "enl" in flight.optfields
        assert flight.optfields['enl'] == (38, 41)

    def test_logline_h_flightdate_invalid_date(self):
        """Raise exception when invalid date in the H record"""
        flight = flightlog.Flight()
        # Month is 13
        assert_raises(flightlog.IGCError, flight._parseline, "HFDTE251309")
        # Day is 60
        assert_raises(flightlog.IGCError, flight._parseline, "HFDTE600809")
        # Not numbers
        assert_raises(flightlog.IGCError, flight._parseline, "HFDTEGARBAGE")
        # No year
        assert_raises(flightlog.IGCError, flight._parseline, "HFDTE2513")

    @raises(flightlog.IGCError)
    def test_logline_b_missing_flightdate(self):
        """Raise an assert when B records are encountered before the flight
        date is set
        """
        flight = flightlog.Flight()
        flight._parseline("B1049155210978N00006639WA0011400065031000")

    def test_logline_b_valid(self):
        """Parse a valid B record with no optional fields"""
        import datetime
        flight = flightlog.Flight()
        flight.date = datetime.date(2009, 1, 1)
        flight._parseline("B1049155210978N00006639WA0011400065")
        assert len(flight.fixrecords) == 1
        testrecord = flight.fixrecords[0]
        assert (testrecord['datetime'] ==
                datetime.datetime(2009, 1, 1, 10, 49, 15))
        assert testrecord['latitude'] == 52 + 10.978/60
        assert testrecord['longitude'] == (0 + 6.639/60) * -1
        assert testrecord['avflag'] is True
        assert testrecord['pressure'] == 114
        assert testrecord['alt_gps'] == 65

    def test_logline_b_two_records_across_days(self):
        """Parse two B records that cross midnight and properly
        handle the date change"""
        import datetime
        flight = flightlog.Flight()
        flight.date = datetime.date(2009, 1, 1)
        flight._parseline("B2242175210978N00006639WA0011400065")
        flight._parseline("B0946085230417N00053009EV0084200805")
        assert len(flight.fixrecords) == 2
        testrecord = flight.fixrecords[0]
        assert (testrecord['datetime'] ==
                datetime.datetime(2009, 1, 1, 22, 42, 17))
        assert testrecord['latitude'] == 52 + 10.978/60
        assert testrecord['longitude'] == (0 + 6.639/60) * -1
        assert testrecord['avflag'] is True
        assert testrecord['pressure'] == 114
        assert testrecord['alt_gps'] == 65
        testrecord = flight.fixrecords[1]
        assert (testrecord['datetime'] ==
                datetime.datetime(2009, 1, 2, 9, 46, 8))
        assert testrecord['latitude'] == 52 + 30.417/60
        assert testrecord['longitude'] == (0 + 53.009/60)
        assert testrecord['avflag'] is False
        assert testrecord['pressure'] == 842
        assert testrecord['alt_gps'] == 805

    def test_logline_b_with_optional_fields(self):
        """Parse a B record with optional fields"""
        import datetime
        flight = flightlog.Flight()
        flight.date = datetime.date(2009, 1, 1)
        flight._parseline("I023638FXA3941ENL")
        flight._parseline("B1246085230417N00053009EA0084200805034002")
        testrecord = flight.fixrecords[0]
        assert 'fxa' in testrecord['optfields']
        assert testrecord['optfields']['fxa'] == "034"
        assert 'enl' in testrecord['optfields']
        assert testrecord['optfields']['enl'] == "002"

    def test_init_simple_igc_file(self):
        """Parse a sample igc file that is very short"""
        import datetime
        flight = flightlog.Flight('test/sample_simple_igc_file.txt')
        assert flight.flightinfo['flightrecorder'] == "LXNGIIFLIGHT:1"
        assert flight.date == datetime.date(2009, 8, 25)
        assert len(flight.fixrecords) == 1
        assert len(flight.optfields) == 0

    def test_init_with_file_object(self):
        """Generate a flight using a file object"""
        import datetime
        fileobj = open('test/sample_simple_igc_file.txt', 'r')
        flight = flightlog.Flight(fileobj)
        assert flight.flightinfo['flightrecorder'] == "LXNGIIFLIGHT:1"
        assert flight.date == datetime.date(2009, 8, 25)
        assert len(flight.fixrecords) == 1
        assert len(flight.optfields) == 0

    def test_init_complex_igc_file(self):
        """Parse a complex igc file"""
        flight = flightlog.Flight('test/sample_complex_igc_file.txt')
        assert len(flight.fixrecords) == 1144


class TestIGCError():
    def test_string(self):
        """Ensure IGCErrors output messages properly"""
        try:
            raise flightlog.IGCError(line_num=10, msg="unit test")
        except flightlog.IGCError as e:
            assert type(e) is flightlog.IGCError
            assert "unit test" in str(e)
