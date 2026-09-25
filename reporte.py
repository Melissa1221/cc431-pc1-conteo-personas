import pickle
import csv
import numpy as np
import matplotlib.pyplot as plt

# Usa la muestra de 10 minutos para estimar cuanta gente pasa por la vereda
# en una hora, un dia, una semana y un mes.

INICIO = (19, 59, 8)          # hora de inicio de la grabacion (nombre del archivo 20260924_195908)
DURACION_MIN = 9.98           # minutos analizados
HORAS_DIA = 15                # la FC tiene movimiento de 7:00 a 22:00 aprox.
DIAS_SEMANA = 5               # lunes a viernes (sabado casi no hay clases en la FC)
SEMANAS_MES = 4

with open('eventos.pkl', 'rb') as file:
    eventos = pickle.load(file)
with open('factor.pkl', 'rb') as file:
    factor = pickle.load(file)
manual = list(csv.DictReader(open('conteo_manual.csv')))

# ---------- flujo por minuto ----------
auto_min = np.zeros(10)
for t, d, n in eventos:
    auto_min[min(int(t // 60), 9)] += n

man_min = np.zeros(10)
for fila in manual:
    # el conteo manual es por ventana; lo ponemos en el minuto donde cae la ventana
    medio = (float(fila['inicio_s']) + float(fila['fin_s'])) / 2
    man_min[min(int(medio // 60), 9)] += int(fila['izquierda']) + int(fila['derecha'])

etiquetas = []
for m in range(10):
    total_seg = INICIO[0] * 3600 + INICIO[1] * 60 + INICIO[2] + m * 60
    etiquetas.append(f'{total_seg // 3600}:{(total_seg % 3600) // 60:02d}')

x = np.arange(10)
plt.figure(figsize=(9, 4.5))
plt.bar(x - 0.2, auto_min, 0.4, label='conteo automatico', color='#2a7de1')
plt.bar(x + 0.2, man_min, 0.4, label='conteo manual (a ojo)', color='#f28c28')
plt.xticks(x, etiquetas)
plt.xlabel('hora (jueves 24/09/2026)')
plt.ylabel('personas por minuto')
plt.title('Personas que cruzan la vereda frente al Reloj Solar (FC-UNI)')
plt.axvspan(5.5, 8.5, color='gray', alpha=0.15)
plt.text(7, max(man_min) * 0.93, 'pico: salida del\nbloque 18-20?', ha='center')
plt.legend(loc='upper left')
plt.tight_layout()
plt.savefig('flujo_por_minuto.png', dpi=150)

# ---------- extrapolacion ----------
total_auto = auto_min.sum()
total_corr = total_auto * factor
por_min = total_corr / DURACION_MIN
print(f'muestra: {total_auto:.0f} personas contadas en {DURACION_MIN} min')
print(f'corregido por grupos (x{factor:.2f}): {total_corr:.0f} personas')
print(f'ritmo: {por_min:.1f} personas/min')
print()

# Escenario A (ingenuo): todo el dia es como estos 10 minutos
hora_a = por_min * 60
dia_a = hora_a * HORAS_DIA
print('Escenario A - todo el dia igual que la muestra')
print(f'  hora:   {hora_a:8.0f}')
print(f'  dia:    {dia_a:8.0f}')
print(f'  semana: {dia_a * DIAS_SEMANA:8.0f}')
print(f'  mes:    {dia_a * DIAS_SEMANA * SEMANAS_MES:8.0f}')
print()

# Escenario B: separamos el "pico" (20:05-20:07, justo despues de que terminan las
# clases de 18 a 20) del "valle" (el resto). Hipotesis: cada hora tiene 3 min de pico
# (en la UNI los bloques de clase terminan a la hora exacta) y 57 min de valle.
PICO = [6, 7, 8]
VALLE = [0, 1, 2, 3, 4, 5, 9]
valle = auto_min[VALLE].sum() * factor / len(VALLE)
pico = auto_min[PICO].sum() * factor / len(PICO)
hora_b = valle * 57 + pico * 3
dia_b = hora_b * HORAS_DIA
print(f'Escenario B - valle {valle:.1f}/min (clases en curso) + pico {pico:.1f}/min (cambio de hora)')
print(f'  hora:   {hora_b:8.0f}')
print(f'  dia:    {dia_b:8.0f}')
print(f'  semana: {dia_b * DIAS_SEMANA:8.0f}')
print(f'  mes:    {dia_b * DIAS_SEMANA * SEMANAS_MES:8.0f}')
print()
print(f'el pico es {pico / valle:.1f} veces el valle')
print('grafico guardado en flujo_por_minuto.png')
