import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import openpyxl

HISTORIAL_PATH = Path("historial/recibos.xlsx")


def crear_pestana_buscar(tabs):
    frame = ttk.Frame(tabs)
    tabs.add(frame, text="🔍 Buscar / Editar")

    ttk.Label(frame, text="Buscar por:").grid(row=0, column=0, sticky="w", pady=5)
    criterio = ttk.Combobox(frame, values=["Número", "Cliente", "Fecha"])
    criterio.grid(row=0, column=1)
    entrada = ttk.Entry(frame, width=30)
    entrada.grid(row=0, column=2)

    resultados = tk.Listbox(frame, width=80)
    resultados.grid(row=1, column=0, columnspan=3, pady=10)

    def buscar():
        resultados.delete(0, tk.END)
        if not HISTORIAL_PATH.exists():
            messagebox.showwarning("Sin historial", "No se encontró historial para buscar.")
            return

        libro = openpyxl.load_workbook(HISTORIAL_PATH)
        hoja = libro.active

        campo = criterio.get()
        valor = entrada.get().lower()

        col_map = {"Número": 0, "Cliente": 1, "Fecha": 2}
        idx = col_map.get(campo)

        for fila in hoja.iter_rows(min_row=2, values_only=True):
            if valor in str(fila[idx]).lower():
                resultados.insert(tk.END, " | ".join(str(c) for c in fila))

    ttk.Button(frame, text="Buscar", command=buscar).grid(row=0, column=3, padx=5)

    def editar():
        seleccion = resultados.get(tk.ACTIVE)
        if not seleccion:
            messagebox.showinfo("Seleccionar", "Seleccioná un recibo para editar.")
            return
        messagebox.showinfo("Edición", "Funcionalidad de edición pendiente de implementación.")

    ttk.Button(frame, text="Editar seleccionado", command=editar).grid(row=2, column=0, columnspan=3, pady=10)
