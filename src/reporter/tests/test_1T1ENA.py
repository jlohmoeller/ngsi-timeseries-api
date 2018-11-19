from conftest import QL_URL
from reporter.tests.utils import insert_test_data
from conftest import crate_translator as translator
import pytest
import requests
from utils.common import assert_equal_time_index_arrays

entity_type = 'Room'
entity_id = 'Room0'
temperature = 'temperature'
pressure = 'pressure'
n_days = 30


def query_url(values=False):
    url = "{qlUrl}/entities/{entityId}"
    if values:
        url += '/value'
    return url.format(
        qlUrl=QL_URL,
        entityId=entity_id,
    )


@pytest.fixture()
def reporter_dataset(translator):
    insert_test_data(translator,
                     [entity_type],
                     n_entities=1,
                     n_days=30)
    yield


def assert_1T1ENA_response(obtained, expected):
    """
    Check API responses for 1T1ENA
    """
    # Assert time index
    obt_index = obtained['data'].pop('index')
    exp_index = expected['data'].pop('index')
    assert_equal_time_index_arrays(obt_index, exp_index)

    # Assert rest of data
    assert obtained == expected


def test_1T1ENA_defaults(reporter_dataset):
    # Query
    query_params = {
        'type': entity_type,
    }
    r = requests.get(query_url(), params=query_params)
    assert r.status_code == 200, r.text

    # Assert
    expected_temperatures = list(range(n_days))
    expected_pressures = [t*10 for t in expected_temperatures]
    expected_index = [
        '1970-01-{:02}T00:00:00'.format(i+1) for i in expected_temperatures
    ]
    expected = {
        'data': {
            'entityId': entity_id,
            'index': expected_index,
            'attributes': [
                {
                    'attrName': pressure,
                    'values': expected_pressures,
                },
                {
                    'attrName': temperature,
                    'values': expected_temperatures,
                },
            ]
        }
    }
    obtained = r.json()
    assert_1T1ENA_response(obtained, expected)


@pytest.mark.parametrize("aggr_meth, aggr_press, aggr_temp", [
    ("count", 30, 30),
    ("sum", 4350, 435),
    ("avg", 145, 14.5),
    ("min", 0, 0),
    ("max", 290, 29),
])
def test_1T1ENA_aggrMethod(reporter_dataset, aggr_meth, aggr_press, aggr_temp):
    # Query
    query_params = {
        'type': entity_type,
        'aggrMethod': aggr_meth,
        'attrs': temperature + ',' + pressure,
    }
    r = requests.get(query_url(), params=query_params)
    assert r.status_code == 200, r.text

    # Assert
    expected = {
        'data': {
            'entityId': entity_id,
            'index': [],
            'attributes': [
                {
                    'attrName': pressure,
                    'values': [aggr_press],
                },
                {
                    'attrName': temperature,
                    'values': [aggr_temp],
                },
            ]
        }
    }
    obtained = r.json()
    assert_1T1ENA_response(obtained, expected)


def test_1T1ENA_aggrPeriod(reporter_dataset):
    # GH issue https://github.com/smartsdk/ngsi-timeseries-api/issues/89

    # aggrPeriod needs aggrMethod
    query_params = {
        'type': entity_type,
        'aggrPeriod': 'minute',
    }
    r = requests.get(query_url(), params=query_params)
    assert r.status_code == 400, r.text

    query_params = {
        'type': entity_type,
        'aggrMethod': 'avg',
        'aggrPeriod': 'minute',
    }
    r = requests.get(query_url(), params=query_params)
    assert r.status_code == 501, r.text


def test_1T1ENA_fromDate_toDate(reporter_dataset):
    # Query
    query_params = {
        'type': entity_type,
        'fromDate': "1970-01-06T00:00:00",
        'toDate': "1970-01-17T00:00:00",
    }
    r = requests.get(query_url(), params=query_params)
    assert r.status_code == 200, r.text

    # Expect only last N
    expected_temperatures = list(range(5, 17))
    expected_pressures = [t*10 for t in expected_temperatures]
    expected_index = [
        '1970-01-{:02}T00:00:00'.format(i+1) for i in expected_temperatures
    ]
    assert len(expected_index) == 12
    assert expected_index[0] == "1970-01-06T00:00:00"
    assert expected_index[-1] == "1970-01-17T00:00:00"

    # Assert
    expected = {
        'data': {
            'entityId': entity_id,
            'index': expected_index,
            'attributes': [
                {
                    'attrName': pressure,
                    'values': expected_pressures,
                },
                {
                    'attrName': temperature,
                    'values': expected_temperatures,
                },
            ]
        }
    }
    obtained = r.json()
    assert_1T1ENA_response(obtained, expected)


def test_1T1ENA_lastN(reporter_dataset):
    # Query
    query_params = {
        'type': entity_type,
        'lastN': 10
    }
    r = requests.get(query_url(), params=query_params)
    assert r.status_code == 200, r.text

    # Expect only last N
    expected_temperatures = list(range(n_days-10, n_days))
    expected_pressures = [t*10 for t in expected_temperatures]
    expected_index = [
        '1970-01-{:02}T00:00:00'.format(i+1) for i in expected_temperatures
    ]
    assert len(expected_index) == 10
    assert expected_index[0] == "1970-01-21T00:00:00"
    assert expected_index[-1] == "1970-01-30T00:00:00"

    # Assert
    expected = {
        'data': {
            'entityId': entity_id,
            'index': expected_index,
            'attributes': [
                {
                    'attrName': pressure,
                    'values': expected_pressures,
                },
                {
                    'attrName': temperature,
                    'values': expected_temperatures,
                },
            ]
        }
    }
    obtained = r.json()
    assert_1T1ENA_response(obtained, expected)


def test_1T1ENA_limit(reporter_dataset):
    # Query
    query_params = {
        'type': entity_type,
        'limit': 5
    }
    r = requests.get(query_url(), params=query_params)
    assert r.status_code == 200, r.text

    # Expect only last N
    expected_temperatures = list(range(5))
    expected_pressures = [t*10 for t in expected_temperatures]
    expected_index = [
        '1970-01-{:02}T00:00:00'.format(i+1) for i in expected_temperatures
    ]
    assert len(expected_index) == 5
    assert expected_index[0] == "1970-01-01T00:00:00"
    assert expected_index[-1] == "1970-01-05T00:00:00"

    # Assert
    expected = {
        'data': {
            'entityId': entity_id,
            'index': expected_index,
            'attributes': [
                {
                    'attrName': pressure,
                    'values': expected_pressures,
                },
                {
                    'attrName': temperature,
                    'values': expected_temperatures,
                },
            ]
        }
    }
    obtained = r.json()
    assert_1T1ENA_response(obtained, expected)


def test_1T1ENA_offset(reporter_dataset):
    # Query
    query_params = {
        'type': entity_type,
        'offset': 3
    }
    r = requests.get(query_url(), params=query_params)
    assert r.status_code == 200, r.text

    # Expect only last N
    expected_temperatures = list(range(3, n_days))
    expected_pressures = [t*10 for t in expected_temperatures]
    expected_index = [
        '1970-01-{:02}T00:00:00'.format(i+1) for i in expected_temperatures
    ]
    assert len(expected_index) == 27
    assert expected_index[0] == "1970-01-04T00:00:00"
    assert expected_index[-1] == "1970-01-30T00:00:00"

    # Assert
    expected = {
        'data': {
            'entityId': entity_id,
            'index': expected_index,
            'attributes': [
                {
                    'attrName': pressure,
                    'values': expected_pressures,
                },
                {
                    'attrName': temperature,
                    'values': expected_temperatures,
                },
            ]
        }
    }
    obtained = r.json()
    assert_1T1ENA_response(obtained, expected)


def test_1T1ENA_combined(reporter_dataset):
    # Query
    query_params = {
        'type': entity_type,
        'offset': 2,
        'toDate': "1970-01-20T00:00:00",
        'limit': 28,
    }
    r = requests.get(query_url(), params=query_params)
    assert r.status_code == 200, r.text

    # Expect only last N
    expected_temperatures = list(range(2, 20))
    expected_pressures = [t*10 for t in expected_temperatures]
    expected_index = [
        '1970-01-{:02}T00:00:00'.format(i+1) for i in expected_temperatures
    ]
    assert len(expected_index) == 18
    assert expected_index[0] == "1970-01-03T00:00:00"
    assert expected_index[-1] == "1970-01-20T00:00:00"

    # Assert
    expected = {
        'data': {
            'entityId': entity_id,
            'index': expected_index,
            'attributes': [
                {
                    'attrName': pressure,
                    'values': expected_pressures,
                },
                {
                    'attrName': temperature,
                    'values': expected_temperatures,
                },
            ]
        }
    }
    obtained = r.json()
    assert_1T1ENA_response(obtained, expected)


def test_1T1ENA_values_defaults(reporter_dataset):
    # Query
    query_params = {
        'type': entity_type,
    }
    r = requests.get(query_url(values=True), params=query_params)
    assert r.status_code == 200, r.text

    # Assert
    expected_temperatures = list(range(n_days))
    expected_pressures = [t*10 for t in expected_temperatures]
    expected_index = [
        '1970-01-{:02}T00:00:00'.format(i+1) for i in expected_temperatures
    ]
    expected = {
        'data': {
            'index': expected_index,
            'attributes': [
                {
                    'attrName': pressure,
                    'values': expected_pressures,
                },
                {
                    'attrName': temperature,
                    'values': expected_temperatures,
                },
            ]
        }
    }
    obtained = r.json()
    assert_1T1ENA_response(obtained, expected)


def test_not_found():
    query_params = {
        'type': entity_type,
    }
    r = requests.get(query_url(), params=query_params)
    print(r.text)
    assert r.status_code == 404, r.text
    assert r.json() == {
        "error": "Not Found",
        "description": "No records were found for such query."
    }
