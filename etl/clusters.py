"""
clusters.py — Fase 6: BUILD CLUSTERS
PCA + K-Means sobre las métricas de customer_360.
Asigna cluster_id y cluster_label a cada cliente.
"""

import pandas as pd
import numpy as np
from etl.config import SCHEMA_MARTS
from etl.db import query
from sqlalchemy import text


FEATURES = [
    'cltv', 'ingresos_netos', 'aov',
    'frecuencia_mensual', 'recencia_dias',
    'return_rate', 'antiguedad_dias'
]

CLUSTER_LABELS = {
    0: 'Champions',
    1: 'Base',
    2: 'Churned',
}


def build_clusters(engine) -> dict:
    try:
        from sklearn.preprocessing import StandardScaler
        from sklearn.decomposition import PCA
        from sklearn.cluster import KMeans
    except ImportError:
        raise ImportError(
            'scikit-learn no instalado. Ejecuta: pip install scikit-learn'
        )

    df = query(engine, f"""
        SELECT cliente_sk, {', '.join(FEATURES)}
        FROM {SCHEMA_MARTS}.customer_360
        WHERE cltv IS NOT NULL
    """)

    if len(df) == 0:
        return {}

    df[FEATURES] = df[FEATURES].fillna(0)
    X = df[FEATURES].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    pca = PCA(n_components=2, random_state=42)
    X_pca = pca.fit_transform(X_scaled)

    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_pca)

    df['cluster_raw'] = labels
    cltv_por_cluster  = df.groupby('cluster_raw')['cltv'].mean().sort_values(ascending=False)
    rank_map          = {c: r for r, c in enumerate(cltv_por_cluster.index)}
    df['cluster_id']    = df['cluster_raw'].map(rank_map)
    df['cluster_label'] = df['cluster_id'].map(CLUSTER_LABELS)

    records = df[['cliente_sk', 'cluster_id', 'cluster_label']].to_dict('records')
    with engine.begin() as conn:
        for rec in records:
            conn.execute(text(f"""
                UPDATE {SCHEMA_MARTS}.customer_360
                SET cluster_id    = :cluster_id,
                    cluster_label = :cluster_label
                WHERE cliente_sk  = :cliente_sk
            """), rec)

    return df.groupby('cluster_label').size().to_dict()