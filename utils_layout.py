
import streamlit as st

def whatsapp_icon(url: str, size: int = 22):
    svg = f"""
    <a href="{url}" target="_blank" rel="noopener noreferrer" title="WhatsApp">
      <svg width="{size}" height="{size}" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg" style="display:inline-block;vertical-align:middle;">
        <defs>
          <linearGradient id="wgrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="#25D366"/>
            <stop offset="100%" stop-color="#128C7E"/>
          </linearGradient>
        </defs>
        <circle cx="16" cy="16" r="14" fill="url(#wgrad)"/>
        <path fill="#fff" d="M21.6 18.7c-.3-.2-1.7-.8-2-1s-.5-.3-.7 0-.8 1-1 1.2-.4.2-.7.1-1.4-.5-2.7-1.7-1.7-2.4-1.9-2.8 0-.6.2-.8.4-.5.5-.7.1-.4 0-.6c0-.2-.7-1.7-1-2.4-.2-.6-.5-.5-.7-.5h-.6c-.2 0-.6.1-.9.4s-1.2 1.1-1.2 2.7 1.2 3.1 1.4 3.3c.2.3 2.4 3.6 5.8 5 3.5 1.4 3.5.9 4.1.9s2-.9 2.3-1.8c.3-.9.3-1.7.2-1.8 0-.1-.2-.1-.4-.2z"/>
      </svg>
    </a>
    """
    st.markdown(svg, unsafe_allow_html=True)
