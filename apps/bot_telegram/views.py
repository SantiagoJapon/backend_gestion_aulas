from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@api_view(['POST'])
@permission_classes([AllowAny])
def webhook_telegram_view(request):
    """Endpoint básico para el bot de Telegram"""
    
    telegram_user_id = request.data.get('telegram_user_id')
    mensaje = request.data.get('mensaje', '').lower()
    
    if not telegram_user_id or not mensaje:
        return Response({
            'respuesta': 'Error: Faltan datos requeridos',
            'tipo_respuesta': 'error'
        })
    
    # Respuesta básica por ahora
    if 'ayuda' in mensaje or 'help' in mensaje:
        respuesta = """🤖 Bot de Gestión de Aulas

Comandos disponibles:
- ayuda: Mostrar este menú
- hola: Saludo

Próximamente más funciones..."""
    elif 'hola' in mensaje:
        respuesta = "¡Hola! Soy el bot de gestión de aulas. Escribe 'ayuda' para ver los comandos."
    else:
        respuesta = f"Recibí tu mensaje: '{mensaje}'. Escribe 'ayuda' para ver los comandos disponibles."
    
    return Response({
        'respuesta': respuesta,
        'tipo_respuesta': 'general'
    })