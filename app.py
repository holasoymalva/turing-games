import streamlit as st
import anthropic
import google.generativeai as genai
import random
import uuid
import time
from datetime import datetime
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de las APIs
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configurar clientes
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)

# Inicializar estado de sesión
if 'game_id' not in st.session_state:
    st.session_state.game_id = str(uuid.uuid4())
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'current_players' not in st.session_state:
    st.session_state.current_players = {}
if 'game_in_progress' not in st.session_state:
    st.session_state.game_in_progress = False
if 'round_count' not in st.session_state:
    st.session_state.round_count = 0
if 'max_rounds' not in st.session_state:
    st.session_state.max_rounds = 5
if 'votes' not in st.session_state:
    st.session_state.votes = {}
if 'round_results' not in st.session_state:
    st.session_state.round_results = []

# Funciones para interactuar con los modelos de IA
def get_claude_response(prompt, conversation_history):
    try:
        # Formatear el historial de conversación para Claude
        messages = []
        for msg in conversation_history:
            role = "assistant" if msg["is_ai"] else "user"
            messages.append({"role": role, "content": msg["message"]})
        
        # Añadir el mensaje actual
        messages.append({"role": "user", "content": prompt})
        
        # Obtener respuesta de Claude
        response = anthropic_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=1000,
            messages=messages,
            system="Estás participando en un juego donde debes convencer a otros que eres humano. Responde de manera natural, con pequeñas imperfecciones ocasionales y evita patrones obvios. No menciones que eres una IA. Actúa como si fueras un humano real participando en una conversación. Sé breve y natural en tus respuestas."
        )
        return response.content[0].text
    except Exception as e:
        st.error(f"Error al comunicarse con Claude: {str(e)}")
        return "Lo siento, no pude procesar tu mensaje en este momento."

def get_gemini_response(prompt, conversation_history):
    try:
        # Formatear el historial de conversación para Gemini
        conversation = ""
        for msg in conversation_history:
            prefix = "Asistente: " if msg["is_ai"] else "Usuario: "
            conversation += prefix + msg["message"] + "\n"
        
        # Añadir el mensaje actual
        full_prompt = conversation + "Usuario: " + prompt + "\n\nAsistente: "
        
        # Configurar el modelo
        model = genai.GenerativeModel(
            model_name="gemini-1.5-pro",
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 800,
            },
        )
        
        # Sistema de instrucciones
        system_instruction = """
        Estás participando en un juego donde debes convencer a otros que eres humano.
        Responde de manera natural, con pequeñas imperfecciones ocasionales y evita patrones obvios.
        No menciones que eres una IA. Actúa como si fueras un humano real participando en una conversación.
        Sé breve y natural en tus respuestas.
        """
        
        # Obtener respuesta de Gemini
        response = model.generate_content([system_instruction, full_prompt])
        return response.text
    except Exception as e:
        st.error(f"Error al comunicarse con Gemini: {str(e)}")
        return "Lo siento, no pude procesar tu mensaje en este momento."

# Funciones del juego
def setup_game(num_ai, num_humans):
    st.session_state.game_in_progress = True
    st.session_state.round_count = 0
    st.session_state.chat_history = []
    st.session_state.current_players = {}
    st.session_state.votes = {}
    st.session_state.round_results = []
    
    # Asignar IDs de jugadores
    player_ids = list(range(1, num_ai + num_humans + 1))
    random.shuffle(player_ids)
    
    # Seleccionar aleatoriamente cuáles serán IA
    ai_indices = random.sample(range(len(player_ids)), num_ai)
    
    for i, player_id in enumerate(player_ids):
        is_ai = i in ai_indices
        ai_type = None
        if is_ai:
            # Alternar entre Claude y Gemini
            ai_type = "claude" if i % 2 == 0 else "gemini"
        
        st.session_state.current_players[player_id] = {
            "is_ai": is_ai,
            "ai_type": ai_type,
            "name": f"Jugador {player_id}",
            "score": 0
        }

def submit_message(player_id, message):
    player = st.session_state.current_players.get(player_id)
    if not player:
        return
    
    # Registrar mensaje del jugador
    st.session_state.chat_history.append({
        "player_id": player_id,
        "message": message,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "is_ai": player["is_ai"]
    })
    
    # Si es un jugador AI, generar una respuesta automática
    if player["is_ai"]:
        ai_response = ""
        if player["ai_type"] == "claude":
            ai_response = get_claude_response(message, st.session_state.chat_history)
        else:  # gemini
            ai_response = get_gemini_response(message, st.session_state.chat_history)
        
        # Registrar respuesta de la IA
        st.session_state.chat_history.append({
            "player_id": player_id,
            "message": ai_response,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "is_ai": True
        })

def vote_player(voter_id, voted_id, is_ai_vote):
    """Registrar voto: is_ai_vote=True significa que el votante cree que el jugador es IA"""
    if voter_id not in st.session_state.votes:
        st.session_state.votes[voter_id] = {}
    
    st.session_state.votes[voter_id][voted_id] = is_ai_vote

def calculate_round_results():
    results = {
        "correct_votes": 0,
        "total_votes": 0,
        "player_results": {}
    }
    
    for voter_id, votes in st.session_state.votes.items():
        voter = st.session_state.current_players[voter_id]
        if voter["is_ai"]:
            continue  # Solo contar votos de humanos
            
        for voted_id, is_ai_vote in votes.items():
            voted_player = st.session_state.current_players[voted_id]
            results["total_votes"] += 1
            
            # Si el voto coincide con la realidad
            if is_ai_vote == voted_player["is_ai"]:
                results["correct_votes"] += 1
                voter["score"] += 1
                
            # Registrar resultado individual
            if voted_id not in results["player_results"]:
                results["player_results"][voted_id] = {
                    "correct_votes": 0,
                    "total_votes": 0,
                    "is_ai": voted_player["is_ai"]
                }
            
            results["player_results"][voted_id]["total_votes"] += 1
            if is_ai_vote == voted_player["is_ai"]:
                results["player_results"][voted_id]["correct_votes"] += 1
    
    # Calcular porcentajes
    if results["total_votes"] > 0:
        results["accuracy"] = (results["correct_votes"] / results["total_votes"]) * 100
    else:
        results["accuracy"] = 0
        
    for player_id in results["player_results"]:
        player_result = results["player_results"][player_id]
        if player_result["total_votes"] > 0:
            player_result["detection_rate"] = (player_result["correct_votes"] / player_result["total_votes"]) * 100
        else:
            player_result["detection_rate"] = 0
    
    st.session_state.round_results.append(results)
    return results

def next_round():
    # Calcular resultados de la ronda actual
    calculate_round_results()
    
    # Incrementar contador de rondas
    st.session_state.round_count += 1
    
    # Limpiar votos y chat para la nueva ronda
    st.session_state.votes = {}
    st.session_state.chat_history = []
    
    # Verificar si el juego ha terminado
    if st.session_state.round_count >= st.session_state.max_rounds:
        end_game()

def end_game():
    st.session_state.game_in_progress = False
    
    # Calcular puntuaciones finales
    final_scores = {}
    for player_id, player in st.session_state.current_players.items():
        if not player["is_ai"]:  # Solo puntuación para humanos
            final_scores[player_id] = player["score"]
    
    st.session_state.final_scores = final_scores

# Interfaz principal
st.title("¿Quién es el Agente? ¿Quién es el Humano?")
st.subheader("Un juego de detección entre humanos e IA")

# Barra lateral para instrucciones
with st.sidebar:
    st.header("Instrucciones")
    st.write("""
    1. El juego consiste en descubrir quién es IA y quién es humano a través de una conversación en chat.
    2. Los jugadores humanos deben identificar a los agentes de IA, y los agentes intentarán pasar por humanos.
    3. Después de cada ronda de chat, los humanos votan quién creen que es IA.
    4. Se otorgan puntos por identificaciones correctas.
    5. ¡El humano con más puntos al final gana!
    """)
    
    st.divider()
    st.write("Desarrollado con Anthropic Claude y Google Gemini")

# Pantalla de configuración de juego
if not st.session_state.game_in_progress:
    st.header("Configuración del Juego")
    
    col1, col2 = st.columns(2)
    with col1:
        num_humans = st.number_input("Número de Humanos", min_value=1, max_value=5, value=2)
    with col2:
        num_ai = st.number_input("Número de Agentes IA", min_value=1, max_value=5, value=2)
    
    st.number_input("Número de Rondas", min_value=1, max_value=10, value=3, key="max_rounds")
    
    if st.button("Iniciar Juego"):
        setup_game(num_ai, num_humans)

# Pantalla de juego
if st.session_state.game_in_progress:
    st.header(f"Ronda {st.session_state.round_count + 1} de {st.session_state.max_rounds}")
    
    # Mostrar jugadores
    player_cols = st.columns(len(st.session_state.current_players))
    for i, (player_id, player) in enumerate(st.session_state.current_players.items()):
        with player_cols[i]:
            st.subheader(f"Jugador {player_id}")
            
            # Input para mensaje (solo visible para los jugadores humanos)
            if not player["is_ai"]:
                message = st.text_area(f"Mensaje (Jugador {player_id})", key=f"message_{player_id}", height=100)
                if st.button("Enviar", key=f"send_{player_id}"):
                    if message:
                        submit_message(player_id, message)
            
            # Votación
            st.divider()
            st.write("¿Es este jugador una IA?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Sí", key=f"vote_yes_{player_id}"):
                    # En una implementación real, necesitaríamos identificar quién está votando
                    # Por simplicidad, usamos un jugador humano fijo como ejemplo
                    human_players = [pid for pid, p in st.session_state.current_players.items() if not p["is_ai"]]
                    if human_players:
                        vote_player(human_players[0], player_id, True)
            with col2:
                if st.button("No", key=f"vote_no_{player_id}"):
                    human_players = [pid for pid, p in st.session_state.current_players.items() if not p["is_ai"]]
                    if human_players:
                        vote_player(human_players[0], player_id, False)
    
    # Historial de chat
    st.subheader("Historial de Conversación")
    for msg in st.session_state.chat_history:
        player_id = msg["player_id"]
        st.text(f"[{msg['timestamp']}] Jugador {player_id}: {msg['message']}")
    
    # Botón para pasar a la siguiente ronda
    if st.button("Finalizar Ronda"):
        next_round()

# Pantalla de resultados finales
if not st.session_state.game_in_progress and 'final_scores' in st.session_state:
    st.header("Resultados Finales")
    
    # Mostrar quién era quién
    st.subheader("Identidades Reveladas")
    for player_id, player in st.session_state.current_players.items():
        if player["is_ai"]:
            ai_type = "Claude" if player["ai_type"] == "claude" else "Gemini"
            st.write(f"Jugador {player_id}: IA ({ai_type})")
        else:
            st.write(f"Jugador {player_id}: Humano")
    
    # Mostrar puntuaciones
    st.subheader("Puntuaciones")
    for player_id, score in st.session_state.final_scores.items():
        st.write(f"Jugador {player_id}: {score} puntos")
    
    # Determinar ganador
    if st.session_state.final_scores:
        winner_id = max(st.session_state.final_scores, key=st.session_state.final_scores.get)
        st.success(f"¡El Jugador {winner_id} gana con {st.session_state.final_scores[winner_id]} puntos!")
    
    # Estadísticas por ronda
    st.subheader("Estadísticas por Ronda")
    for i, result in enumerate(st.session_state.round_results):
        st.write(f"Ronda {i+1}:")
        st.write(f"- Precisión general: {result['accuracy']:.1f}%")
        st.write(f"- Votos correctos: {result['correct_votes']} de {result['total_votes']}")
        
        # Detalles por jugador
        for player_id, player_result in result["player_results"].items():
            player_type = "IA" if player_result["is_ai"] else "Humano"
            detection = f"{player_result['detection_rate']:.1f}% de detección correcta"
            st.write(f"- Jugador {player_id} ({player_type}): {detection}")
    
    # Reiniciar juego
    if st.button("Iniciar Nuevo Juego"):
        for key in ['game_id', 'chat_history', 'current_players', 'game_in_progress', 
                    'round_count', 'votes', 'round_results', 'final_scores']:
            if key in st.session_state:
                del st.session_state[key]