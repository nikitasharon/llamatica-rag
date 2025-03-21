import streamlit as st
import requests
import json
import fitz  # PyMuPDF for PDF text extraction

# Set API key and endpoint (Directly included)
GROQ_API_KEY = "API_KEY_GOES_HERE"  # Replace with your actual API key
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"  # Corrected endpoint
MODEL_NAME = "llama-3.3-70b-versatile"
#This is a cool code
# Define the chatbot's persona as a system message (this will be hidden from display)
PERSONA_MESSAGE = {
    "role": "system",
    "content": ("You are Llamatica, an AI assistant who can help with general tasks "
                "and also answer users' questions based on the document when it is uploaded.")
}

# Streamlit UI
st.set_page_config(page_title="Llamatica - AI Chatbot", layout="wide")
st.title("🦙 Llamatica - RAG Chatbot!")

# Initialize chat and document state if not present
if "messages" not in st.session_state:
    # Start with the persona message in the background (won't be displayed)
    st.session_state.messages = [PERSONA_MESSAGE]
if "doc_summaries" not in st.session_state:
    st.session_state.doc_summaries = []  # List of (filename, summary) tuples
if "processed_doc_names" not in st.session_state:
    st.session_state.processed_doc_names = set()

# Sidebar for file upload (allow multiple file uploads)
st.sidebar.header("Upload Document(s) for Summary")
uploaded_files = st.sidebar.file_uploader("Choose PDF file(s)", type=["pdf"], accept_multiple_files=True)

if uploaded_files is not None:
    for uploaded_file in uploaded_files:
        # Process the file only if it hasn't been processed before
        if uploaded_file.name not in st.session_state.processed_doc_names:
            with st.spinner(f"Reading and summarizing {uploaded_file.name}..."):
                try:
                    # Extract text from PDF using PyMuPDF
                    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                    file_content = "\n".join([page.get_text("text") for page in doc])
                    if not file_content.strip():
                        summary = f"Error: Could not extract text from {uploaded_file.name}. It might be scanned or image-based."
                    else:
                        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
                        payload = {
                            "model": MODEL_NAME,
                            "messages": [
                                {"role": "system", "content": "Summarize the following document."},
                                {"role": "user", "content": file_content}
                            ],
                            "max_tokens": 1000
                        }
                        response = requests.post(GROQ_ENDPOINT, json=payload, headers=headers).json()
                        if "choices" in response:
                            summary = response["choices"][0]["message"]["content"]
                        else:
                            summary = f"Error: {response.get('error', {}).get('message', 'Unknown error occurred.')}"
                except Exception as e:
                    summary = f"Error processing {uploaded_file.name}: {str(e)}"
                # Save summary and mark file as processed
                st.session_state.doc_summaries.append((uploaded_file.name, summary))
                st.session_state.processed_doc_names.add(uploaded_file.name)
                # Also insert the document context as a system message in chat history
                st.session_state.messages.insert(0, {
                    "role": "system",
                    "content": f"Document '{uploaded_file.name}' context: {summary}"
                })

# Display chat history (hide the persona message)
for message in st.session_state.messages:
    # Skip displaying the persona system message
    if message["role"] == "system" and message["content"] == PERSONA_MESSAGE["content"]:
        continue
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input for chat
user_input = st.chat_input("Ask me anything...")
if user_input:
    # Append user message to chat history
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Build messages payload for the API.
    # Include the persona message (even though it's hidden) and all document context system messages,
    # then the rest of the conversation.
    messages_payload = [PERSONA_MESSAGE]
    for filename, summary in st.session_state.doc_summaries:
        messages_payload.append({"role": "system", "content": f"Document '{filename}' context: {summary}"})
    messages_payload.extend(st.session_state.messages)
    
    with st.spinner("Thinking..."):
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": MODEL_NAME,
            "messages": messages_payload,
            "max_tokens": 450
        }
        response = requests.post(GROQ_ENDPOINT, json=payload, headers=headers).json()
        if "choices" in response:
            ai_response = response["choices"][0]["message"]["content"]
        else:
            ai_response = f"Error: {response.get('error', {}).get('message', 'Unknown error occurred.')}"
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
    with st.chat_message("assistant"):
        st.markdown(ai_response)
