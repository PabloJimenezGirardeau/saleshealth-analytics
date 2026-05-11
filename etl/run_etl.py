"""
run_etl.py — Orquestador del pipeline ETL
Ejecuta las 6 fases en secuencia con logging de tiempos.

Uso:
    python -m etl.run_etl
"""

import time
from datetime import datetime
from etl.db import get_engine
from etl.extract import extract
from etl.load_dimensions import load_dimensions
from etl.load_facts import load_facts
from etl.validate import validate
from etl.customer_360 import load_customer_360
from etl.clusters import build_clusters


def _sep(char='─', n=60):
    return char * n


def _fmt_time(seconds: float) -> str:
    return f'{seconds:.1f}s'


def run():
    print(_sep('═'))
    print(f'  PIPELINE ETL — saleshealth DWH')
    print(f'  Inicio: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(_sep('═'))

    engine     = get_engine()
    t_total    = time.time()
    resultados = {}

    # ── FASE 1: EXTRACT ───────────────────────────────────────────────────────
    print(f'\n>>> FASE 1/6 — EXTRACT')
    t0 = time.time()
    res_extract = extract(engine)
    t1 = time.time()
    total_stg = sum(res_extract.values())
    print(f'    {len(res_extract)} tablas copiadas a stg.*  |  '
          f'{total_stg:,} registros  |  {_fmt_time(t1-t0)}')
    resultados['extract'] = res_extract

    # ── FASE 2: DIMENSIONES ───────────────────────────────────────────────────
    print(f'\n>>> FASE 2/6 — DIMENSIONES')
    t0 = time.time()
    res_dims = load_dimensions(engine)
    t1 = time.time()
    for dim, n in res_dims.items():
        print(f'    {dim:<30} {n:>6,} registros')
    print(f'    {_sep(n=40)}')
    print(f'    7 dimensiones cargadas  |  {_fmt_time(t1-t0)}')
    resultados['dimensiones'] = res_dims

    # ── FASE 3: HECHOS ────────────────────────────────────────────────────────
    print(f'\n>>> FASE 3/6 — HECHOS')
    t0 = time.time()
    res_facts = load_facts(engine)
    t1 = time.time()
    for fact, n in res_facts.items():
        print(f'    {fact:<30} {n:>6,} registros')
    print(f'    {_sep(n=40)}')
    print(f'    2 tablas de hechos cargadas  |  {_fmt_time(t1-t0)}')
    resultados['hechos'] = res_facts

    # ── FASE 4: VALIDACIONES ──────────────────────────────────────────────────
    print(f'\n>>> FASE 4/6 — VALIDACIONES')
    t0 = time.time()
    res_val = validate(engine)
    t1 = time.time()

    for r in res_val['detalles']:
        estado = '✅' if r['ok'] else '❌'
        print(f'    {estado} [{r["id"]}] {r["desc"]}', end='')
        if not r['ok']:
            print(f'  → obtenido: {r["valor"]}, esperado: {r["esperado"]}')
        else:
            print()

    print(f'    {_sep(n=40)}')
    print(f'    {res_val["passed"]}/{res_val["total"]} validaciones OK  |  {_fmt_time(t1-t0)}')

    if res_val['failed'] > 0:
        print(f'\n    ⚠  {res_val["failed"]} validaciones fallaron.')
        print(f'    El pipeline continuará, pero revisa los errores.')

    resultados['validaciones'] = res_val

    # ── FASE 5: CUSTOMER 360 ──────────────────────────────────────────────────
    print(f'\n>>> FASE 5/6 — CUSTOMER 360')
    t0 = time.time()
    n_clientes = load_customer_360(engine)
    t1 = time.time()
    print(f'    marts.customer_360 cargada  |  '
          f'{n_clientes:,} clientes  |  {_fmt_time(t1-t0)}')
    resultados['customer_360'] = n_clientes

    # ── FASE 6: CLUSTERING ────────────────────────────────────────────────────
    print(f'\n>>> FASE 6/6 — CLUSTERING')
    t0 = time.time()
    try:
        conteo = build_clusters(engine)
        t1 = time.time()
        for label, n in sorted(conteo.items()):
            print(f'    Cluster {label:<20} {n:>6,} clientes')
        print(f'    {_sep(n=40)}')
        print(f'    K-Means K=4 completado  |  {_fmt_time(t1-t0)}')
        resultados['clusters'] = conteo
    except ImportError as e:
        print(f'    ⚠  {e}')
        print(f'    Clustering omitido — instala scikit-learn para habilitarlo.')
        resultados['clusters'] = {}

    # ── RESUMEN FINAL ─────────────────────────────────────────────────────────
    t_elapsed = time.time() - t_total
    print(f'\n{_sep("═")}')
    estado_val = f'{res_val["passed"]}/{res_val["total"]} validaciones'
    if res_val['failed'] == 0:
        print(f'  ✅ PIPELINE ETL COMPLETADO')
    else:
        print(f'  ⚠  PIPELINE ETL COMPLETADO CON ADVERTENCIAS')
    print(f'  Tiempo total : {_fmt_time(t_elapsed)}')
    print(f'  Validaciones : {estado_val}')
    print(f'  Clientes 360 : {n_clientes:,}')
    print(f'  Fin          : {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(_sep('═'))

    return resultados


if __name__ == '__main__':
    run()
