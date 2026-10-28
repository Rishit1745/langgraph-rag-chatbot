import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

for key in ("GOOGLE_API_KEY", "ALPHA_VANTAGE_API_KEY"):
    try:
        if key in st.secrets:
            os.environ[key] = st.secrets[key]
    except Exception:
        pass 


from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
import uuid
from backend import (chatbot, ingest_pdf, retrieve_all_threads, thread_document_metadata,)


# for naming the chats correctly
import json
from langchain_google_genai import ChatGoogleGenerativeAI

# **************************** utility functions **************

def generate_thread_id():
    thread_id = str(uuid.uuid4())
    return thread_id


def extract_text(content):
    if isinstance(content, str):
        return content
    parts = []
    def walk(item):
        if isinstance(item, dict):
            if item.get('type') == 'text':
                parts.append(item.get('text', ''))
        elif isinstance(item, list):
            for sub in item:
                walk(sub)
    walk(content)
    return ''.join(parts)


# ---- chat titles ----
TITLES_FILE = 'chat_titles.json'
title_llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite", timeout=30)

def load_titles():
    if os.path.exists(TITLES_FILE):
        with open(TITLES_FILE) as f:
            return json.load(f)
    return {}

def save_title(thread_id, title):
    titles = load_titles()
    titles[thread_id] = title
    with open(TITLES_FILE, 'w') as f:
        json.dump(titles, f)

def generate_title(first_message):
    try:
        resp = title_llm.invoke(
            "Give a 2-4 word title for a chat that starts with this message. "
            f"Reply with only the title, no quotes.\n\nMessage: {first_message}"
        )
        title = extract_text(resp.content).strip()
        return title or first_message[:30]
    except Exception:
        return first_message[:30]   # fallback if the API fails or quota is hit


def reset_chat():
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    add_thread(st.session_state['thread_id'])
    st.session_state['message_history'] = []

def add_thread(thread_id):
    if thread_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'].append(thread_id)


def load_conv(thread_id):
    state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})
    return state.values.get('messages', [])                     

# *************************** session setup ***********************
 
# st.session_state
if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()    

if 'chat_threads' not in st.session_state:
    st.session_state['chat_threads'] = retrieve_all_threads()

if "ingested_docs" not in st.session_state:
    st.session_state["ingested_docs"] = {}

add_thread(st.session_state['thread_id'])

thread_key = str(st.session_state["thread_id"])
thread_docs = st.session_state["ingested_docs"].setdefault(thread_key, {})
threads = st.session_state["chat_threads"][::-1]
selected_thread = None

# ******************************* Sidebar UI ****************************

st.sidebar.title('LangGraph Chatbot')
st.sidebar.markdown(f"**Thread ID:** `{thread_key}`")

if st.sidebar.button('New Chat'):
    reset_chat()
    st.rerun()

if thread_docs:
    latest_doc = list(thread_docs.values())[-1]
    st.sidebar.success(
        f"Using `{latest_doc.get('filename')}` "
        f"({latest_doc.get('chunks')} chunks from {latest_doc.get('documents')} pages)"
    )
else:
    st.sidebar.info("No PDF indexed yet.")

uploaded_pdf = st.sidebar.file_uploader("Upload a PDF for this chat", type=["pdf"])
if uploaded_pdf:
    if uploaded_pdf.name in thread_docs:
        st.sidebar.info(f"`{uploaded_pdf.name}` already processed for this chat.")
    else:
        with st.sidebar.status("Indexing PDF…", expanded=True) as status_box:
            summary = ingest_pdf(
                uploaded_pdf.getvalue(),
                thread_id=thread_key,
                filename=uploaded_pdf.name,
            )
            thread_docs[uploaded_pdf.name] = summary
            status_box.update(label="✅ PDF indexed", state="complete", expanded=False)

st.sidebar.subheader("Past conversations")
if not threads:
    st.sidebar.write("No past conversations yet.")
else:
    for thread_id in threads:
        if st.sidebar.button(str(thread_id), key=f"side-thread-{thread_id}"):
            selected_thread = thread_id



# ******************************* MAIN UI ******************************
st.title("Multi Utility Chatbot")

# displaying message history
for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.text(message['content'])



# create input box
user_input = st.chat_input('Ask about your document or use tools') 

if user_input:

    # first add the mssg to history
    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    with st.chat_message('user'):
        st.markdown(user_input)

    # create a title for this chat if it doesn't have one yet
    new_title = False
    if st.session_state['thread_id'] not in load_titles():
        save_title(st.session_state['thread_id'], generate_title(user_input))
        new_title = True


    config = {
        'configurable': {'thread_id': st.session_state['thread_id']},
        'metadata': {'thread_id': st.session_state['thread_id']},
        'run_name': 'chat_response',
    }

    with st.chat_message('assistant'):
        # use a mutable holder so the generator can set/modify it
        status_holder = {"box": None}

        def ai_only_stream():
            for message_chunk, metadata in chatbot.stream(
                {'messages': [HumanMessage(content=user_input)]},
                config=config,
                stream_mode='messages',
            ):
                # lazily create & update the same status container when any tool runs
                if isinstance(message_chunk, ToolMessage):
                    tool_name = getattr(message_chunk, 'name', 'tool')
                    if status_holder["box"] is None:
                        status_holder["box"] = st.status(
                            f"Using {tool_name}...", expanded=True
                        )
                    else:
                        status_holder["box"].update(
                            label=f"Using {tool_name}...", state="running", expanded=True
                        )

                # only stream the model's own text, skip ToolMessage output
                if isinstance(message_chunk, AIMessage):
                    text = extract_text(message_chunk.content)
                    if text:
                        yield text

        ai_message = st.write_stream(ai_only_stream())

        # finalize only if a tool was actually used, otherwise the status box is never created
        if status_holder["box"] is not None:
            status_holder["box"].update(label="Done", state="complete", expanded=False)

    # save assistant's message to history after the stream is complete
    st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message})

    doc_meta = thread_document_metadata(thread_key)
    if doc_meta:
        st.caption(
            f"Document indexed: {doc_meta.get('filename')} "
            f"(chunks: {doc_meta.get('chunks')}, pages: {doc_meta.get('documents')})"
        )
st.divider()

if selected_thread:
    st.session_state["thread_id"] = selected_thread
    messages = load_conv(selected_thread)

    temp_messages = []
    for msg in messages:
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        temp_messages.append({"role": role, "content": msg.content})
    st.session_state["message_history"] = temp_messages
    st.session_state["ingested_docs"].setdefault(str(selected_thread), {})
    st.rerun()


    # refresh so the new title shows in the sidebar
    if new_title:
        st.rerun()