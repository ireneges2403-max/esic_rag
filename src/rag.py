import os
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.neighbors import NearestNeighbors  

os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'


# Inicializamos el modelo de lenguaje (SentenceTransformer)
# Usamos 'hiiamsid/sentence_similarity_spanish_es' por su optimización en español

try:
    model = SentenceTransformer("hiiamsid/sentence_similarity_spanish_es")
except Exception as e:
    print(f"Error al cargar el modelo: {e}")
    raise e

# FASE 1: BÚSQUEDA SEMÁNTICA (RETRIEVAL)
# Buscamos los 15 productos más cercanos en el espacio vectorial a la consulta del usuario

def buscar(consulta, df, buscador_vectorial):
    consulta_limpia = consulta.lower()
    vec = model.encode([consulta_limpia])
    
    # 1. Recupera los 15 más relevantes
    distancias, indices = buscador_vectorial.kneighbors(vec, n_neighbors=15)
    
    resultados_reranked = []

# FASE 2: ALGORITMO DE RE-RANKING
# Evaluamos los 15 candidatos obtenidos aplicando la fórmula estricta de la rúbrica

    for i, idx in enumerate(indices[0]):
        r = df.iloc[idx]
        
        # La distancia va de 0 (idéntico) a más. La invertimos para que mayor sea mejor (0 a 1)
        similitud_semantica = 1 / (1 + distancias[0][i]) 
        
        # Fórmula estricta de la rúbrica: 60% Semántica + 20% Nutri + 20% Precio
        score_final = (0.6 * similitud_semantica) + (0.2 * (r['norm_nutri'] / 100)) + (0.2 * r['norm_precio'])
        
        resultados_reranked.append((score_final, r))
        
    # 3. Ordenamos de mayor a menor puntuación final y nos quedamos los 3 mejores
    resultados_reranked.sort(key=lambda x: x[0], reverse=True)
    mejores_3 = resultados_reranked[:3]
    
    print(f"\nResultados recomendados para: '{consulta}'")
    for score, r in mejores_3:
        print(f"-> {r['titulo']} | Precio: {r['precio']}€ | Salud: {r['score_nutricional']:.2f}")

# Usamos NearestNeighbors (Scikit-Learn) como alternativa a FAISS por compatibilidad con Mac.
# La métrica 'cosine' evalúa la similitud semántica independientemente de la longitud del texto.
def consultar(df_prod):
    print("\nCreando el espacio vectorial de los productos...")
    embeddings = model.encode(df_prod["texto_busqueda"].fillna("").tolist(), show_progress_bar=True)
    
    buscador_vectorial = NearestNeighbors(n_neighbors=15, metric='cosine', algorithm='auto')
    buscador_vectorial.fit(embeddings)
    
    while True:
        q = input("\n¿Qué quieres buscar? (o escribe 'salir'): ")
        if q.lower() == "salir":
            break
        if q.strip():
            buscar(q, df_prod, buscador_vectorial)

if __name__ == "__main__":
    ruta = os.path.join("data", "clean", "productos_limpios.csv")
    
    if os.path.exists(ruta):
        df_prod = pd.read_csv(ruta, sep=";")
        consultar(df_prod) 
    else:
        print(f"ERROR: No se encontró el archivo en {ruta}")