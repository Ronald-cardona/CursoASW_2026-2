import integrador


class RespuestaFalsa:
    def __init__(self, codigo, mensaje):
        self.status_code = codigo
        self.text = ""

        self._contenido = {
            "mensaje": mensaje
        }

    def json(self):
        return self._contenido


def test_reintenta_errores_503_hasta_aceptar(monkeypatch):
    respuestas = [
        RespuestaFalsa(503, "Servicio no disponible"),
        RespuestaFalsa(503, "Servicio no disponible"),
        RespuestaFalsa(201, "Medición registrada"),
    ]

    def envio_falso(registro):
        return respuestas.pop(0)

    monkeypatch.setattr(
        integrador,
        "enviar_medicion",
        envio_falso
    )

    registro = {
        "id_origen": "PRUEBA-001",
        "dato": {}
    }

    resultado = integrador.enviar_medicion_con_reintentos(registro)

    assert resultado["resultado"] == "aceptado"
    assert resultado["codigo_http"] == 201
    assert resultado["intentos"] == 3


def test_timeout_agota_tres_intentos(monkeypatch):
    contador = {"intentos": 0}

    def envio_con_timeout(registro):
        contador["intentos"] += 1
        raise integrador.requests.exceptions.Timeout()

    monkeypatch.setattr(
        integrador,
        "enviar_medicion",
        envio_con_timeout
    )

    registro = {
        "id_origen": "PRUEBA-TIMEOUT",
        "dato": {}
    }

    resultado = integrador.enviar_medicion_con_reintentos(registro)

    assert resultado["resultado"] == "error_comunicacion"
    assert resultado["intentos"] == 3
    assert contador["intentos"] == 3
    assert resultado["codigo_http"] is None


def test_error_conexion_agota_tres_intentos(monkeypatch):
    contador = {"intentos": 0}

    def envio_sin_conexion(registro):
        contador["intentos"] += 1
        raise integrador.requests.exceptions.ConnectionError()

    monkeypatch.setattr(
        integrador,
        "enviar_medicion",
        envio_sin_conexion
    )

    registro = {
        "id_origen": "PRUEBA-CONEXION",
        "dato": {}
    }

    resultado = integrador.enviar_medicion_con_reintentos(registro)

    assert resultado["resultado"] == "error_comunicacion"
    assert resultado["intentos"] == 3
    assert contador["intentos"] == 3
    assert resultado["codigo_http"] is None

def test_enviar_varios_registros_validos(monkeypatch):
    registros = [
        {
            "id_origen": "PRUEBA-001",
            "dato": {}
        },
        {
            "id_origen": "PRUEBA-002",
            "dato": {}
        },
        {
            "id_origen": "PRUEBA-003",
            "dato": {}
        }
    ]

    def envio_falso(registro):
        return {
            "id_origen": registro["id_origen"],
            "codigo_http": 201,
            "resultado": "aceptado",
            "reintentar": False,
            "intentos": 1,
            "respuesta": {
                "mensaje": "Medición registrada"
            }
        }

    monkeypatch.setattr(
        integrador,
        "enviar_medicion_con_reintentos",
        envio_falso
    )

    resultados = integrador.enviar_registros_validos(registros)

    assert len(resultados) == 3
    assert resultados[0]["id_origen"] == "PRUEBA-001"
    assert resultados[1]["id_origen"] == "PRUEBA-002"
    assert resultados[2]["id_origen"] == "PRUEBA-003"

    assert all(
        resultado["resultado"] == "aceptado"
        for resultado in resultados
    )    

def test_generar_reporte_resume_resultados():
    clasificados = {
        "validos": [
            {"id_origen": "A-001"},
            {"id_origen": "A-002"},
            {"id_origen": "A-003"},
        ],
        "rechazados_localmente": [
            {"id_origen": "B-001"}
        ],
        "error_normalizacion": [
            {"id_origen": "B-002"}
        ],
    }

    resultados_envio = [
        {
            "id_origen": "A-001",
            "resultado": "aceptado"
        },
        {
            "id_origen": "A-002",
            "resultado": "rechazado_api"
        },
        {
            "id_origen": "A-003",
            "resultado": "error_comunicacion"
        },
    ]

    consulta_final = {
        "ok": True,
        "codigo_http": 200,
        "respuesta": {
            "total": 1
        },
    }

    reporte = integrador.generar_reporte(
        procesados=5,
        clasificados=clasificados,
        resultados_envio=resultados_envio,
        consulta_final=consulta_final,
    )

    resumen = reporte["resumen"]

    assert resumen["procesados"] == 5
    assert resumen["normalizados"] == 4
    assert resumen["errores_normalizacion"] == 1
    assert resumen["validos_localmente"] == 3
    assert resumen["rechazados_localmente"] == 1
    assert resumen["enviados"] == 3
    assert resumen["aceptados_api"] == 1
    assert resumen["rechazados_api"] == 1
    assert resumen["errores_comunicacion"] == 1