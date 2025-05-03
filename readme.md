# Juego de Identificación: ¿Agente o Humano?

Este proyecto implementa un juego de estilo Turing donde jugadores humanos interactúan con agentes de IA (Claude de Anthropic y Gemini de Google) a través de una interfaz de chat, intentando determinar quién es humano y quién es un agente de IA.

## Características

- Interfaz web creada con Streamlit
- Integración con APIs de Anthropic (Claude) y Google (Gemini)
- Sistema de rondas de conversación y votación
- Puntuación para los jugadores humanos
- Estadísticas de detección por ronda
- Revelación de identidades al final del juego

## Requisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)
- Claves API para:
  - Anthropic Claude 
  - Google Gemini

## Configuración del Entorno

### 1. Clonar el Repositorio

```bash
git clone https://github.com/tu-usuario/agente-humano-juego.git
cd agente-humano-juego
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

### 4. Configurar Variables de Entorno

Crea un archivo `.env` en el directorio raíz:
```bash
# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

Edita el archivo `.env` con tus claves API:
```
ANTHROPIC_API_KEY=tu_clave_api_anthropic
GEMINI_API_KEY=tu_clave_api_gemini
```

Si no tienes un archivo `.env.example`, crea el archivo `.env` directamente y añade las líneas anteriores.

## Ejecución

Para iniciar la aplicación (con el entorno virtual activado):

```bash
streamlit run app.py
```

La aplicación se abrirá en tu navegador web (generalmente en http://localhost:8501).

## Cómo Jugar

1. **Configuración del juego**: Define el número de jugadores humanos, agentes IA y rondas.

2. **Durante cada ronda**: 
   - Los jugadores humanos escriben mensajes en el chat.
   - Los agentes IA responden automáticamente, intentando parecer humanos.
   - Todos los jugadores humanos votan quién creen que es IA y quién es humano.

3. **Al final de cada ronda**:
   - Se calculan los puntos por aciertos.
   - Se avanza a la siguiente ronda.

4. **Al final del juego**:
   - Se revelan las identidades de todos los jugadores.
   - Se muestra la puntuación final.
   - Se comparten estadísticas sobre la detección.

## Estructura del Proyecto

```
agente-humano-juego/
│
├── app.py                 # Aplicación principal
├── .env                   # Variables de entorno (claves API)
├── requirements.txt       # Dependencias del proyecto
├── README.md              # Este archivo
└── venv/                  # Entorno virtual (generado al configurar)
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

### Errores de Entorno Virtual

Si encuentras problemas con el entorno virtual:

- **El comando `venv` no se reconoce**: Asegúrate de tener instalado el módulo `venv`:
  ```bash
  pip install virtualenv
  ```

- **Problemas de permisos en macOS/Linux**: Intenta con:
  ```bash
  chmod +x venv/bin/activate
  ```

- **Problemas al activar en Windows PowerShell**: Si tienes restricciones de ejecución, ejecuta:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

### Errores de API

- **Errores de autenticación**: Verifica que las claves API en el archivo `.env` sean correctas y actuales.
- **Errores de cuota**: Las APIs gratuitas suelen tener límites. Consulta tu plan en las respectivas consolas de desarrollador.

## Desactivar el Entorno Virtual

Cuando termines de trabajar en el proyecto:

```bash
# Windows/macOS/Linux
deactivate
```

## Personalización

Puedes personalizar varios aspectos del juego:
- Modifica las instrucciones a las IAs en las funciones `get_claude_response` y `get_gemini_response`
- Ajusta el número máximo de jugadores y rondas
- Personaliza la interfaz de usuario modificando los elementos de Streamlit

## Implementación en Producción

Para un despliegue en producción, considera:

1. **Hosting de Streamlit**: 
   - [Streamlit Sharing](https://streamlit.io/sharing)
   - [Heroku](https://heroku.com)
   - [AWS](https://aws.amazon.com)

2. **Gestión de Secretos**:
   - Usa servicios de gestión de secretos como AWS Secrets Manager o GitHub Secrets
   - No incluyas el archivo `.env` en el control de versiones

3. **Base de Datos**:
   - Integra una base de datos para persistencia (SQLite, PostgreSQL, MongoDB)

## Limitaciones Actuales

- La implementación actual asume que todos los jugadores humanos están en el mismo dispositivo
- Para un uso real, necesitarías implementar autenticación de usuarios
- En una implementación completa, cada humano tendría su propia sesión

## Contribuir

Si deseas contribuir a este proyecto:

1. Haz un fork del repositorio
2. Crea una rama para tu funcionalidad (`git checkout -b feature/nueva-funcionalidad`)
3. Haz commit de tus cambios (`git commit -m 'Añade nueva funcionalidad'`)
4. Haz push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## Licencia

Este proyecto está bajo la licencia MIT. Consulta el archivo LICENSE para obtener más detalles.

---

Este proyecto fue creado como una demostración de las capacidades de las APIs de Anthropic Claude y Google Gemini para simular conversaciones humanas.