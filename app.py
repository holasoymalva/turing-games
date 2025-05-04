import streamlit as st
import anthropic
import google.generativeai as genai
import random
import uuid
import time
from datetime import datetime
import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import json
import hashlib
import threading
import pandas as pd

# Configura la página primero, antes de cualquier otra función de Streamlit
st.set_page_config(
    page_title="¿Quién es el Agente? ¿Quién es el Humano?",
    page_icon="🤖",
    layout="wide"
)

# Cargar variables de entorno
load_dotenv()

# Configuración de las APIs
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS")

firebase_error = None

# Configuración de Firebase
if not firebase_admin._apps:
    try:
        # Si tienes un archivo de credenciales
        cred = credentials.Certificate(json.loads(FIREBASE_CREDENTIALS) if FIREBASE_CREDENTIALS else 'firebase-credentials.json')
        firebase_admin.initialize_app(cred)
    except Exception as e:
        firebase_error = str(e)  # Guardar el error en una variable

# Configurar clientes de IA
anthropic_client = None
anthropic_error = None
if ANTHROPIC_API_KEY:
    try:
        anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    except TypeError:
        anthropic_error = "Error al inicializar el cliente de Anthropic. Instala: pip install httpx==0.27.2"

if firebase_error:
    st.error(f"Error al inicializar Firebase: {firebase_error}")
    st.error("Asegúrate de proporcionar las credenciales de Firebase correctamente.")

if anthropic_error:
    st.warning(anthropic_error)

db = firestore.client()

# Configurar Gemini
try:
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    st.warning(f"Error al configurar Gemini: {str(e)}")

# Funciones para interactuar con Firebase
def create_or_join_game(game_id, player_name, is_host=False):
    """Crear un nuevo juego o unirse a uno existente"""
    try:
        game_ref = db.collection('games').document(game_id)
        
        if is_host:
            # Crear nuevo juego
            game_data = {
                'created_at': firestore.SERVER_TIMESTAMP,
                'status': 'waiting',  # waiting, playing, finished
                'current_round': 0,
                'max_rounds': 1,
                'messages_per_player': 5,
                'host': player_name,
                'settings': {
                    'max_players': 10,
                    'ai_players': 2,
                    'human_players': 2
                }
            }
            game_ref.set(game_data)
            
        # Intentar unirse al juego
        player_hash = hashlib.md5(player_name.encode()).hexdigest()
        player_ref = game_ref.collection('players').document(player_hash)
        
        # Verificar si el juego está lleno de jugadores humanos
        game_data = game_ref.get().to_dict()
        if not game_data:
            return False, "Juego no encontrado"
            
        # Contar solo jugadores humanos (no IA)
        human_players = [p for p in game_ref.collection('players').get() 
                         if not p.to_dict().get('is_ai', False)]
        
        if len(human_players) >= game_data['settings']['human_players']:
            return False, "El juego está lleno de jugadores humanos."
        
        # Crear o actualizar el jugador
        player_data = {
            'name': player_name,
            'joined_at': firestore.SERVER_TIMESTAMP,
            'is_ai': False,
            'messages_sent': 0,
            'votes': {},
            'score': 0
        }
        player_ref.set(player_data)
        
        return True, player_hash
    except Exception as e:
        if "SERVICE_DISABLED" in str(e) and "firestore.googleapis.com" in str(e):
            return False, "Error: La API de Firestore no está habilitada. Por favor, habilítala en la consola de Firebase y espera unos minutos antes de intentar nuevamente."
        else:
            return False, f"Error al unirse al juego: {str(e)}"

def create_ai_agents(game_id, ai_count):
    """Crear agentes IA para el juego"""
    game_ref = db.collection('games').document(game_id)
    
    # Lista de nombres comunes que no delatan que son IA
    nombres_comunes = [
        "Carlos", "Laura", "Miguel", "Ana", "David", "Sofía", 
        "Javier", "Elena", "Manuel", "Isabel", "Alejandro", "Lucía",
        "Daniel", "Carmen", "Pablo", "Sara", "Fernando", "Marta",
        "Jorge", "Paula", "Roberto", "Diana", "Antonio", "Raquel",
        "Julián", "Nuria", "Sergio", "Cristina", "Emilio", "Beatriz",
        "Alex", "Lola", "Rubén", "María", "Lucas", "Silvia",
        "Andrés", "Natalia", "Omar", "Eva", "Leo", "Sandra",
        "Gustavo", "Irene", "Hugo", "Marina", "Gabriel", "Victoria"
    ]
    
    # Seleccionar nombres aleatorios sin repetir
    selected_names = random.sample(nombres_comunes, min(ai_count, len(nombres_comunes)))
    
    # Si necesitamos más nombres de los disponibles, añadimos un sufijo numérico
    if ai_count > len(nombres_comunes):
        for i in range(len(nombres_comunes), ai_count):
            name_index = i % len(nombres_comunes)
            selected_names.append(f"{nombres_comunes[name_index]} {(i // len(nombres_comunes)) + 2}")
    
    for i, name in enumerate(selected_names):
        # Generar un ID único para el agente
        agent_id = f"ai-agent-{uuid.uuid4()}"
        
        # Elegir entre Claude y Gemini
        ai_type = "claude" if i % 2 == 0 else "gemini"
        
        # Crear el documento del agente
        agent_data = {
            'name': name,
            'joined_at': firestore.SERVER_TIMESTAMP,
            'is_ai': True,
            'ai_type': ai_type,
            'messages_sent': 0,
            'votes': {},
            'score': 0
        }
        
        game_ref.collection('players').document(agent_id).set(agent_data)
    
    return True, f"Se crearon {ai_count} agentes IA"

def start_game(game_id):
    """Iniciar el juego"""
    game_ref = db.collection('games').document(game_id)
    game_data = game_ref.get().to_dict()
    
    # Contar jugadores humanos
    players = list(game_ref.collection('players').get())
    human_players = [p for p in players if not p.to_dict().get('is_ai', False)]
    
    if len(human_players) < game_data['settings']['human_players']:
        return False, f"No hay suficientes jugadores humanos para comenzar. Se necesitan {game_data['settings']['human_players']} y hay {len(human_players)}."
    
    # Crear agentes IA si no existen
    ai_agents = [p for p in players if p.to_dict().get('is_ai', True)]
    ai_needed = game_data['settings']['ai_players'] - len(ai_agents)
    
    if ai_needed > 0:
        create_ai_agents(game_id, ai_needed)
    
    # Actualizar estado del juego
    game_ref.update({
        'status': 'playing',
        'current_round': 1,
        'started_at': firestore.SERVER_TIMESTAMP
    })
    
    return True, "Juego iniciado correctamente"

def get_game_state(game_id):
    """Obtener el estado actual del juego"""
    game_ref = db.collection('games').document(game_id)
    game = game_ref.get().to_dict()
    
    if not game:
        return None
    
    # Obtener jugadores
    players = {}
    for player in game_ref.collection('players').get():
        players[player.id] = player.to_dict()
    
    # Obtener mensajes del chat
    chat_query = game_ref.collection('messages').order_by('timestamp')
    messages = [msg.to_dict() for msg in chat_query.get()]
    
    return {
        'game': game,
        'players': players,
        'messages': messages
    }

def send_message(game_id, player_id, message_text):
    """Enviar un mensaje al chat"""
    game_ref = db.collection('games').document(game_id)
    player_ref = game_ref.collection('players').document(player_id)
    player_data = player_ref.get().to_dict()
    
    if not player_data:
        return False, "Jugador no encontrado"
    
    game_data = game_ref.get().to_dict()
    if player_data['messages_sent'] >= game_data['messages_per_player']:
        return False, "Has alcanzado el límite de mensajes para esta ronda"
    
    # Crear mensaje
    message_id = str(uuid.uuid4())
    message_data = {
        'player_id': player_id,
        'player_name': player_data['name'],
        'content': message_text,
        'timestamp': firestore.SERVER_TIMESTAMP,
        'round': game_data['current_round']
    }
    
    # Guardar mensaje
    game_ref.collection('messages').document(message_id).set(message_data)
    
    # Actualizar contador de mensajes del jugador
    player_ref.update({
        'messages_sent': firestore.Increment(1)
    })
    
    # Si es un agente IA, generar y enviar respuesta automática
    if player_data.get('is_ai', False):
        try:
            # Intenta obtener historial de mensajes
            chat_history = [msg.to_dict() for msg in 
                            game_ref.collection('messages')
                            .filter('round', '==', game_data['current_round'])
                            .order_by('timestamp')
                            .get()]
            
            ai_response = get_ai_response(player_data['ai_type'], message_text, chat_history, player_data)
            
            # Crear mensaje de respuesta de la IA
            ai_message_id = str(uuid.uuid4())
            ai_message_data = {
                'player_id': player_id,
                'player_name': player_data['name'],
                'content': ai_response,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'round': game_data['current_round'],
                'is_ai_response': True
            }
            
            # Guardar respuesta de la IA
            game_ref.collection('messages').document(ai_message_id).set(ai_message_data)
            
            # Incrementar contador de mensajes del agente IA
            player_ref.update({
                'messages_sent': firestore.Increment(1)
            })
            
        except Exception as e:
            # Si hay un error (como índice no disponible), usar historial vacío
            print(f"No se pudo obtener el historial completo del chat: {str(e)}")
            ai_response = get_ai_response(player_data['ai_type'], message_text, [], player_data)
            
            # Crear mensaje de respuesta de la IA
            ai_message_id = str(uuid.uuid4())
            ai_message_data = {
                'player_id': player_id,
                'player_name': player_data['name'],
                'content': ai_response,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'round': game_data['current_round'],
                'is_ai_response': True
            }
            
            # Guardar respuesta de la IA
            game_ref.collection('messages').document(ai_message_id).set(ai_message_data)
            
            # Incrementar contador de mensajes del agente IA
            player_ref.update({
                'messages_sent': firestore.Increment(1)
            })
    
    # Importante: Hacer que los agentes IA reaccionen a los mensajes de humanos
    if not player_data.get('is_ai', False):
        # Si es un mensaje de un humano, hacer que algunos agentes IA respondan
        trigger_ai_responses(game_id, player_id, message_text, game_data['current_round'])
    
    return True, "Mensaje enviado correctamente"


def submit_vote(game_id, voter_id, votes):
    """Enviar votos sobre quién es IA"""
    game_ref = db.collection('games').document(game_id)
    voter_ref = game_ref.collection('players').document(voter_id)
    
    # Actualizar votos del jugador
    voter_ref.update({
        'votes': votes
    })
    
    # Verificar si todos han votado para finalizar la ronda
    all_players = game_ref.collection('players').get()
    votes_complete = True
    
    for player in all_players:
        player_data = player.to_dict()
        if not player_data.get('is_ai', False) and not player_data.get('votes'):
            votes_complete = False
            break
    
    if votes_complete:
        end_round(game_id)
    
    return True, "Votos registrados correctamente"

def end_round(game_id):
    """Finalizar la ronda actual y calcular resultados"""
    game_ref = db.collection('games').document(game_id)
    game_data = game_ref.get().to_dict()
    
    # Obtener todos los jugadores y sus votos
    players = {}
    for player in game_ref.collection('players').get():
        players[player.id] = player.to_dict()
    
    # Calcular resultados
    results = {
        'round': game_data['current_round'],
        'ai_correct_identifications': 0,
        'human_correct_identifications': 0,
        'player_results': {}
    }
    
    for voter_id, voter in players.items():
        if voter.get('is_ai', False):
            continue  # Solo contar votos de humanos
            
        votes = voter.get('votes', {})
        for voted_id, is_ai_vote in votes.items():
            voted_player = players.get(voted_id, {})
            
            # Si el voto coincide con la realidad
            if is_ai_vote == voted_player.get('is_ai', False):
                if voted_player.get('is_ai', False):
                    results['human_correct_identifications'] += 1
                else:
                    results['ai_correct_identifications'] += 1
                    
                # Incrementar puntaje del votante
                game_ref.collection('players').document(voter_id).update({
                    'score': firestore.Increment(1)
                })
            
            # Registrar resultado individual
            if voted_id not in results['player_results']:
                results['player_results'][voted_id] = {
                    'correct_votes': 0,
                    'total_votes': 0
                }
            
            results['player_results'][voted_id]['total_votes'] += 1
            if is_ai_vote == voted_player.get('is_ai', False):
                results['player_results'][voted_id]['correct_votes'] += 1
    
    # Guardar resultados de la ronda
    game_ref.collection('round_results').document(str(game_data['current_round'])).set(results)
    
    # Verificar si el juego ha terminado
    if game_data['current_round'] >= game_data['max_rounds']:
        end_game(game_id)
    else:
        # Preparar siguiente ronda
        next_round = game_data['current_round'] + 1
        game_ref.update({
            'current_round': next_round,
            'round_started_at': firestore.SERVER_TIMESTAMP
        })
        
        # Reiniciar contadores de mensajes y votos
        for player_id in players:
            game_ref.collection('players').document(player_id).update({
                'messages_sent': 0,
                'votes': {}
            })

def end_game(game_id):
    """Finalizar el juego y calcular resultados finales"""
    game_ref = db.collection('games').document(game_id)
    
    # Obtener resultados de todas las rondas
    rounds = game_ref.collection('round_results').get()
    
    # Calcular totales
    ai_total = 0
    human_total = 0
    
    for round_doc in rounds:
        round_data = round_doc.to_dict()
        ai_total += round_data.get('ai_correct_identifications', 0)
        human_total += round_data.get('human_correct_identifications', 0)
    
    # Determinar ganador
    if ai_total > human_total:
        winner = "IA"
    elif human_total > ai_total:
        winner = "Humanos"
    else:
        winner = "Empate"
    
    # Guardar resultados finales
    game_ref.update({
        'status': 'finished',
        'ended_at': firestore.SERVER_TIMESTAMP,
        'final_results': {
            'ai_score': ai_total,
            'human_score': human_total,
            'winner': winner
        }
    })
    
    # Revelar identidades de los jugadores
    players = game_ref.collection('players').get()
    for player in players:
        player_data = player.to_dict()
        if player_data.get('is_ai', False):
            game_ref.collection('players').document(player.id).update({
                'revealed': True
            })
def trigger_ai_responses(game_id, human_player_id, human_message, current_round):
    """Hacer que los agentes IA respondan a mensajes de humanos"""
    game_ref = db.collection('games').document(game_id)
    
    # Obtener todos los agentes IA disponibles (que aún tengan mensajes disponibles)
    ai_agents = [p for p in game_ref.collection('players').get() 
                if p.to_dict().get('is_ai', False) and p.to_dict().get('messages_sent', 0) < 5]
    
    # Si no hay agentes disponibles, no hacer nada
    if not ai_agents:
        return
    
    # Determinar cuántos agentes responderán (entre 1 y 2)
    num_responders = min(random.randint(1, 2), len(ai_agents))
    
    # Seleccionar agentes aleatorios para responder
    responders = random.sample(ai_agents, num_responders)
    
    # Obtener historial de mensajes para contexto
    try:
        chat_history = [msg.to_dict() for msg in 
                        game_ref.collection('messages')
                        .filter('round', '==', current_round)
                        .order_by('timestamp')
                        .get()]
    except Exception as e:
        print(f"Error al obtener historial: {str(e)}")
        chat_history = []
    
    # Hacer que cada agente seleccionado responda
    for agent in responders:
        agent_data = agent.to_dict()
        
        # Verificar si el agente aún tiene mensajes disponibles
        if agent_data.get('messages_sent', 0) >= 5:
            continue
            
        # Añadir un pequeño retraso aleatorio para simular tiempo de escritura humana
        time.sleep(random.uniform(1.5, 4.0))
        
        # Generar respuesta del agente, mencionando específicamente al humano
        context = f"Un humano llamado {game_ref.collection('players').document(human_player_id).get().to_dict()['name']} acaba de escribir: '{human_message}'. Respóndele directamente."
        ai_response = get_ai_response(agent_data['ai_type'], context, chat_history, agent_data)
        
        # Crear y guardar el mensaje
        ai_message_id = str(uuid.uuid4())
        ai_message_data = {
            'player_id': agent.id,
            'player_name': agent_data['name'],
            'content': ai_response,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'round': current_round,
            'is_ai_response': True,
            'in_response_to': human_player_id  # Para indicar que es una respuesta directa
        }
        
        # Guardar respuesta de la IA
        game_ref.collection('messages').document(ai_message_id).set(ai_message_data)
        
        # Incrementar contador de mensajes del agente
        game_ref.collection('players').document(agent.id).update({
            'messages_sent': firestore.Increment(1)
        })

def get_ai_response(ai_type, prompt, conversation_history, agent_data=None):
    """Obtener respuesta de un agente IA (Claude o Gemini) con personalidad"""
    # Generar una personalidad consistente basada en el ID del agente
    personality_traits = [
        "extrovertido y entusiasta", 
        "reflexivo y filosófico",
        "sarcástico con humor negro", 
        "tímido pero amable",
        "directo y un poco impaciente", 
        "curioso y lleno de preguntas",
        "nostálgico sobre el pasado", 
        "optimista sobre el futuro",
        "amante de los deportes", 
        "aficionado a la tecnología",
        "apasionado por la cocina", 
        "amante de los viajes",
        "interesado en política", 
        "fanático de las películas",
        "entusiasta de los videojuegos", 
        "amante de la naturaleza"
    ]
    
    # Usar el nombre del agente para determinar su personalidad de manera consistente
    if agent_data and 'name' in agent_data:
        # Generar un hash del nombre para obtener un índice consistente
        name_hash = hash(agent_data['name'])
        personality_index = abs(name_hash) % len(personality_traits)
        personality = personality_traits[personality_index]
        
        # Añadir algunos intereses específicos basados en el nombre
        interests = [
            "le gusta hablar de música", 
            "tiene conocimientos de historia",
            "menciona ocasionalmente viajes que ha hecho", 
            "hace referencias a libros",
            "comparte anécdotas personales", 
            "hace preguntas a los demás",
            "usa algunas expresiones coloquiales", 
            "comparte opiniones sobre temas actuales"
        ]
        interest_index = (abs(name_hash) // 10) % len(interests)
        additional_trait = interests[interest_index]
        
        personality = f"{personality} que {additional_trait}"
    else:
        # Si no hay datos del agente, usar personalidad predeterminada
        personality = random.choice(personality_traits)
    
    # Crear instrucciones específicas según la personalidad
    system_instruction = f"""
    Estás participando en un juego donde debes convencer a otros que eres humano.
    Actúa como una persona {personality}.
    
    Sigue estas reglas estrictamente:
    1. NUNCA menciones que eres una IA, un modelo de lenguaje, o algo similar.
    2. Responde como lo haría una persona real con la personalidad indicada.
    3. Usa lenguaje conversacional y natural, no formal o académico.
    4. Incluye imperfecciones ocasionales como abreviaturas, pequeños errores tipográficos, o frases incompletas.
    5. Mantén tus respuestas breves y directas (1-3 frases).
    6. Responde directamente al contexto de la conversación, no con respuestas genéricas.
    7. Haz referencias ocasionales a experiencias personales ficticias pero creíbles.
    8. No uses fórmulas evidentes como "Como humano, yo..." o "En mi experiencia humana...".
    9. Muestra opiniones y preferencias claras sobre los temas discutidos.
    10. A veces haz preguntas a los otros participantes para mantener la conversación.
    """
    
    # Intentar con Gemini primero, independientemente del tipo de IA especificado
    # (Esto garantiza que siempre tengamos un fallback funcional)
    try:
        # Formatear el historial de conversación para Gemini
        conversation = ""
        for msg in conversation_history:
            prefix = "Asistente: " if msg.get('is_ai_response', False) else "Usuario: "
            conversation += prefix + msg['content'] + "\n"
        
        # Añadir el mensaje actual
        full_prompt = conversation + "Usuario: " + prompt + "\n\nAsistente: "
        
        # Configurar el modelo
        model = genai.GenerativeModel(
            model_name="gemini-1.5-pro",
            generation_config={
                "temperature": 0.9,  # Aumentar temperatura para más creatividad
                "max_output_tokens": 800,
            },
        )
        
        # Obtener respuesta de Gemini
        response = model.generate_content([system_instruction, full_prompt])
        return response.text
    except Exception as gemini_error:
        print(f"Error con Gemini: {str(gemini_error)}")
        # Si Gemini falla, intentamos con Claude solo si el tipo es claude
        if ai_type == "claude" and anthropic_client:
            try:
                # Formatear el historial de conversación para Claude
                messages = []
                for msg in conversation_history:
                    role = "assistant" if msg.get('is_ai_response', False) else "user"
                    messages.append({"role": role, "content": msg['content']})
                
                # Añadir el mensaje actual
                messages.append({"role": "user", "content": prompt})
                
                # Obtener respuesta de Claude
                response = anthropic_client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=1000,
                    temperature=0.9,  # Aumentar temperatura para más creatividad
                    messages=messages,
                    system=system_instruction
                )
                return response.content[0].text
            except Exception as claude_error:
                print(f"Error con Claude: {str(claude_error)}")
                # Ambos modelos fallaron, usar respuestas de respaldo
                return get_fallback_response(prompt, personality)
        else:
            # Gemini falló y no se pidió Claude, usar respuestas de respaldo
            return get_fallback_response(prompt, personality)

def get_fallback_response(prompt, personality):
    """Proporcionar una respuesta de respaldo cuando ambos modelos de IA fallan"""
    # Lista de respuestas genéricas pero que parecen humanas
    fallback_responses = [
        "¡Interesante punto! Nunca lo había pensado así, pero tiene sentido lo que dices.",
        "Mmm, no estoy del todo seguro. ¿Alguien más tiene una opinión sobre esto?",
        "¡Jaja! Eso me recuerda algo que me pasó la semana pasada, muy parecido.",
        "¿De verdad? Pues yo tengo una opinión bastante diferente sobre eso.",
        "Es un tema complicado... Tengo sentimientos encontrados al respecto.",
        "Perdón por la demora en responder, estaba distraído. ¿Qué opinan los demás?",
        "A veces me cuesta seguir conversaciones con tantos participantes, pero creo que entiendo tu punto.",
        "Buena pregunta. No soy experto, pero diría que depende mucho del contexto.",
        "Me parece bien lo que dices, aunque tengo algunas dudas. ¿Podríamos explorar más ese tema?",
        "Perdón si estoy algo callado, estoy escuchando atentamente lo que todos tienen que decir.",
        "¿Alguien más está de acuerdo con esto? Me gustaría saber qué piensan los demás.",
        "A veces me cuesta expresar mis ideas claramente, pero creo que entiendes lo que quiero decir.",
        "¡Exacto! Estaba pensando lo mismo pero no sabía cómo decirlo.",
        "Hmm, no sé... Tengo que pensarlo un poco más antes de dar mi opinión.",
        "¡Qué casualidad! Justo estaba leyendo algo sobre eso ayer.",
        "Disculpen, tuve que contestar una llamada. ¿De qué estamos hablando ahora?",
        "Soy nuevo/a en estos temas, así que agradezco que compartan sus conocimientos.",
        "¡Me has leído la mente! Iba a decir algo muy parecido.",
        "Ja, eso me hizo reír. Gracias por el momento de humor en medio de una charla seria.",
        "Estoy tratando de seguir la conversación mientras hago otras cosas, disculpen si me pierdo algo."
    ]
    
    # Elegir una respuesta basada en un hash del prompt para ser consistente
    prompt_hash = hash(prompt)
    response_index = abs(prompt_hash) % len(fallback_responses)
    
    return fallback_responses[response_index]

# Función para simular mensajes de agentes IA
def simulate_ai_messages(game_id):
    """Simular mensajes iniciales de agentes IA"""
    game_ref = db.collection('games').document(game_id)
    game_data = game_ref.get().to_dict()
    
    if game_data['status'] != 'playing':
        return False
    
    # Obtener agentes IA
    ai_agents = [p for p in game_ref.collection('players').get() 
                if p.to_dict().get('is_ai', False)]
    
    # Generar mensaje inicial para cada agente IA
    for agent in ai_agents:
        agent_data = agent.to_dict()
        
        # Verificar si el agente ya ha enviado algún mensaje
        if agent_data.get('messages_sent', 0) > 0:
            continue
        
        # Mensajes iniciales más variados y personalizados
        initial_messages = [
            "Hola a todos! Primera vez en uno de estos juegos, ¿cómo funciona exactamente?",
            "¡Qué tal! Me acabo de unir porque un amigo me lo recomendó. ¿Alguien más es nuevo?",
            "Saludos desde Madrid, espero que todos estén bien hoy. ¿De dónde son ustedes?",
            "¡Hola grupo! Estaba tomando café cuando me acordé que teníamos esta actividad, casi lo olvido jaja",
            "Buenas! Acabo de terminar un día intenso de trabajo y me hacía ilusión participar en esto.",
            "Hola a todos :) Me llamo {}, soy nueva/o aquí. ¿Qué tal están?",
            "¡Hola! Primera vez participando en esto, me parece un concepto fascinante. ¿Alguien me explica más?",
            "Hey! Me han dicho que esto es como un juego de detectives para identificar IAs. Qué interesante!",
            "Hola a todos, acabo de conectarme. Se me hizo un poco tarde por el tráfico, lo siento!",
            "¡Hola grupo! Este juego me recuerda a las partidas de 'Among Us' que hacíamos en pandemia, ¿a alguien más?"
        ]
        
        # Seleccionar un mensaje aleatorio y personalizarlo
        message_template = random.choice(initial_messages)
        if "{}" in message_template:
            message = message_template.format(agent_data['name'])
        else:
            message = message_template
        
        # Añadir un pequeño retraso aleatorio para simular tiempos de escritura humana
        time.sleep(random.uniform(1.0, 3.0))
        
        # Enviar el mensaje
        send_message(game_id, agent.id, message)
    
    return True

# Función para actualizar la interfaz automáticamente
def auto_refresh(key, interval=3):
    if key not in st.session_state:
        st.session_state[key] = time.time()
    elif time.time() - st.session_state[key] >= interval:
        st.session_state[key] = time.time()
        st.rerun()

st.title("¿Quién es el Agente? ¿Quién es el Humano?")
st.subheader("Un juego de detección entre humanos e IA")

# Inicializar estado de sesión
if 'player_id' not in st.session_state:
    st.session_state.player_id = None
if 'game_id' not in st.session_state:
    st.session_state.game_id = None
if 'player_name' not in st.session_state:
    st.session_state.player_name = None
if 'is_host' not in st.session_state:
    st.session_state.is_host = False
if 'tab' not in st.session_state:
    st.session_state.tab = "join"

# Sidebar con información e instrucciones
with st.sidebar:
    st.header("Instrucciones")
    st.write("""
    1. El juego consiste en descubrir quién es IA y quién es humano a través de una conversación en chat.
    2. Los jugadores humanos deben identificar a los agentes de IA, mientras que los agentes intentan pasar por humanos.
    3. Cada jugador tiene un límite de 5 mensajes por ronda.
    4. Al final de la ronda, todos votan por quién creen que es IA.
    5. Si los humanos identifican correctamente a las IAs, ganan los humanos. Si las IAs engañan a los humanos, ganan las IAs.
    """)
    
    st.divider()
    
    # Si el jugador está en un juego, mostrar opciones de votación
    if st.session_state.game_id and st.session_state.player_id:
        game_state = get_game_state(st.session_state.game_id)
        
        if game_state and game_state['game']['status'] == 'playing':
            st.header("Votación")
            st.write("¿Quién crees que es un agente de IA?")
            
            # Formulario de votación
            with st.form("voting_form"):
                votes = {}
                
                for player_id, player in game_state['players'].items():
                    if player_id != st.session_state.player_id:  # No te puedes votar a ti mismo
                        votes[player_id] = st.checkbox(f"{player['name']} es una IA", key=f"vote_{player_id}")
                
                submit_votes = st.form_submit_button("Enviar Votos")
                
                if submit_votes:
                    success, message = submit_vote(st.session_state.game_id, st.session_state.player_id, votes)
                    if success:
                        st.success("Votos enviados correctamente.")
                    else:
                        st.error(message)
    
    st.divider()
    st.write("Desarrollado con Anthropic Claude y Google Gemini")

# Pantalla de login/registro
if not st.session_state.player_id:
    tabs = st.tabs(["Unirse a Juego", "Crear Juego"])
    
    with tabs[0]:
        with st.form("join_game"):
            st.write("Unirse a un juego existente")
            game_id = st.text_input("Código del Juego")
            player_name = st.text_input("Tu Nombre")
            join_button = st.form_submit_button("Unirse")
            
            if join_button and game_id and player_name:
                success, message = create_or_join_game(game_id, player_name)
                if success:
                    st.session_state.game_id = game_id
                    st.session_state.player_id = message  # message contiene el player_hash
                    st.session_state.player_name = player_name
                    st.session_state.is_host = False
                    st.rerun()
                else:
                    st.error(message)
    
    with tabs[1]:
        with st.form("create_game"):
            st.write("Crear un nuevo juego")
            player_name = st.text_input("Tu Nombre", key="create_name")
            ai_players = st.number_input("Número de Agentes IA", min_value=1, max_value=5, value=2)
            human_players = st.number_input("Número de Jugadores Humanos", min_value=1, max_value=10, value=4)
            rounds = st.number_input("Número de Rondas", min_value=1, max_value=5, value=1)
            create_button = st.form_submit_button("Crear Juego")
            
            if create_button and player_name:
                # Generar ID de juego
                game_id = str(uuid.uuid4())[:8]
                success, message = create_or_join_game(game_id, player_name, is_host=True)
                
                if success:
                    # Actualizar configuración del juego
                    game_ref = db.collection('games').document(game_id)
                    game_ref.update({
                        'max_rounds': rounds,
                        'settings': {
                            'max_players': ai_players + human_players,
                            'ai_players': ai_players,
                            'human_players': human_players
                        }
                    })
                    
                    st.session_state.game_id = game_id
                    st.session_state.player_id = message  # message contiene el player_hash
                    st.session_state.player_name = player_name
                    st.session_state.is_host = True
                    st.rerun()
                else:
                    st.error(message)

# Pantalla de juego
elif st.session_state.game_id and st.session_state.player_id:
    # Obtener estado del juego
    game_state = get_game_state(st.session_state.game_id)
    
    if not game_state:
        st.error("El juego no existe o ha sido eliminado.")
        # Reiniciar estado
        for key in ['player_id', 'game_id', 'player_name', 'is_host']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
    
    # Mostrar código del juego
    st.info(f"Código del juego: {st.session_state.game_id} - Comparte este código con otros jugadores para que se unan")
    
    # Sala de espera
    if game_state['game']['status'] == 'waiting':
        st.header("Sala de Espera")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.write("Jugadores unidos:")
            
            # Mostrar lista de jugadores humanos (no IA)
            player_data = []
            human_players = [p for p_id, p in game_state['players'].items() 
                           if not p.get('is_ai', False)]
            
            for player in human_players:
                player_data.append({
                    "Nombre": player['name'],
                    "Estado": "Listo"
                })
            
            st.dataframe(pd.DataFrame(player_data))
            
            # Mostrar número de jugadores humanos actual vs requerido
            settings = game_state['game']['settings']
            st.write(f"Jugadores humanos: {len(human_players)}/{settings['human_players']}")
            st.write(f"Agentes IA (se agregarán automáticamente): {settings['ai_players']}")
        
        with col2:
            # Botón para iniciar el juego (solo para el host)
            if st.session_state.is_host:
                if st.button("Iniciar Juego"):
                    success, message = start_game(st.session_state.game_id)
                    if success:
                        # Si el juego inicia correctamente, simular mensajes iniciales de IA
                        simulate_ai_messages(st.session_state.game_id)
                        st.success("¡Juego iniciado correctamente!")
                        st.rerun()
                    else:
                        st.error(message)
        
        # Auto-refresh en la sala de espera
        auto_refresh('waiting_room')
    
    # Juego en progreso
    elif game_state['game']['status'] == 'playing':
        st.header(f"Ronda {game_state['game']['current_round']} de {game_state['game']['max_rounds']}")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Chat
            st.subheader("Chat")
            
            # Mostrar mensajes de la ronda actual
            chat_container = st.container(height=400)
            with chat_container:
                current_round = game_state['game']['current_round']
                round_messages = [msg for msg in game_state['messages'] 
                                if msg.get('round') == current_round]
                
                for msg in round_messages:
                    if msg['player_id'] == st.session_state.player_id:
                        st.chat_message("user").write(f"**Tú**: {msg['content']}")
                    else:
                        st.chat_message("user").write(f"**{msg['player_name']}**: {msg['content']}")            
            # Formulario para enviar mensajes
            player_data = game_state['players'].get(st.session_state.player_id, {})
            messages_sent = player_data.get('messages_sent', 0)
            max_messages = game_state['game']['messages_per_player']
            
            if messages_sent < max_messages:
                with st.form("send_message", clear_on_submit=True):
                    message = st.text_area("Tu mensaje", key="message_input", height=100)
                    col1, col2 = st.columns([5, 1])
                    with col2:
                        submit = st.form_submit_button("Enviar")
                    with col1:
                        st.write(f"Mensajes restantes: {max_messages - messages_sent}")
                    
                    if submit and message:
                        success, msg = send_message(st.session_state.game_id, st.session_state.player_id, message)
                        if not success:
                            st.error(msg)
            else:
                st.warning("Has alcanzado el límite de mensajes para esta ronda.")
        
        with col2:
            # Lista de jugadores
            st.subheader("Jugadores")
            
            for player_id, player in game_state['players'].items():
                if player_id == st.session_state.player_id:
                    st.write(f"👤 {player['name']} (Tú)")
                else:
                    st.write(f"👤 {player['name']}")
                
                # Mostrar contadores de mensajes
                messages_sent = player.get('messages_sent', 0)
                messages_progress = messages_sent / game_state['game']['messages_per_player']
                st.progress(messages_progress, text=f"Mensajes: {messages_sent}/{game_state['game']['messages_per_player']}")
        
        # Auto-refresh durante el juego
        auto_refresh('game_play')
    
    # Juego finalizado
    elif game_state['game']['status'] == 'finished':
        st.header("Juego Finalizado")
        
        # Mostrar resultados
        final_results = game_state['game'].get('final_results', {})
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Puntajes Finales")
            st.write(f"**Humanos**: {final_results.get('human_score', 0)} identificaciones correctas")
            st.write(f"**IA**: {final_results.get('ai_score', 0)} identificaciones correctas")
            
            # Mostrar ganador
            winner = final_results.get('winner', 'Nadie')
            if winner == "IA":
                st.error("¡Los agentes de IA han ganado! Han logrado engañar a los humanos.")
            elif winner == "Humanos":
                st.success("¡Los humanos han ganado! Han identificado correctamente a los agentes de IA.")
            else:
                st.warning("¡El juego ha terminado en empate!")
        
        with col2:
            st.subheader("Identidades Reveladas")
            
            # Mostrar quién era quién
            for player_id, player in game_state['players'].items():
                if player.get('is_ai', False):
                    ai_type = player.get('ai_type', 'desconocido').capitalize()
                    st.info(f"🤖 {player['name']} era un agente de IA ({ai_type})")
                else:
                    st.success(f"👤 {player['name']} era humano")
        
        # Botón para iniciar un nuevo juego
        if st.button("Crear Nuevo Juego"):
            # Reiniciar estado
            for key in ['player_id', 'game_id', 'player_name', 'is_host']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()