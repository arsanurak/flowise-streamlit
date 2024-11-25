import streamlit as st
from flowise import Flowise, PredictionData
import json
import requests

# Flowise app base url
base_url = st.secrets["APP_URL"] or "https://your-flowise-url.com"

# Chatflow/Agentflow ID
flow_id = st.secrets["FLOW_ID"] or "abc"

# Show title and description.
st.title("💬 Flowise Streamlit Chat")
st.write(
    "This is a simple chatbot that uses Flowise Python SDK"
)

# Sidebar for user ID and API key input
with st.sidebar:
    user_id = st.text_input("User ID")
    api_key = st.text_input("API Key", type="password")

#Webhook URL
webhook_url = "https://wp.dollarsmart.co/wp-json/custom/v1/api-call"

# Create a Flowise client.
client = Flowise(base_url=base_url)

# Create a session state variable to store the chat messages. This ensures that the
# messages persist across reruns.
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display the existing chat messages via `st.chat_message`.
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

def generate_response(prompt: str):
    print('generating response')
    try:
        #Webhook check
        webhook_response = requests.post(webhook_url, json={"user_id": user_id, "api_key": api_key})
        webhook_response.raise_for_status()
        webhook_data = webhook_response.json()
        status = webhook_data.get('status', 'unknown')
        message = webhook_data.get('message', 'No message provided')
        new_balance = webhook_data.get('new_balance')
        yield f"Webhook status: {status}, Message: {message}, New Balance: {new_balance}\n\n\n"

        if status != "success":
            return

        completion = client.create_prediction(
            PredictionData(
                chatflowId=flow_id,
                question=prompt,
                overrideConfig={
                    "sessionId": "session1234",
                    "user_id": user_id,
                    "api_key": api_key
                },
                streaming=True
            )
        )

        for chunk in completion:
            print(chunk)
            parsed_chunk = json.loads(chunk)
            if (parsed_chunk['event'] == 'token' and parsed_chunk['data'] != ''):
                yield str(parsed_chunk['data'])
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            yield f"Webhook request failed with 401 Unauthorized. Please check your credentials." #Handle 401 error
        else:
            yield f"An error occurred during the webhook request: {e}"
    except requests.exceptions.RequestException as e:
        yield f"An error occurred during the webhook request: {e}"
    except json.JSONDecodeError as e:
        yield f"Invalid JSON response from webhook: {e}"
    except KeyError as e:
        yield f"Missing key in webhook response: {e}"


# Create a chat input field to allow the user to enter a message. This will display
# automatically at the bottom of the page.
if prompt := st.chat_input("What is up?"):

    # Store and display the current prompt.
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Stream the response to the chat using `st.write_stream`, then store it in 
    # session state.
    with st.chat_message("assistant"):
        response = generate_response(prompt)
        full_response = st.write_stream(response)
    st.session_state.messages.append({"role": "assistant", "content": full_response})
