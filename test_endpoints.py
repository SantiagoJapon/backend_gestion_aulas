import requests  # Si ves el error, instala con: pip install requests

def test_endpoints():
    base_url = "http://127.0.0.1:8000"
    
    endpoints = [
        "/api/aulas/",
        "/api/aulas/tipos/",
        "/api/aulas/disponibilidad/",
        "/api/reportes/estadisticas/",
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get("{}{}".format(base_url, endpoint))  # S3457: usa .format en vez de f-string
            print("GET {}: {}".format(endpoint, response.status_code))  # S3457: usa .format
            if response.status_code == 200:
                print("   ✓ Respuesta OK")
            else:
                print("   ✗ Error: {}".format(response.status_code))  # S3457: usa .format
        except requests.exceptions.ConnectionError:
            print("   ✗ No se pudo conectar al servidor")
        print()

if __name__ == "__main__":
    test_endpoints()