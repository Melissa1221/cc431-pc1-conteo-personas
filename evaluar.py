import pickle
import csv

# Compara el conteo automatico (eventos.pkl, sale de main.py) con nuestro conteo
# manual (conteo_manual.csv: miramos el video y anotamos cada persona que cruzo).

with open('eventos.pkl', 'rb') as file:
    eventos = pickle.load(file)

manual = list(csv.DictReader(open('conteo_manual.csv')))

print('ventana  tiempo      auto(izq,der)  manual(izq,der)')
exactas = 0
tot_auto = [0, 0]
tot_man = [0, 0]
tot_auto_sueltos = [0, 0]
tot_man_sueltos = [0, 0]
for fila in manual:
    a = float(fila['inicio_s'])
    b = float(fila['fin_s'])
    izq = sum(n for t, d, n in eventos if a <= t <= b + 1 and d == 'izquierda')
    der = sum(n for t, d, n in eventos if a <= t <= b + 1 and d == 'derecha')
    mi = int(fila['izquierda'])
    md = int(fila['derecha'])
    ok = (izq == mi and der == md)
    exactas += ok
    tot_auto[0] += izq
    tot_auto[1] += der
    tot_man[0] += mi
    tot_man[1] += md
    # "sueltos" = ventanas donde paso a lo mas 1 persona por direccion
    if mi <= 1 and md <= 1:
        tot_auto_sueltos[0] += izq
        tot_auto_sueltos[1] += der
        tot_man_sueltos[0] += mi
        tot_man_sueltos[1] += md
    marca = '' if ok else '   <-- ' + fila['nota']
    print(f"{fila['ventana']:>5}  {a:6.1f}-{b:6.1f}   {izq:3d} {der:3d}        {mi:3d} {md:3d}{marca}")

total_auto = sum(tot_auto)
total_man = sum(tot_man)
print()
print(f'ventanas exactas: {exactas} de {len(manual)}')
print(f'total automatico: {total_auto}  (izq {tot_auto[0]}, der {tot_auto[1]})')
print(f'total manual:     {total_man}  (izq {tot_man[0]}, der {tot_man[1]})')
print(f'personas que se escaparon: {100 * (1 - total_auto / total_man):.0f} %')
print(f'solo gente caminando sola: auto {sum(tot_auto_sueltos)} vs manual {sum(tot_man_sueltos)}')
factor = total_man / total_auto
print(f'factor de correccion (manual / automatico): {factor:.2f}')

with open('factor.pkl', 'wb') as file:
    pickle.dump(factor, file)
