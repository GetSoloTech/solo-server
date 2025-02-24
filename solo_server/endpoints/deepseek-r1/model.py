import re

import streamlit as st
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="lit",
)


def header():
    st.markdown(
        """
        <div style='text-align: center; margin-bottom:4'>
        <img src="https://github.com/deepseek-ai/DeepSeek-V2/blob/main/figures/logo.svg?raw=true">
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "<h1 style='text-align: center; font-size:1.5rem'>Chat with DeepSeek-R1</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='text-align: center; margin-bottom:4'>"
        "<p style='font-size:0.9rem'>DeepSeek-R1: A cutting-edge reasoning model leveraging cold-start RL to surpass predecessor limitations, rivaling OpenAI-o1 in math, code, and reasoning, while open-sourcing SOTA distilled variants for community innovation. <br/><a href='https://huggingface.co/deepseek-ai/DeepSeek-R1' target='_blank'>Read more</a></p>"
        "</div>",
        unsafe_allow_html=True,
    )


def initialize_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []


def format_assistant_content(content):
    """Format assistant content by replacing specific tags."""
    return (
        content.replace("<think>\n\n</think>", "")
        .replace("<think>", "")
        .replace("</think>", "")
    )


def display_chat_history(show_clear_button=False):
    """Display chat messages from session state."""
    for message in st.session_state.messages:
        role = message["role"]
        content = message["content"]
        think_content = ""
        if role == "assistant":
            # extract content between <think> tags
            pattern = r"<think>(.*?)</think>"
            think_content = re.search(pattern, content, re.DOTALL).group(0)
            content = content.replace(think_content, "")
            think_content = format_assistant_content(think_content)
        with st.chat_message(role):
            if think_content and len(think_content) > 0:
                with st.expander("Thinking complete!"):
                    st.markdown(think_content)
            st.markdown(content)

    if show_clear_button and st.session_state.messages:
        _, _, right = st.columns(3)
        right.button(
            "Clear Chat History",
            on_click=lambda: st.session_state.messages.clear(),
            type="primary",
            icon=":material/delete:",
            use_container_width=True,
        )


def main():
    # Title section
    header()

    # Initialize session state
    initialize_session_state()

    # Chat history container
    display_chat_history(show_clear_button=False)

    if prompt := st.chat_input("Ask something", key="prompt"):
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})

        # Get response from the assistant
        with st.chat_message("assistant"):
            messages = [*st.session_state.messages]
            stream = client.chat.completions.create(
                model="deepseek-r1",
                messages=messages,
                stream=True,
                max_completion_tokens=2048
            )

            # thinking part
            thinking_content = ""
            with st.status("Thinking...", expanded=True) as status:
                res = st.empty()
                for chunk in stream:
                    content = chunk.choices[0].delta.content or ""
                    thinking_content += content

                    if "<think>" in content:
                        continue
                    if "</think>" in content:
                        content = content.replace("</think>", "")
                        status.update(
                            label="Thinking complete!", state="complete", expanded=False
                        )
                        break
                    res.markdown(format_assistant_content(thinking_content))

            # response part
            res = st.empty()
            response_content = ""
            for chunk in stream:
                content = chunk.choices[0].delta.content or ""
                response_content += content
                res.markdown(response_content)

            st.session_state.messages.append(
                {"role": "assistant", "content": thinking_content + response_content}
            )


if __name__ == "__main__":
    main()