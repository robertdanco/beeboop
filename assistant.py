# Importing required packages
import streamlit as st
import openai
import uuid
import time
import backoff

# Function to initialize session state variables
def initialize_session_state():
    default_values = {
        "session_id": str(uuid.uuid4()),
        "run": {"status": None},
        "messages": [],
        "retry_error": 0,
        "assistant": None,
        "thread": None
    }
    for key, value in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = value

# Function to display messages
def display_messages(messages):
    for message in reversed(messages):
        if message.role in ["user", "assistant"]:
            with st.chat_message(message.role):
                st.markdown(message.content[0].text.value)

# Function for checking run status with exponential backoff
@backoff.on_exception(backoff.expo, Exception, max_tries=3)
def check_run_status():
    if st.session_state.run.status == "running":
        with st.chat_message("assistant"):
            st.write("Thinking ......")
        time.sleep(1)
        st.rerun()
    elif st.session_state.run.status == "failed":
        st.session_state.retry_error += 1
        with st.chat_message("assistant"):
            if st.session_state.retry_error < 3:
                st.write("Run failed, retrying ......")
                time.sleep(3)
                st.rerun()
            else:
                st.error("FAILED: The OpenAI API is currently processing too many requests. Please try again later ......")
    elif st.session_state.run.status != "completed":
        st.session_state.run = client.beta.threads.runs.retrieve(
            thread_id=st.session_state.thread.id,
            run_id=st.session_state.run.id,
        )
        time.sleep(3)
        st.rerun()

# Initialize session state variables
initialize_session_state()

# Streamlit UI setup
st.set_page_config(page_title="BeeBoop: a Beeswax Chatbot")
st.sidebar.title("Ask me anything!")
st.sidebar.divider()
st.sidebar.markdown("Current Version: 0.0.3")
st.sidebar.markdown("Using gpt-4-1106-preview API")
st.sidebar.markdown(st.session_state.session_id)
st.sidebar.divider()

client = openai.OpenAI()
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Handling OpenAI assistant and thread creation
if "assistant" not in st.session_state:
    st.session_state.assistant = openai.beta.assistants.retrieve(
        st.secrets["OPENAI_ASSISTANT"]
    )
    st.session_state.thread = client.beta.threads.create(
        metadata={
            "session_id": st.session_state.session_id,
        }
    )

# Main interaction loop
if prompt := st.chat_input("How can I help you?"):
    with st.chat_message("user"):
        st.write(prompt)

    st.session_state.messages = client.beta.threads.messages.create(
        thread_id=st.session_state.thread.id, 
        role="user", 
        content=f"Use the provided documents as context to answer this question: {prompt}"
    )

    st.session_state.run = client.beta.threads.runs.create(
        thread_id=st.session_state.thread.id,
        assistant_id=st.session_state.assistant.id,
    )
    if st.session_state.retry_error < 3:
        time.sleep(1)
        st.rerun()

    display_messages(st.session_state.messages.data[-1:])  # Display only the latest message

# Check run status with improved retry mechanism
check_run_status()
