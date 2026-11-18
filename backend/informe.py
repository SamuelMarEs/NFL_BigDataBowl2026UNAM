"""T8: informe de texto por defensor. Intenta Amazon Bedrock (Nova) con Strands Agents.
Si falla por cualquier motivo (sin llaves, sin red, timeout), devuelve una plantilla con las mismas cifras.
No lee ni valida llaves AWS: boto3 las toma del entorno (.env en local, rol de la tarea en AWS).
"""
import os


def plantilla(d: dict) -> str:
    mejor = d["delta_medio"] >= 0
    t = (
        f"{d['nombre']} ({d['posicion']}, {d['equipo']}) tuvo {d['plays']} pases como defensor más cercano. "
        f"Concedió en promedio {abs(d['delta_medio']):.2f} yardas esperadas {'menos' if mejor else 'más'} "
        f"que un defensor promedio en las mismas jugadas ({'mejor' if mejor else 'peor'} que el fantasma; "
        f"error estándar {d['error_estandar']:.2f}). "
        f"Delta en cobertura man: {d['delta_man']:.2f}; en zone: {d['delta_zone']:.2f}."
    )
    b = d.get("boxscore")
    if b:
        t += (f" Boxscore: {b['intercepciones']} intercepciones, {b['pases_defendidos']} pases defendidos, "
              f"{b['fumbles_forzados']} fumbles forzados, {b['tackles_completos']} tackles en pases completos.")
    return t


def _datos(d: dict) -> str:
    lineas = [f"Nombre: {d['nombre']}", f"Posición: {d['posicion']}", f"Equipo: {d['equipo']}",
              f"Pases como defensor más cercano: {d['plays']}",
              f"Delta medio (yardas esperadas concedidas, positivo = mejor que el fantasma): {d['delta_medio']:.2f}",
              f"Delta total: {d['delta_total']:.1f}", f"Error estándar del delta medio: {d['error_estandar']:.2f}",
              f"Delta en cobertura man: {d['delta_man']:.2f}", f"Delta en cobertura zone: {d['delta_zone']:.2f}"]
    b = d.get("boxscore")
    if b:
        lineas += [f"Intercepciones: {b['intercepciones']}", f"Pases defendidos: {b['pases_defendidos']}",
                   f"Fumbles forzados: {b['fumbles_forzados']}", f"Tackles en pases completos: {b['tackles_completos']}"]
    return "\n".join(lineas)


SISTEMA = (
    "Eres analista de la NFL. Escribes en español, en un párrafo de 3 a 4 oraciones, para un coach o reclutador. "
    "Usa solo las cifras que te dan, sin inventar datos ni jugadas. Si el error estándar es mayor o igual que "
    "el valor absoluto del delta medio, di que la diferencia no es concluyente. Un delta de 0 en man o zone "
    "puede significar que no hubo pases de ese tipo. La evaluación es al momento del lanzamiento del pase."
)

_cache: dict[int, str] = {}


def _con_ia(d: dict) -> str:
    from botocore.config import Config
    from strands import Agent
    from strands.models import BedrockModel

    modelo = BedrockModel(
        model_id=os.environ.get("BEDROCK_MODEL_ID", "us.amazon.nova-pro-v1:0"),
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
        boto_client_config=Config(connect_timeout=5, read_timeout=20, retries={"max_attempts": 1}),
        max_tokens=400, temperature=0.2,
    )
    agente = Agent(model=modelo, system_prompt=SISTEMA, callback_handler=None)
    texto = str(agente("Redacta el informe de este defensor:\n" + _datos(d))).strip()
    if not texto:
        raise ValueError("respuesta vacía")
    return texto


def generar(d: dict) -> dict:
    """Devuelve {"texto", "generado_con_ia"}. Nunca lanza excepción."""
    if d["nflId"] in _cache:
        return {"texto": _cache[d["nflId"]], "generado_con_ia": True}
    try:
        texto = _con_ia(d)
        _cache[d["nflId"]] = texto
        return {"texto": texto, "generado_con_ia": True}
    except Exception:
        return {"texto": plantilla(d), "generado_con_ia": False}
