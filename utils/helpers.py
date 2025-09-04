from num2words import num2words
# utils/helpers.py  (agregar)
from datetime import datetime

def validar_fecha_no_futura(fecha_str: str) -> bool:
    try:
        d = datetime.strptime(fecha_str, "%d/%m/%Y").date()
        return d <= datetime.now().date()
    except Exception:
        return False

def numero_a_letras(monto):
    entero = int(monto)
    centavos = int(round((monto - entero) * 100))

    texto = num2words(entero, lang='es').capitalize()

    if centavos > 0:
        texto += f" con {centavos:02}/100"
    else:
        texto += " con 00/100"

    return texto
