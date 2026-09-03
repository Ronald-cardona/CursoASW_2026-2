import csv
import json
from pathlib import Path

def leer_estudiantes(ruta_csv):
    with Path(ruta_csv).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def transformar_estudiante(estudiante):
    return {
        "id": estudiante["codigo"],
        "nombre_completo": f"{estudiante['nombre']} {estudiante['apellido']}",
        "semestre": int(estudiante["semestre"]),
        "promedio": float(estudiante["promedio"]),
        "estado": "Activo" if estudiante["activo"].strip().lower() == "true" else "Inactivo"
    }

if __name__ == "__main__":
    estudiantes = leer_estudiantes("datos/estudiantes.csv")
    transformados = [transformar_estudiante(e) for e in estudiantes]

    with Path("salida/estudiantes_resumen.json").open("w", encoding="utf-8") as f:
        json.dump(transformados, f, indent=2, ensure_ascii=False)

    print(f"Se transformaron {len(transformados)} estudiantes")