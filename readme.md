# Turing Games: ¿Quién es el Agente? ¿Quién es el Humano?

Este proyecto implementa un juego de estilo Turing donde múltiples jugadores humanos interactúan con agentes de IA (Claude de Anthropic y Gemini de Google) a través de una interfaz de chat en tiempo real, intentando determinar quién es humano y quién es un agente de IA.

## Características

- **Multijugador en Tiempo Real**: Cada jugador puede unirse desde su propio dispositivo
- **Chat en Tiempo Real**: Comunicación sincronizada entre todos los participantes
- **Integración con APIs de IA**: Utiliza Anthropic Claude y Google Gemini para los agentes
- **Sistema de Rondas y Votación**: Mecánica para identificar quién es IA y quién es humano
- **Sincronización con Firebase**: Backend para manejar datos entre múltiples dispositivos
- **Interfaz Responsive**: Diseñada para funcionar en diferentes tamaños de pantalla

## Requisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)
- Claves API para:
  - Anthropic Claude 
  - Google Gemini
- Credenciales de Firebase

## Configuración del Entorno

### 1. Clonar el Repositorio

```bash
git clone https://github.com/holasoymalva/turing-games.git
cd turing-games
```

### 2. Crear un Entorno Virtual

Para Windows:
```bash
# Crear el entorno virtual
python -m venv venv

# Activar el entorno virtual
venv\Scripts\activate
```

Para macOS/Linux:
```bash
# Crear el entorno virtual
python3 -m venv venv

# Activar el entorno virtual
source venv/bin/activate
```

### 3. Instalar Dependencias

Con el entorno virtual activado:
```bash
pip install -r requirements.txt
```

### 4. Configurar Firebase

Sigue las instrucciones detalladas en el archivo `FIREBASE_SETUP.md` para configurar Firebase como backend para el juego.

### 5. Configurar Variables de Entorno

Crea un archivo `.env` en el directorio raíz con el siguiente contenido:

```
ANTHROPIC_API_KEY=tu_clave_api_anthropic
GEMINI_API_KEY=tu_clave_api_gemini
FIREBASE_CREDENTIALS={"type":"service_account","project_id":"tu-proyecto",...}
```

Alternativamente, coloca el archivo `firebase-credentials.json` en el directorio del proyecto.

## Ejecución

Para iniciar la aplicación (con el entorno virtual activado):

```bash
streamlit run app.py
```

La aplicación se abrirá en tu navegador web (generalmente en http://localhost:8501).

## Cómo Jugar

### Crear un Nuevo Juego

1. Cuando inicies la aplicación, selecciona la pestaña "Crear Juego"
2. Ingresa tu nombre
3. Configura el número de agentes IA y jugadores humanos
4. Define el número de rondas
5. Haz clic en "Crear Juego"
6. Comparte el código del juego con otros jugadores

### Unirse a un Juego Existente

1. Selecciona la pestaña "Unirse a Juego"
2. Ingresa el código del juego proporcionado por el anfitrión
3. Ingresa tu nombre
4. Haz clic en "Unirse"

### Durante el Juego

1. **Fase de Chat**: 
   - Cada jugador puede enviar hasta 5 mensajes por ronda
   - Los agentes IA (asignados aleatoriamente) responderán automáticamente, fingiendo ser humanos
   - Intenta determinar quién es IA y quién es humano basándote en las respuestas

2. **Fase de Votación**:
   - En la barra lateral, selecciona quién crees que es un agente de IA
   - Envía tus votos

3. **Resultados**:
   - Si los humanos identifican correctamente a los agentes, ganan los humanos
   - Si los agentes engañan a los humanos, ganan las IA

## Estructura del Proyecto

```
agente-humano-multiplayer/
│
├── app.py                     # Aplicación principal
├── .env                       # Variables de entorno (claves API)
├── requirements.txt           # Dependencias del proyecto
├── README.md                  # Este archivo
├── FIREBASE_SETUP.md          # Instrucciones para configurar Firebase
├── firebase-credentials.json  # Credenciales de Firebase (no incluido en el repositorio)
└── venv/                      # Entorno virtual (generado al configurar)
```

## Obtención de Claves API

### Anthropic Claude
Para obtener una clave API de Anthropic:
1. Regístrate en [console.anthropic.com](https://console.anthropic.com)
2. En la consola, ve a "API Keys" y crea una nueva clave
3. Copia la clave y añádela al archivo `.env`

### Google Gemini
Para obtener una clave API de Google Gemini:
1. Visita [AI Studio](https://aistudio.google.com)
2. Crea una cuenta o inicia sesión
3. Ve a "Get API key" en la barra lateral
4. Copia la clave y añádela al archivo `.env`

## Solución de Problemas

### Errores con Firebase

- **Error al inicializar Firebase**: Verifica que las credenciales sean correctas y que el formato JSON sea válido.
- **Error "Permission denied"**: Asegúrate de que las reglas de seguridad de Firestore permitan lectura y escritura.

### Errores con las APIs de IA

- **Error con Anthropic**: Si ves un error relacionado con `proxies`, asegúrate de tener instalada la versión correcta de httpx: `pip install httpx==0.27.2`.
- **Error con Gemini**: Verifica que la clave API sea válida y que tengas conexión a internet.

## Despliegue para Acceso Público

Para permitir que los jugadores accedan desde diferentes ubicaciones:

### Usando Streamlit Sharing

1. Sube tu código a GitHub
2. Visita [streamlit.io/sharing](https://streamlit.io/sharing) para desplegar la aplicación
3. Asegúrate de configurar las variables de entorno en la plataforma

### Usando Ngrok (para pruebas)

1. Instala ngrok: `pip install pyngrok`
2. Inicia tu aplicación Streamlit: `streamlit run app.py`
3. En otra terminal, ejecuta: `ngrok http 8501`
4. Comparte la URL que proporciona ngrok

## Personalización

Puedes personalizar varios aspectos del juego:

- Modifica las instrucciones a las IAs en las funciones `get_ai_response`
- Ajusta el número máximo de mensajes por jugador en la variable `messages_per_player`
- Personaliza la interfaz de usuario modificando los elementos de Streamlit

## Contribuir

Si deseas contribuir a este proyecto:

1. Haz un fork del repositorio
2. Crea una rama para tu funcionalidad (`git checkout -b feature/nueva-funcionalidad`)
3. Haz commit de tus cambios (`git commit -m 'Añade nueva funcionalidad'`)
4. Haz push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## Licencia

Este proyecto está bajo la licencia MIT. Consulta el archivo LICENSE para obtener más detalles.
