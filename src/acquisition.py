import json
import os
import time
import re
from bs4 import BeautifulSoup

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("Error: Faltan librerías. Ejecute: pip install selenium webdriver-manager beautifulsoup4")
    exit()

def obtener_datos_eroski_profesional():
    print("Iniciando extracción...")
    
    lista_final = []
    objetivo = 210
    
    urls_busqueda = [
        "https://supermercado.eroski.es/es/search/results/?q=cereales",
        "https://supermercado.eroski.es/es/search/results/?q=leche",
        "https://supermercado.eroski.es/es/search/results/?q=galletas",
        "https://supermercado.eroski.es/es/search/results/?q=pasta",
        "https://supermercado.eroski.es/es/search/results/?q=yogur",
        "https://supermercado.eroski.es/es/search/results/?q=arroz",
        "https://supermercado.eroski.es/es/search/results/?q=huevos",
        "https://supermercado.eroski.es/es/search/results/?q=queso",
        "https://supermercado.eroski.es/es/search/results/?q=atun",
        "https://supermercado.eroski.es/es/search/results/?q=pan",
        "https://supermercado.eroski.es/es/search/results/?q=legumbres"
    ]
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    
    # Optimización crítica: Desactivación de carga de imágenes
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    
    # Identidad de navegador profesional
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        for url in urls_busqueda:
            if len(lista_final) >= objetivo:
                break
                
            print(f"Escaneando categoría: {url.split('q=')[1].upper()}")
            driver.get(url)
            time.sleep(2.5) 
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            enlaces_productos = []
            for a in soup.find_all('a', href=True):
                if '/es/productdetail/' in a['href']:
                    link = "https://supermercado.eroski.es" + a['href'] if not a['href'].startswith('http') else a['href']
                    if link not in enlaces_productos:
                        enlaces_productos.append(link)
            
            for enlace in enlaces_productos:
                if len(lista_final) >= objetivo:
                    break
                    
                try:
                    driver.get(enlace)
                    # El tiempo de espera se reduce ya que no cargamos imágenes
                    time.sleep(1.2) 
                    
                    s_det = BeautifulSoup(driver.page_source, 'html.parser')
                    titulo_elem = s_det.find('h1')
                    if not titulo_elem:
                        continue
                    titulo = titulo_elem.text.strip().upper()
                        
                    # Extracción mediante metadatos JSON-LD
                    precio_total = 0.0
                    scripts = s_det.find_all('script', type='application/ld+json')
                    for script in scripts:
                        if script.string:
                            try:
                                datos = json.loads(script.string)
                                items = datos if isinstance(datos, list) else [datos]
                                for item in items:
                                    if item.get('@type') == 'Product' and 'offers' in item:
                                        precio_total = float(item['offers'].get('price', 0.0))
                            except:
                                pass
                    
                    if precio_total == 0.0:
                        continue
                    
                    # Extracción de valores nutricionales
                    nutri = {k: "0 gr" for k in ["Grasas", "Saturadas", "Hidratos de carbono", "Azucares", "Proteinas", "Sal"]}
                    nutri["Valor energetico"] = "0 kcal"
                    
                    textos = s_det.get_text(separator='|', strip=True).split('|')
                    for i, t in enumerate(textos):
                        t_l = t.lower()
                        if i + 1 < len(textos):
                            v = textos[i+1].lower()
                            if 'kcal' in t_l or 'kilocaloría' in t_l: nutri['Valor energetico'] = v.replace('kilocaloría it (international table)', 'kcal').strip()
                            elif t_l == 'grasas': nutri['Grasas'] = v
                            elif 'ácidos grasos saturados' in t_l: nutri['Saturadas'] = v
                            elif 'hidratos de carbono' in t_l: nutri['Hidratos de carbono'] = v
                            elif 'azúcares' in t_l: nutri['Azucares'] = v
                            elif 'proteínas' in t_l: nutri['Proteinas'] = v
                            elif t_l == 'sal': nutri['Sal'] = v
                                    
                    lista_final.append({
                        "url": enlace,
                        "titulo": titulo,
                        "valores_nutricionales_100_g": nutri,
                        "precio_total": precio_total,
                        "origen": "Eroski"
                    })
                    print(f"Registro exitoso: {titulo[:30]}... [{precio_total} EUR] ({len(lista_final)}/{objetivo})")
                    
                except Exception:
                    continue
                    
    finally:
        driver.quit()

    ruta_archivo = os.path.join(os.getcwd(), "data", "raw", "productos.json")
    os.makedirs(os.path.dirname(ruta_archivo), exist_ok=True)
    with open(ruta_archivo, "w", encoding="utf-8") as f:
        json.dump(lista_final, f, indent=2, ensure_ascii=False)
        
    print(f"Proceso concluido. Archivo generado en: {ruta_archivo}")

if __name__ == "__main__":
    obtener_datos_eroski_profesional()