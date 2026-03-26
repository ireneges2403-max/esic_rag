import json
import os
import re
import pandas as pd

def limpiar_texto(texto):
    if pd.isna(texto): 
        return ""
    texto = str(texto).lower()
    # Eliminar caracteres especiales y puntuacion
    texto = re.sub(r'[^\w\s]', '', texto) 
    return texto.strip()

def extraer_numero(valor):
    if pd.isna(valor) or str(valor).lower() == "energía" or str(valor).strip() == "": 
        return 0.0
    # Buscar patrones numericos con coma o punto
    match = re.search(r"(\d+([,\.]\d+)?)", str(valor))
    if match:
        return float(match.group(1).replace(',', '.'))
    return 0.0

def limpiar_datos(datos=None):
    ruta_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ruta_raw = os.path.join(ruta_raiz, "data", "raw", "productos.json")
    ruta_clean = os.path.join(ruta_raiz, "data", "clean", "productos_limpios.csv")

    if datos is not None:
        df = pd.DataFrame(datos)
    else:
        if not os.path.exists(ruta_raw):
            print("Error: El archivo fuente productos.json no existe en data/raw/")
            return None
        try:
            with open(ruta_raw, "r", encoding="utf-8") as f:
                df = pd.DataFrame(json.load(f))
        except Exception as e:
            print(f"Error al leer el archivo JSON: {e}")
            return None

    # Eliminacion de duplicados y valores criticos
    df = df.drop_duplicates(subset=['titulo'])
    df = df.dropna(subset=['titulo'])

    # Procesamiento de valores nutricionales
    # Desglosar el diccionario de nutricion
    nutri_df = df['valores_nutricionales_100_g'].apply(pd.Series)
    
    # Funcion interna para procesar columnas de forma segura
    def obtener_columna_limpia(nombre_col):
        if nombre_col in nutri_df.columns:
            return nutri_df[nombre_col].apply(extraer_numero)
        return 0.0

    df['precio'] = df['precio_total'].apply(extraer_numero)
    df['proteinas'] = obtener_columna_limpia('Proteinas')
    df['carbohidratos'] = obtener_columna_limpia('Hidratos de carbono')
    df['grasas'] = obtener_columna_limpia('Grasas')
    df['calories'] = obtener_columna_limpia('Valor energetico')
    
    # Columnas adicionales para calculos internos
    df['azucares'] = obtener_columna_limpia('Azucares')
    df['saturadas'] = obtener_columna_limpia('Saturadas')
    df['sal'] = obtener_columna_limpia('Sal')
    df['fibra'] = obtener_columna_limpia('Fibra')

    # Normalizacion y Enriquecimiento

    # norm_precio: Escalado 0-1 (mas barato = valor mas cercano a 1)
    p_min, p_max = df['precio'].min(), df['precio'].max()
    if p_max > p_min:
        df['norm_precio'] = 1 - ((df['precio'] - p_min) / (p_max - p_min))
    else:
        df['norm_precio'] = 1.0

    # norm_nutri: Score 0-100 basado en proteinas
    prot_max = df['proteinas'].max()
    df['norm_nutri'] = (df['proteinas'] / prot_max * 100) if prot_max > 0 else 0.0

    # score_nutricional: Balance de macronutrientes basado en recompensar proteínas y penalizar elementos restrictivos (azúcares, grasas saturadas y especialmente la sal x2)
    df['score_nutricional'] = df['proteinas'] - (df['azucares'] + df['saturadas'] + (df['sal'] * 2))

    # texto_busqueda: Concatenacion para embeddings
    df['texto_busqueda'] = (
        df['titulo'].apply(limpiar_texto) + " " + 
        df['origen'].apply(limpiar_texto)
    )

    # Seleccion final de columnas segun rubrica
    columnas_finales = [
        'titulo', 'precio', 'proteinas', 'carbohidratos', 'grasas', 
        'fibra', 'calories', 'texto_busqueda', 'norm_precio', 
        'norm_nutri', 'score_nutricional'
    ]
    
    df_output = df[columnas_finales]

    # Exportacion
    os.makedirs(os.path.dirname(ruta_clean), exist_ok=True)
    df_output.to_csv(ruta_clean, index=False, sep=";", encoding="utf-8-sig")

    print("Proceso de preprocesamiento finalizado")
    print(f"Registros finales: {len(df_output)}")
    print(f"Archivo generado en: {ruta_clean}")
    
    # Devolvemos los datos limpios al final para que sigan su camino
    return df_output

if __name__ == "__main__":
    limpiar_datos()