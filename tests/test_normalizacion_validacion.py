import integrador


def test_normalizar_proveedor_a_convierte_unidades():
    registro = {
        "provider_record_id": "PRUEBA-A-001",
        "station": {
            "city_name": "Medellin",
            "country_code": "CO",
        },
        "location": {
            "lat": "6.25",
            "lon": "-75.56",
        },
        "measurements": {
            "temperature_f": 68,
            "relative_humidity": 50,
            "wind_speed_ms": 10,
        },
        "observed_at": "2026-09-01T10:00:00-05:00",
        "source": "weather_provider_a",
    }

    resultado = integrador.normalizar_registro_a(registro)

    assert resultado["ok"] is True
    assert resultado["dato"]["temperatura_c"] == 20.0
    assert resultado["dato"]["viento_kmh"] == 36.0
    assert resultado["dato"]["origen"] == "proveedor_a"


def test_normalizar_proveedor_b_transforma_fecha_y_origen():
    registro = {
        "record_code": "PRUEBA-B-001",
        "municipality": "Medellin",
        "country": "CO",
        "latitude_deg": "6.25",
        "longitude_deg": "-75.56",
        "temp_celsius": "22.5",
        "humidity_pct": "60",
        "wind_kmh": "15",
        "measurement_time": "01/09/2026 10:30",
        "origin_code": "PB",
    }

    resultado = integrador.normalizar_registro_b(registro)

    assert resultado["ok"] is True
    assert resultado["dato"]["temperatura_c"] == 22.5
    assert resultado["dato"]["origen"] == "proveedor_b"
    assert resultado["dato"]["fecha_hora"] == "2026-09-01T10:30:00-05:00"


def test_validar_registro_correcto():
    dato = {
        "ciudad": "Medellin",
        "pais": "CO",
        "latitud": 6.25,
        "longitud": -75.56,
        "temperatura_c": 22.0,
        "humedad": 60.0,
        "viento_kmh": 15.0,
        "fecha_hora": "2026-09-01T10:00:00-05:00",
        "origen": "proveedor_a",
    }

    es_valido, motivos = integrador.validar_registro(dato)

    assert es_valido is True
    assert motivos == []


def test_rechazar_registro_con_humedad_fuera_de_rango():
    dato = {
        "ciudad": "Medellin",
        "pais": "CO",
        "latitud": 6.25,
        "longitud": -75.56,
        "temperatura_c": 22.0,
        "humedad": 101.0,
        "viento_kmh": 15.0,
        "fecha_hora": "2026-09-01T10:00:00-05:00",
        "origen": "proveedor_a",
    }

    es_valido, motivos = integrador.validar_registro(dato)

    assert es_valido is False
    assert "humedad fuera de rango: 101.0" in motivos


def test_valores_limite_son_validos():
    dato = {
        "ciudad": "Medellin",
        "pais": "CO",
        "latitud": 90,
        "longitud": 180,
        "temperatura_c": 0.0,
        "humedad": 100,
        "viento_kmh": 0,
        "fecha_hora": "2026-09-01T10:00:00-05:00",
        "origen": "proveedor_b",
    }

    es_valido, motivos = integrador.validar_registro(dato)

    assert es_valido is True
    assert motivos == []